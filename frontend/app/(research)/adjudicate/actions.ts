"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "@/utils/supabase/server";
import { createAdminClient } from "@/utils/supabase/admin";

import { verifyResearchAuth, validateSubmissionPayload, type SubmissionPayload } from "../_shared/actions";

export type BlindAnnotation = {
  same_character: boolean;
  failure_reasons: string[];
  anatomy_intact: boolean;
  text_free: boolean;
};

export async function submitAdjudication(payload: SubmissionPayload) {
  const { pairId, failureReasons, sameCharacter, anatomyIntact, textFree } = payload;
  
  const { error: authError, user } = await verifyResearchAuth(true);
  if (authError || !user) return { error: authError || "Unauthorized" };

  const { error: validationError } = validateSubmissionPayload(payload);
  if (validationError) return { error: validationError };

  const supabase = await createSupabaseServerClient();

  const adminClient = await createAdminClient();

  // Validate that the pair is still conflicted
  const { data: pairInfo } = await adminClient
    .from("research_pairs")
    .select("status")
    .eq("id", pairId)
    .single();

  if (!pairInfo || pairInfo.status !== "conflicted") {
    return { error: "Pair is no longer conflicted" };
  }

  const { data: existingAnnotations } = await adminClient
    .from("annotations")
    .select("annotator_id")
    .eq("pair_id", pairId);

  if (!existingAnnotations || (existingAnnotations.length !== 2 && existingAnnotations.length !== 3)) {
    return { error: "Invalid pair state: requires exactly 2 prior annotations" };
  }

  if (existingAnnotations.length === 3) {
    if (existingAnnotations.some(a => a.annotator_id === user.id)) {
      // Idempotency: Already adjudicated by this user, just retry status update
      await adminClient.from("research_pairs").update({ status: "adjudicated" }).eq("id", pairId);
      return { success: true };
    }
    return { error: "Pair already adjudicated by another adjudicator" };
  }

  if (existingAnnotations.some(a => a.annotator_id === user.id)) {
    return { error: "Adjudicator cannot resolve their own annotations" };
  }

  // Insert the authoritative annotation (first-write-wins idempotency)
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
      console.log("Adjudication already exists for pair", pairId);
    } else {
      console.error("Failed to insert adjudication:", insertError);
      return { error: "Failed to save adjudication" };
    }
  }

  // Update status to adjudicated
  const { error: updateError } = await adminClient
    .from("research_pairs")
    .update({ status: "adjudicated" })
    .eq("id", pairId);

  if (updateError) {
    console.error("Failed to update status:", updateError);
    return { error: "Saved, but failed to update pair status" };
  }

  revalidatePath("/(research)/adjudicate", "page");
  return { success: true };
}

export async function getConflictedPair() {
  const { error: authError, user } = await verifyResearchAuth(true);
  if (authError || !user) return { error: authError || "Unauthorized" };

  const adminClient = await createAdminClient();

  const { data: userAnnotations } = await adminClient
    .from("annotations")
    .select("pair_id")
    .eq("annotator_id", user.id);

  const annotatedPairIds = (userAnnotations || []).map(a => a.pair_id);

  let query = adminClient
    .from("research_pairs")
    .select("id, canonical_storage_path, scene_storage_path")
    .eq("status", "conflicted")
    .order("created_at", { ascending: true })
    .limit(50);

  if (annotatedPairIds.length > 0) {
    query = query.not("id", "in", `(${annotatedPairIds.join(",")})`);
  }

  const { data: pairs, error: pairsError } = await query;

  if (pairsError || !pairs || pairs.length === 0) {
    return { pair: null };
  }

  let selectedPair = null;
  let annotationA: BlindAnnotation | null = null;
  let annotationB: BlindAnnotation | null = null;

  for (const pair of pairs) {
    const { data: annotations } = await adminClient
      .from("annotations")
      .select("annotator_id, same_character, failure_reasons, anatomy_intact, text_free")
      .eq("pair_id", pair.id);

    if (annotations && annotations.length === 2 && !annotations.some(a => a.annotator_id === user.id)) {
      const [a1, a2] = annotations;
      
      const a1Reasons = Array.from(new Set(a1.failure_reasons || [])).sort();
      const a2Reasons = Array.from(new Set(a2.failure_reasons || [])).sort();

      const agree = a1.same_character === a2.same_character && 
                    a1.anatomy_intact === a2.anatomy_intact &&
                    a1.text_free === a2.text_free &&
                    JSON.stringify(a1Reasons) === JSON.stringify(a2Reasons);

      if (agree) continue; // Not truly conflicted

      selectedPair = pair;
      // Strip identities
      annotationA = {
        same_character: a1.same_character,
        failure_reasons: a1.failure_reasons,
        anatomy_intact: a1.anatomy_intact,
        text_free: a1.text_free,
      };
      annotationB = {
        same_character: a2.same_character,
        failure_reasons: a2.failure_reasons,
        anatomy_intact: a2.anatomy_intact,
        text_free: a2.text_free,
      };
      break;
    }
  }

  if (!selectedPair || !annotationA || !annotationB) {
    return { pair: null };
  }

  const { data: canonicalUrlData } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(selectedPair.canonical_storage_path, 3600);
    
  const { data: sceneUrlData } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(selectedPair.scene_storage_path, 3600);

  return {
    pair: {
      id: selectedPair.id,
      canonical_signed_url: canonicalUrlData?.signedUrl || "",
      scene_signed_url: sceneUrlData?.signedUrl || ""
    },
    annotationA,
    annotationB
  };
}
