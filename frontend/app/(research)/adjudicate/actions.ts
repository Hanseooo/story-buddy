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

type AnnotationRow = BlindAnnotation & {
  annotator_id: string;
  round: number | null;
};

const ADJUDICATION_ROUND = 3;
const ORDINARY_ROUNDS = new Set([1, 2]);

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

function annotationRound(annotation: { round: number | null }) {
  return annotation.round ?? 1;
}

function hasValidRound(annotation: { round: number | null }) {
  const round = annotationRound(annotation);
  return Number.isInteger(round) && round >= 1 && round <= ADJUDICATION_ROUND;
}

function isAdjudicationRow(annotation: AnnotationRow, adjudicatorIds: Set<string>) {
  return annotationRound(annotation) >= ADJUDICATION_ROUND || adjudicatorIds.has(annotation.annotator_id);
}

function isSoloOrdinaryShape(ordinary: AnnotationRow[], userId: string) {
  return (
    ordinary.length === 2 &&
    ordinary.every(annotation => annotation.annotator_id === userId) &&
    ordinary.every(annotation => ORDINARY_ROUNDS.has(annotationRound(annotation))) &&
    new Set(ordinary.map(annotationRound)).size === 2
  );
}

export async function submitAdjudication(payload: SubmissionPayload) {
  const { pairId, failureReasons, sameCharacter, anatomyIntact, textFree } = payload;
  
  const { error: authError, user, isAdjudicator } = await verifyResearchAuth("any");
  if (authError || !user) return { error: authError || "Unauthorized" };

  const { error: validationError } = validateSubmissionPayload(payload);
  if (validationError) return { error: validationError };

  const supabase = await createSupabaseServerClient();

  const adminClient = await createAdminClient();

  // Validate that the pair is still conflicted
  const { data: pairInfo, error: pairError } = await adminClient
    .from("research_pairs")
    .select("status")
    .eq("id", pairId)
    .single();

  if (pairError || !pairInfo || pairInfo.status !== "conflicted") {
    return { error: "Pair is no longer conflicted" };
  }

  const { data: existingAnnotations, error: annotationsError } = await adminClient
    .from("annotations")
    .select("annotator_id, round, same_character, failure_reasons, anatomy_intact, text_free")
    .eq("pair_id", pairId);

  if (annotationsError || !existingAnnotations) {
    return { error: "Failed to verify prior annotations" };
  }

  if (existingAnnotations.some(annotation => !hasValidRound(annotation))) {
    return { error: "Invalid pair state: malformed annotation round" };
  }

  const { ids: adjudicatorIds, error: profileError } = await findAdjudicatorIds(
    adminClient,
    [...new Set(existingAnnotations.map(annotation => annotation.annotator_id))],
  );
  if (profileError) return { error: "Failed to verify prior annotators" };

  const rows = existingAnnotations as AnnotationRow[];
  const ordinary = rows.filter(annotation => !isAdjudicationRow(annotation, adjudicatorIds));
  const adjudications = rows.filter(annotation => isAdjudicationRow(annotation, adjudicatorIds));

  if (adjudications.length > 1) {
    return { error: "Invalid pair state: multiple adjudication rows" };
  }

  if (adjudications.length === 1 && rows.length === 2) {
    return { error: "Invalid pair state: prior annotations must be from ordinary annotators" };
  }

  if (ordinary.length !== 2) {
    return { error: "Invalid pair state: requires exactly 2 prior annotations" };
  }

  const soloOrdinary = isSoloOrdinaryShape(ordinary, user.id);

  if (!isAdjudicator && !soloOrdinary) {
    if (ordinary.some(annotation => annotation.annotator_id === user.id)) {
      return { error: "Ordinary researcher cannot adjudicate mixed self/other rows" };
    }
    return { error: "Ordinary researcher cannot adjudicate someone else's pair" };
  }

  if (isAdjudicator && ordinary.some(annotation => annotation.annotator_id === user.id)) {
    return { error: "Adjudicator cannot resolve their own annotations" };
  }

  if (adjudications.length === 1) {
    if (adjudications[0]?.annotator_id !== user.id) {
      return { error: "Pair already adjudicated by another adjudicator" };
    }
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
      round: ADJUDICATION_ROUND,
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
  const { error: authError, user, isAdjudicator } = await verifyResearchAuth("any");
  if (authError || !user) return { error: authError || "Unauthorized" };

  const adminClient = await createAdminClient();

  const { data: userAnnotations, error: annotationsError } = await adminClient
    .from("annotations")
    .select("pair_id, round")
    .eq("annotator_id", user.id);

  if (annotationsError) return { error: "Failed to load adjudication queue" };

  const adjudicatedPairIds = new Set(
    (userAnnotations || [])
      .filter(annotation => isAdjudicator || annotationRound(annotation) >= ADJUDICATION_ROUND)
      .map(a => a.pair_id)
  );

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
      if (adjudicatedPairIds.has(pair.id)) {
        continue;
      }

      const { data: annotations, error: annotationsError } = await adminClient
        .from("annotations")
        .select("annotator_id, round, same_character, failure_reasons, anatomy_intact, text_free")
        .eq("pair_id", pair.id);

      if (annotationsError) return { error: "Failed to load adjudication queue" };

      if (!annotations || annotations.some(annotation => !hasValidRound(annotation))) {
        continue;
      }

      const rows = annotations as AnnotationRow[];
      const ordinary = rows.filter(annotation => !isAdjudicationRow(annotation, adjudicatorIds));
      const adjudications = rows.filter(annotation => isAdjudicationRow(annotation, adjudicatorIds));
      const soloOrdinary = isSoloOrdinaryShape(ordinary, user.id);
      const distinctAdjudicatorShape = isAdjudicator && ordinary.length === 2 && !ordinary.some(a => a.annotator_id === user.id);

      if (adjudications.length === 0 && (soloOrdinary || distinctAdjudicatorShape)) {
        const [a1, a2] = ordinary;
        
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
