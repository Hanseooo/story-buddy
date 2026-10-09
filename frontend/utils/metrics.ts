export interface JobRow {
  id: string;
  status: string;
  created_at: string;
  style_preset_id?: string | null;
  classroom_id?: string | null;
  failure_reason?: string | null;
  regen_count?: number | null;
  image_count?: number | null;
  scenes_total?: number | null;
  scenes_passed?: number | null;
  scenes_unchecked?: number | null;
  usd_estimate?: number | null;
  langfuse_trace_url?: string | null;
  approved_at?: string | null;
  title?: string | null;
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
  const failedByReason: Record<string, number> = {};
  let uncheckedPages = 0;
  let imageSum = 0;
  let pagesWithImages = 0;

  for (const job of jobs) {
    if (job.status === "failed") {
      const reason = job.failure_reason ?? "unrecorded";
      failedByReason[reason] = (failedByReason[reason] ?? 0) + 1;
    }
    if (job.scenes_unchecked != null) {
      uncheckedPages += job.scenes_unchecked;
    }
    // Only runs that recorded both: a failed run usually wrote image_count but never scenes_total.
    if (job.image_count != null && job.scenes_total != null) {
      imageSum += job.image_count;
      pagesWithImages += job.scenes_total;
    }
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
    failedByReason,
    uncheckedPages,
    imagesPerPage: pagesWithImages > 0 ? imageSum / pagesWithImages : null,
    pagesTotal: sumTotalScenes,
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

export function failedSplit(byReason: Record<string, number>): string {
  return Object.entries(byReason)
    .sort(([, a], [, b]) => b - a)
    .map(([reason, n]) => `${n} ${reason === "unrecorded" ? "no reason recorded" : failureLabel(reason).toLowerCase()}`)
    .join(" · ");
}

export type StyleRow = {
  style: string | null;
  runs: number;
  jobPassRate: number | null;
  pagePassRate: number | null;
  avgCost: number | null;
};

export function styleBreakdown(jobs: JobRow[]): StyleRow[] {
  const groups = new Map<string | null, JobRow[]>();
  for (const job of jobs) {
    const key = job.style_preset_id ?? null;
    const rows = groups.get(key);
    if (rows) rows.push(job);
    else groups.set(key, [job]);
  }
  return [...groups]
    .map(([style, rows]) => {
      const stats = computeAggregates(rows);
      const costed = rows.filter((row) => row.usd_estimate != null);
      return {
        style,
        runs: rows.length,
        jobPassRate: stats.complete + stats.failed > 0 ? stats.jobPassRate : null,
        pagePassRate: stats.pagesTotal > 0 ? stats.scenePassRate : null,
        avgCost:
          costed.length > 0
            ? costed.reduce((sum, row) => sum + Number(row.usd_estimate), 0) / costed.length
            : null,
      };
    })
    .sort((a, b) => (a.style === null ? 1 : b.style === null ? -1 : b.runs - a.runs));
}

export type RunStatusFilter = "all" | "complete" | "failed" | "in_progress";
export type RunFilter = { status: RunStatusFilter; style: string };

const STATUS_FILTERS: RunStatusFilter[] = ["all", "complete", "failed", "in_progress"];

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function parseRunFilter(params: Record<string, string | string[] | undefined>): RunFilter {
  const status = first(params.status);
  return {
    status: STATUS_FILTERS.includes(status as RunStatusFilter) ? (status as RunStatusFilter) : "all",
    style: first(params.style) || "all",
  };
}

export function filterJobs(jobs: JobRow[], filter: RunFilter): JobRow[] {
  return jobs.filter((job) => {
    const status =
      filter.status === "all" ||
      (filter.status === "in_progress"
        ? job.status !== "complete" && job.status !== "failed"
        : job.status === filter.status);
    const style =
      filter.style === "all" ||
      (filter.style === "none" ? job.style_preset_id == null : job.style_preset_id === filter.style);
    return status && style;
  });
}

export const STATUS_LABELS: Record<string, string> = {
  complete: "Complete",
  failed: "Failed",
  queued: "Queued",
  running: "Running",
  awaiting_confirm: "Waiting for the child",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

// sessionStorage key: the list writes its query here, the run page's back link reads it.
export const RUNS_QUERY_KEY = "research-runs-query";

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
