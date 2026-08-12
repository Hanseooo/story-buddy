"use client";

import { useState, useEffect, useRef } from "react";
import { supabase } from "@/lib/supabaseClient";

export type JobBucket =
  | "not-found"
  | "in-flight"
  | "paused"
  | "terminal-success"
  | "terminal-failure";

export type JobRow = {
  id: string;
  status: string;
  current_stage: string | null;
  failure_reason: string | null;
  input_text: string;
  pages: Array<{ scene_id: string; caption: string; image_path: string }>;
  reveal: {
    characters: Array<{
      char_id: string;
      name: string;
      image_path: string;
      chips: string[];
    }>;
    taps_left: number;
  } | null;
};

export function classify(row: JobRow | null): JobBucket {
  if (!row) return "not-found";
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
  refetch: () => Promise<void>;
} {
  // undefined = hook not yet initialized; null = SELECT returned no row
  const [row, setRow] = useState<JobRow | null | undefined>(undefined);
  const liveArrived = useRef(false);

  async function loadRow(force = false) {
    const { data } = await supabase
      .from("jobs")
      .select("id, status, current_stage, failure_reason, input_text, pages, reveal")
      .eq("id", jobId)
      .single();
    if (force || !liveArrived.current) {
      liveArrived.current = true;
      setRow(data as JobRow | null);
    }
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
          const newRow = payload.new;
          setRow(newRow);
          const b = classify(newRow);
          if (b === "terminal-success" || b === "terminal-failure") {
            supabase.removeChannel(channel);
          }
        }
      )
      .subscribe();

    // Seed: subscribe first, then SELECT — discard if live UPDATE already arrived
    loadRow();

    return () => {
      supabase.removeChannel(channel);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const bucket: JobBucket = row === undefined ? "in-flight" : classify(row);

  return {
    bucket,
    row: row ?? null,
    refetch: () => loadRow(true),
  };
}
