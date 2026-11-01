"use client";

import { useState, useEffect, useRef } from "react";
import { supabase } from "@/lib/supabaseClient";

export type JobBucket =
  | "not-found"
  | "in-flight"
  | "paused"
  | "teacher-held"
  | "stopped"
  | "terminal-success"
  | "terminal-failure";

export type JobRow = {
  id: string;
  status: string;
  moderation_mode?: "baseline" | "teacher_review_v1";
  generation_epoch?: number;
  current_stage: string | null;
  failure_reason: string | null;
  profile_id: string;
  input_text: string;
  title: string | null;
  style_preset_id: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  // `other_versions`: magic-pencil 09, a page with two kept attempts on a feature job (AC-13).
  pages: Array<{ scene_id: string; caption: string; image_path: string; other_versions?: boolean }>;
  reveal: {
    characters: Array<{
      char_id: string;
      name: string;
      image_path: string;
      chips: string[];
      // Magic pencil (ADR-082): absent unless the job was submitted with the setting on.
      versions?: Array<{ version_id: string; image_path: string }>;
      // Unchosen first-round draws nobody has opened, by id only; moderated on open (ticket 05).
      unreviewed?: string[];
      // A pencil result waiting for "Keep this" or "Use the old one"; `image_path` is the old picture (ticket 06).
      pencil_choice?: { use_id: string; version_id: string; image_path: string } | null;
      // The edit model refused the latest pencil change of this picture (SH-04).
      pencil_refused?: boolean;
      // Only a classifier-passed picture can come back as "the old one" (AC-11).
      pencil_ready?: boolean;
    }>;
    taps_left: number;
  } | null;
};

export function classify(row: JobRow | null): JobBucket {
  if (!row) return "not-found";
  if (row.status === "awaiting_teacher") return "teacher-held";
  if (row.status === "stopped") return "stopped";
  if (row.status === "complete" && row.pages.length > 0) return "terminal-success";
  if (row.status === "awaiting_confirm") return "paused";
  if (row.status === "queued" || row.status === "running") return "in-flight";
  if (row.status === "failed") return "terminal-failure";
  // ponytail: fail-safe — unknown status (swept pause, future values) → retry, never a blank screen
  return "terminal-failure";
}

export function useJob(jobId: string): {
  bucket: JobBucket;
  row: JobRow | null;
  refetch: () => Promise<boolean>;
} {
  // undefined = hook not yet initialized; null = SELECT returned no row
  const [row, setRow] = useState<JobRow | null | undefined>(undefined);
  // true = the read itself failed, as opposed to succeeding with no row
  const [readFailed, setReadFailed] = useState(false);
  const liveArrived = useRef(false);

  async function loadRow(force = false): Promise<boolean> {
    const { data, error } = await supabase
      .from("jobs")
      // `profile_id` is who owns the book, not who is reading it: RLS lets a classmate read an
      // approved peer row whole, so every consumer of `input_text` has to be able to tell the
      // owner's own story text from someone else's (story-titles §5).
      .select("id, status, moderation_mode, generation_epoch, current_stage, failure_reason, profile_id, input_text, title, style_preset_id, approved_at, rejected_at, pages, reveal")
      .eq("id", jobId)
      .single();
    // PGRST116 is `.single()` matching zero rows — the book is genuinely absent, or RLS hid it
    // (indistinguishable by design, and both are "not yours to read"). Any other error is the
    // read failing: a blip, a 5xx, an expired session. Telling a child their story does not
    // exist because the network hiccuped is the bug this distinguishes.
    const readFailure = Boolean(error) && error?.code !== "PGRST116";
    // A forced refresh must not overwrite a good row with a failed read: the caller re-enables a
    // paid action on the strength of what it reads back. An absent row is not a failed read — it
    // is the answer, and the job still has to reclassify, or the page waits on a row that is gone.
    if (force && readFailure) return false;
    if (force || !liveArrived.current) {
      liveArrived.current = true;
      setReadFailed(readFailure);
      setRow(data as JobRow | null);
    }
    // Matches the comment above: an absent row is a completed refresh whose answer is "gone",
    // not a failed one. Returning false for it told the caller it had learned nothing.
    return !readFailure;
  }

  useEffect(() => {
    liveArrived.current = false;

    const channel = supabase
      .channel(`job-${jobId}`)
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "jobs", filter: `id=eq.${jobId}` },
        (payload: { new: JobRow }) => {
          liveArrived.current = true;
          setReadFailed(false);
          const newRow = payload.new;
          setRow(newRow);
          const b = classify(newRow);
          // Completed books can still gain or lose teacher approval while the reader is open.
          if (b === "terminal-failure" && newRow.moderation_mode !== "teacher_review_v1") {
            supabase.removeChannel(channel);
          }
        }
      )
      .subscribe();

    // Seed: subscribe first, then SELECT — discard if live UPDATE already arrived
    loadRow();

    function onVisibility() {
      if (document.visibilityState === "visible") void loadRow(true);
    }
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      supabase.removeChannel(channel);
      document.removeEventListener("visibilitychange", onVisibility);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const bucket: JobBucket =
    row === undefined ? "in-flight" : readFailed ? "terminal-failure" : classify(row);

  return {
    bucket,
    row: row ?? null,
    refetch: () => loadRow(true),
  };
}
