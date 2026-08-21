"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "@/utils/supabase/server";
import { createAdminClient } from "@/utils/supabase/admin";

import { verifyResearchAuth } from "../_shared/actions";
import { validateSubmissionPayload, type SubmissionPayload, isConsensus } from "../_shared/validation";

export type BlindAnnotation = {
  same_character: boolean;
  failure_reasons: string[];
  anatomy_intact: boolean;
  text_free: boolean;
};

async function findAdjudicatorIds(
  adminClient: Awaited<ReturnType<typeof createAdminClient>>,
  userIds: string[],
) {
  const { data, error } = await adminClient
    .from("profiles")
    .select("id")
    .in("id", userIds)
    .eq("is_adjudicator", true);
  return { ids: new Set((data || []).map(profile => profile.id)), error };
}

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
    if (!existingAnnotations.some(a => a.annotator_id === user.id)) {
      return { error: "Pair already adjudicated by another adjudicator" };
    }
  }

  const priorAnnotations = existingAnnotations.filter(annotation => annotation.annotator_id !== user.id);
  if (priorAnnotations.length !== 2) {
    return { error: "Adjudicator cannot resolve their own annotations" };
  }

  const { ids: priorAdjudicators, error: profileError } = await findAdjudicatorIds(
    adminClient,
    priorAnnotations.map(annotation => annotation.annotator_id),
  );
  if (profileError) return { error: "Failed to verify prior annotators" };
  if (priorAdjudicators.size > 0) {
    return { error: "Invalid pair state: prior annotations must be from ordinary annotators" };
  }

  if (existingAnnotations.length === 3) {
    const { error: updateError } = await adminClient
      .from("research_pairs")
      .update({ status: "adjudicated" })
      .eq("id", pairId);
    if (updateError) return { error: "Saved, but failed to update pair status" };
    return { success: true };
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

  const { data: userAnnotations, error: annotationsError } = await adminClient
    .from("annotations")
    .select("pair_id")
    .eq("annotator_id", user.id);

  if (annotationsError) return { error: "Failed to load adjudication queue" };

  const annotatedPairIds = new Set((userAnnotations || []).map(a => a.pair_id));

  const { data: adjudicatorProfiles, error: profilesError } = await adminClient
    .from("profiles")
    .select("id")
    .eq("is_adjudicator", true);
  if (profilesError) return { error: "Failed to load adjudication queue" };
  const adjudicatorIds = new Set((adjudicatorProfiles || []).map(profile => profile.id));

  const PAGE_SIZE = 50;
  let page = 0;
  let selectedPair = null;
  let annotationA: BlindAnnotation | null = null;
  let annotationB: BlindAnnotation | null = null;

  while (true) {
    const from = page * PAGE_SIZE;
    const to = (page + 1) * PAGE_SIZE - 1;

    const { data: pairs, error: pairsError } = await adminClient
      .from("research_pairs")
      .select("id, canonical_storage_path, scene_storage_path")
      .eq("status", "conflicted")
      .order("created_at", { ascending: true })
      .range(from, to);

    if (pairsError) return { error: "Failed to load adjudication queue" };
    if (!pairs || pairs.length === 0) {
      break;
    }

    for (const pair of pairs) {
      if (annotatedPairIds.has(pair.id)) {
        continue;
      }

      const { data: annotations, error: annotationsError } = await adminClient
        .from("annotations")
        .select("annotator_id, same_character, failure_reasons, anatomy_intact, text_free")
        .eq("pair_id", pair.id);

      if (annotationsError) return { error: "Failed to load adjudication queue" };

      if (
        annotations &&
        annotations.length === 2 &&
        !annotations.some(a => a.annotator_id === user.id || adjudicatorIds.has(a.annotator_id))
      ) {
        const [a1, a2] = annotations;
        
        if (isConsensus(a1, a2)) continue; // Not truly conflicted

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

    if (selectedPair) {
      break;
    }

    if (pairs.length < PAGE_SIZE) {
      break;
    }

    page++;
  }

  if (!selectedPair || !annotationA || !annotationB) {
    return { pair: null };
  }

  const { data: canonicalUrlData, error: canonicalUrlError } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(selectedPair.canonical_storage_path, 3600);
    
  const { data: sceneUrlData, error: sceneUrlError } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(selectedPair.scene_storage_path, 3600);

  if (canonicalUrlError || sceneUrlError || !canonicalUrlData?.signedUrl || !sceneUrlData?.signedUrl) {
    return { error: "Failed to load adjudication images" };
  }

  return {
    pair: {
      id: selectedPair.id,
      canonical_signed_url: canonicalUrlData.signedUrl,
      scene_signed_url: sceneUrlData.signedUrl
    },
    annotationA,
    annotationB
  };
}
