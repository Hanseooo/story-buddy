export interface JobRow {
  id: string;
  status: string;
  created_at: string;
  style_preset_id?: string | null;
  classroom_id?: string | null;
  failure_reason?: string | null;
  regen_count?: number | null;
  scenes_total?: number | null;
  scenes_passed?: number | null;
  usd_estimate?: number | null;
  langfuse_trace_url?: string | null;
}

export function computeAggregates(jobs: JobRow[]) {
  const totalRuns = jobs.length;
  const complete = jobs.filter((j) => j.status === "complete").length;
  const failed = jobs.filter((j) => j.status === "failed").length;
  // queued / running / awaiting_confirm — see migration 0005's status CHECK.
  const inProgress = totalRuns - complete - failed;

  let totalRegens = 0;
  let estCost = 0;
  let sumPassed = 0;
  let sumTotalScenes = 0;

  for (const job of jobs) {
    if (job.regen_count != null) {
      totalRegens += job.regen_count;
    }
    if (job.usd_estimate != null) {
      estCost += Number(job.usd_estimate);
    }
    if (job.scenes_passed != null) {
      sumPassed += job.scenes_passed;
    }
    if (job.scenes_total != null) {
      sumTotalScenes += job.scenes_total;
    }
  }

  // Two different questions, deliberately kept apart. A failed job usually never writes
  // scenes_total, so it is absent from BOTH sides of scenePassRate — that fraction only ever
  // describes runs that got far enough to be judged. jobPassRate is what answers "did the
  // pipeline deliver a book"; in-progress runs are excluded rather than counted as losses.
  const scenePassRate = sumTotalScenes > 0 ? sumPassed / sumTotalScenes : 0;
  const concluded = complete + failed;
  const jobPassRate = concluded > 0 ? complete / concluded : 0;

  return {
    totalRuns,
    complete,
    failed,
    inProgress,
    totalRegens,
    estCost,
    scenePassRate,
    jobPassRate,
  };
}

// ADR-025's closed set (backend/worker/run_job.py). Unknown values pass through as-is.
const FAILURE_LABELS: Record<string, string> = {
  machine: "Pipeline error",
  child_text: "Content blocked",
};

export function failureLabel(reason: string): string {
  return FAILURE_LABELS[reason] ?? reason;
}

export function formatJob(job: JobRow) {
  return {
    shortId: job.id ? job.id.slice(0, 8) : "—",
    formattedDate: job.created_at
      ? new Date(job.created_at).toLocaleString(undefined, {
          month: "short",
          day: "numeric",
          hour: "numeric",
          minute: "2-digit",
        })
      : "—",
    scenesDisplay:
      job.scenes_total != null
        ? `${job.scenes_passed ?? 0}/${job.scenes_total}`
        : "—",
    costDisplay:
      job.usd_estimate != null ? `$${Number(job.usd_estimate).toFixed(4)}` : "—",
  };
}
