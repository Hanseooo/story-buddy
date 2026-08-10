export interface JobRow {
  id: string;
  status: string;
  created_at: string;
  style_preset_id?: string | null;
  classroom_id?: string | null;
  failure_reason?: string | null;
  image_count?: number | null;
  regen_count?: number | null;
  ref_retry_count?: number | null;
  scenes_total?: number | null;
  scenes_passed?: number | null;
  scenes_failed?: number | null;
  scenes_unchecked?: number | null;
  usd_estimate?: number | null;
  langfuse_trace_url?: string | null;
}

export function computeAggregates(jobs: JobRow[]) {
  const totalRuns = jobs.length;
  const complete = jobs.filter((j) => j.status === "complete").length;
  const failed = jobs.filter((j) => j.status === "failed").length;

  let totalImages = 0;
  let totalRegens = 0;
  let estCost = 0;
  let sumPassed = 0;
  let sumTotalScenes = 0;

  for (const job of jobs) {
    if (job.status === "complete" && job.image_count != null) {
      totalImages += job.image_count;
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

  const passRate = sumTotalScenes > 0 ? sumPassed / sumTotalScenes : 0;

  return {
    totalRuns,
    complete,
    failed,
    totalImages,
    totalRegens,
    estCost,
    passRate,
  };
}
