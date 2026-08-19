"use server";

import { createSupabaseServerClient } from "@/utils/supabase/server";

export async function submitAnnotation(
  pairId: string, 
  failureReasons: string[], 
  sameCharacter: boolean,
  anatomyIntact: boolean,
  textFree: boolean
) {
  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return { error: "Unauthorized" };
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single();

  if (profile?.role !== "researcher") {
    return { error: "Unauthorized" };
  }

  // Insert annotation
  const { error: insertError } = await supabase
    .from("annotations")
    .insert({
      pair_id: pairId,
      annotator_id: user.id,
      same_character: sameCharacter,
      anatomy_intact: anatomyIntact,
      text_free: textFree,
      failure_reasons: failureReasons,
    });

  if (insertError) {
    console.error("Failed to insert annotation:", insertError);
    return { error: "Failed to save annotation" };
  }

  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const { createClient: createSupabaseClient } = await import('@supabase/supabase-js');
  const adminClient = createSupabaseClient(supabaseUrl, serviceKey);

  // We need to count annotations for this pair
  const { count, error: countError } = await adminClient
    .from("annotations")
    .select("*", { count: "exact", head: true })
    .eq("pair_id", pairId);

  if (countError) {
    console.error("Failed to count annotations:", countError);
    return { error: "Saved, but failed to update queue status" };
  }

  if (count === 1) {
    await adminClient.from("research_pairs").update({ status: "partially_annotated" }).eq("id", pairId);
  } else if (count === 2) {
    // Fetch both to see if they agree
    const { data: annotations } = await adminClient
      .from("annotations")
      .select("same_character, failure_reasons, anatomy_intact, text_free")
      .eq("pair_id", pairId);
      
    if (annotations && annotations.length === 2) {
      const [a1, a2] = annotations;
      
      const agree = a1.same_character === a2.same_character && 
                    a1.anatomy_intact === a2.anatomy_intact &&
                    a1.text_free === a2.text_free &&
                    JSON.stringify(a1.failure_reasons.sort()) === JSON.stringify(a2.failure_reasons.sort());
                    
      const newStatus = agree ? "complete" : "conflicted";
      await adminClient.from("research_pairs").update({ status: newStatus }).eq("id", pairId);
    }
  }

  return { success: true };
}

export async function getNextPair() {
  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return { error: "Unauthorized" };
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("role")
    .eq("id", user.id)
    .single();

  if (profile?.role !== "researcher") {
    return { error: "Unauthorized" };
  }

  // Use service role to bypass RLS and fetch a pair that this user hasn't annotated yet
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const { createClient: createSupabaseClient } = await import('@supabase/supabase-js');
  const adminClient = createSupabaseClient(supabaseUrl, serviceKey);

  // We need a pair where status IN ('pending', 'partially_annotated') 
  // AND where this user hasn't already annotated it.
  // For simplicity, we fetch a few and filter in JS if we can't do a complex join here.
  const { data: pairs } = await adminClient
    .from("research_pairs")
    .select("id, canonical_storage_path, scene_storage_path")
    .in("status", ["pending", "partially_annotated"])
    .order("created_at", { ascending: true })
    .limit(20);

  if (!pairs || pairs.length === 0) {
    return { pair: null };
  }

  const { data: userAnnotations } = await adminClient
    .from("annotations")
    .select("pair_id")
    .eq("annotator_id", user.id);

  const annotatedPairIds = new Set((userAnnotations || []).map(a => a.pair_id));
  
  const nextPair = pairs.find(p => !annotatedPairIds.has(p.id));

  if (!nextPair) {
    return { pair: null };
  }

  // Mint signed URLs
  const { data: canonicalUrlData } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(nextPair.canonical_storage_path, 3600);
    
  const { data: sceneUrlData } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(nextPair.scene_storage_path, 3600);

  return {
    pair: {
      id: nextPair.id,
      canonical_signed_url: canonicalUrlData?.signedUrl || "",
      scene_signed_url: sceneUrlData?.signedUrl || ""
    }
  };
}
