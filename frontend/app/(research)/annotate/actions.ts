"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "@/utils/supabase/server";

export async function submitAnnotation(
  pairId: string, 
  failureReasons: string[], 
  sameCharacter: boolean,
  anatomyIntact: boolean,
  textFree: boolean
) {
  const supabase = await createSupabaseServerClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();

  if (authError || !user) {
    return { error: "Unauthorized" };
  }

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  // Fail secure: if is_adjudicator doesn't exist or query fails, deny access
  if (profileError || profile?.role !== "researcher" || profile?.is_adjudicator) {
    console.error("Authorization error or invalid role:", profileError);
    return { error: "Unauthorized" };
  }

  // Server-Side Invariant Validation
  if (sameCharacter && failureReasons.length > 0) {
    return { error: "Invalid state: same_character is true but failure reasons provided" };
  }
  if (!sameCharacter && failureReasons.length === 0) {
    return { error: "Invalid state: same_character is false but no failure reasons provided" };
  }
  if (typeof anatomyIntact !== "boolean" || typeof textFree !== "boolean") {
    return { error: "Invalid state: anatomy_intact and text_free must be explicitly provided" };
  }

  // Insert annotation with first-write-wins idempotency
  const { error: insertError } = await supabase
    .from("annotations")
    .upsert({
      pair_id: pairId,
      annotator_id: user.id,
      same_character: sameCharacter,
      anatomy_intact: anatomyIntact,
      text_free: textFree,
      failure_reasons: failureReasons,
    }, {
      onConflict: "pair_id,annotator_id",
      ignoreDuplicates: true,
    });

  if (insertError) {
    console.error("Failed to insert annotation:", insertError);
    return { error: "Failed to save annotation" };
  }

  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const { createClient: createSupabaseClient } = await import("@supabase/supabase-js");
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
      
      const a1Reasons = Array.isArray(a1.failure_reasons) ? [...a1.failure_reasons].sort() : [];
      const a2Reasons = Array.isArray(a2.failure_reasons) ? [...a2.failure_reasons].sort() : [];

      const agree = a1.same_character === a2.same_character && 
                    a1.anatomy_intact === a2.anatomy_intact &&
                    a1.text_free === a2.text_free &&
                    JSON.stringify(a1Reasons) === JSON.stringify(a2Reasons);
                    
      const newStatus = agree ? "complete" : "conflicted";
      await adminClient.from("research_pairs").update({ status: newStatus }).eq("id", pairId);
    }
  }

  // Clear router cache to ensure the next fetch retrieves a fresh randomized pair
  revalidatePath("/(research)/annotate", "page");

  return { success: true };
}

export async function getNextPair() {
  const supabase = await createSupabaseServerClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();

  if (authError || !user) {
    return { error: "Unauthorized" };
  }

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  if (profileError || profile?.role !== "researcher" || profile?.is_adjudicator) {
    return { error: "Unauthorized" };
  }

  // Use service role to bypass RLS and fetch a pair that this user hasn't annotated yet
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const { createClient: createSupabaseClient } = await import("@supabase/supabase-js");
  const adminClient = createSupabaseClient(supabaseUrl, serviceKey);

  const { data: pairs, error: pairsError } = await adminClient
    .from("research_pairs")
    .select("id, canonical_storage_path, scene_storage_path")
    .in("status", ["pending", "partially_annotated"])
    .order("created_at", { ascending: true })
    .limit(50);

  if (pairsError || !pairs || pairs.length === 0) {
    return { pair: null };
  }

  const { data: userAnnotations } = await adminClient
    .from("annotations")
    .select("pair_id")
    .eq("annotator_id", user.id);

  const annotatedPairIds = new Set((userAnnotations || []).map(a => a.pair_id));
  
  const unannotatedPairs = pairs.filter(p => !annotatedPairIds.has(p.id));

  if (unannotatedPairs.length === 0) {
    return { pair: null };
  }

  // Reproducible pseudo-random shuffle per annotator
  const hashedSort = unannotatedPairs.map(p => {
    let hash = 0;
    const str = p.id + user.id;
    for (let i = 0; i < str.length; i++) {
      hash = (Math.imul(31, hash) + str.charCodeAt(i)) | 0;
    }
    return { ...p, sortVal: hash };
  }).sort((a, b) => a.sortVal - b.sortVal);

  const nextPair = hashedSort[0];

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
