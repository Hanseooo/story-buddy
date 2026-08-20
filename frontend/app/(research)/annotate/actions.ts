"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "@/utils/supabase/server";
import { createAdminClient } from "@/utils/supabase/admin";

import { verifyResearchAuth, validateSubmissionPayload, type SubmissionPayload } from "../_shared/actions";

export async function submitAnnotation(payload: SubmissionPayload) {
  const { pairId, failureReasons, sameCharacter, anatomyIntact, textFree } = payload;
  
  const { error: authError, user } = await verifyResearchAuth(false);
  if (authError || !user) {
    return { error: authError || "Unauthorized" };
  }

  const { error: validationError } = validateSubmissionPayload(payload);
  if (validationError) {
    return { error: validationError };
  }

  const supabase = await createSupabaseServerClient();

  // Insert annotation with first-write-wins idempotency
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
    if (insertError.code === "23505") {
      console.log("Annotation already exists for pair", pairId);
      // Let it fall through, or return success, but we should continue to update queue status if needed?
      // Actually, if it's already there, maybe the queue status is already updated. But to be safe, we just proceed.
    } else {
      console.error("Failed to insert annotation:", insertError);
      return { error: "Failed to save annotation" };
    }
  }

  const adminClient = await createAdminClient();

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
  const { error: authError, user } = await verifyResearchAuth(false);
  if (authError || !user) {
    return { error: authError || "Unauthorized" };
  }

  // Use service role to bypass RLS and fetch a pair that this user hasn't annotated yet
  const adminClient = await createAdminClient();

  const { data: userAnnotations } = await adminClient
    .from("annotations")
    .select("pair_id")
    .eq("annotator_id", user.id);

  const annotatedPairIds = (userAnnotations || []).map(a => a.pair_id);

  let query = adminClient
    .from("research_pairs")
    .select("id, canonical_storage_path, scene_storage_path")
    .in("status", ["pending", "partially_annotated"])
    .order("created_at", { ascending: true })
    .limit(50);

  if (annotatedPairIds.length > 0) {
    query = query.not("id", "in", `(${annotatedPairIds.join(",")})`);
  }

  const { data: pairs, error: pairsError } = await query;

  if (pairsError || !pairs || pairs.length === 0) {
    return { pair: null };
  }

  const unannotatedPairs = pairs;

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
