"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "@/utils/supabase/server";
import { createAdminClient } from "@/utils/supabase/admin";

import { verifyResearchAuth } from "../_shared/actions";
import { validateSubmissionPayload, type SubmissionPayload, isConsensus } from "../_shared/validation";

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
    const { error } = await adminClient
      .from("research_pairs")
      .update({ status: "partially_annotated" })
      .eq("id", pairId);
    if (error) return { error: "Saved, but failed to update queue status" };
  } else if (count === 2) {
    // Fetch both to see if they agree
    const { data: annotations, error: annotationsError } = await adminClient
      .from("annotations")
      .select("same_character, failure_reasons, anatomy_intact, text_free")
      .eq("pair_id", pairId);

    if (annotationsError) return { error: "Saved, but failed to update queue status" };
      
    if (annotations && annotations.length === 2) {
      const [a1, a2] = annotations;
      
      const agree = isConsensus(a1, a2);
                    
      const newStatus = agree ? "complete" : "conflicted";
      const { error } = await adminClient
        .from("research_pairs")
        .update({ status: newStatus })
        .eq("id", pairId);
      if (error) return { error: "Saved, but failed to update queue status" };
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

  const { data: userAnnotations, error: annotationsError } = await adminClient
    .from("annotations")
    .select("pair_id")
    .eq("annotator_id", user.id);

  if (annotationsError) {
    return { error: "Failed to load annotation queue" };
  }

  const annotatedPairIds = new Set((userAnnotations || []).map(a => a.pair_id));

  const PAGE_SIZE = 50;
  let page = 0;
  const unannotatedPairs: Array<{ id: string; canonical_storage_path: string; scene_storage_path: string }> = [];

  while (true) {
    const from = page * PAGE_SIZE;
    const to = (page + 1) * PAGE_SIZE - 1;

    const { data: pairs, error: pairsError } = await adminClient
      .from("research_pairs")
      .select("id, canonical_storage_path, scene_storage_path")
      .in("status", ["pending", "partially_annotated"])
      .order("created_at", { ascending: true })
      .range(from, to);

    if (pairsError) {
      return { error: "Failed to load annotation queue" };
    }

    if (!pairs || pairs.length === 0) {
      break;
    }

    const available = pairs.filter(p => !annotatedPairIds.has(p.id));
    unannotatedPairs.push(...available);

    if (pairs.length < PAGE_SIZE) {
      break;
    }

    page++;
  }

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
  const { data: canonicalUrlData, error: canonicalUrlError } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(nextPair.canonical_storage_path, 3600);
    
  const { data: sceneUrlData, error: sceneUrlError } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(nextPair.scene_storage_path, 3600);

  if (canonicalUrlError || sceneUrlError || !canonicalUrlData?.signedUrl || !sceneUrlData?.signedUrl) {
    return { error: "Failed to load annotation images" };
  }

  return {
    pair: {
      id: nextPair.id,
      canonical_signed_url: canonicalUrlData.signedUrl,
      scene_signed_url: sceneUrlData.signedUrl
    }
  };
}
