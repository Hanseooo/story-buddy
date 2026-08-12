import { createClient } from "@supabase/supabase-js";
import { computeAggregates, failureLabel, formatJob, JobRow } from "@/utils/metrics";
import { ArrowRight, CheckCircle, XCircle, Clock, ArrowLeft, Info } from "@phosphor-icons/react/dist/ssr";
import Link from "next/link";

export const revalidate = 0;

export default async function ResearchPage() {
  const supabase = createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!
  );

  const { data: jobsData, error } = await supabase
    .from("jobs")
    .select(`
      id, status, created_at, style_preset_id,
      failure_reason, regen_count,
      scenes_total, scenes_passed,
      usd_estimate, langfuse_trace_url
    `)
    .order("created_at", { ascending: false });

  if (error) {
    throw new Error(error.message);
  }

  const jobs: JobRow[] = jobsData || [];
  const stats = computeAggregates(jobs);

  return (
    <div className="min-h-[100dvh] bg-background p-4 sm:p-6 lg:p-10 text-foreground font-sans">
      <div className="mx-auto max-w-7xl space-y-8 lg:space-y-12">
        
        {/* Header */}
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between border-b border-primary/10 pb-4">
            <Link 
              href="/research"
              className="inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:text-primary-deep transition-colors w-fit"
            >
              <ArrowLeft weight="bold" className="w-4 h-4" />
              Back to Methodology
            </Link>

            <div className="flex items-center gap-2 select-none">
              <div className="grid size-7 sm:size-8 place-items-center rounded-[9px_9px_9px_3px] overflow-hidden bg-surface shadow-sm shrink-0">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.png" alt="" className="h-full w-full object-contain scale-[1.35]" />
              </div>
              <span className="font-display text-lg font-extrabold text-primary tracking-tight hidden sm:block">
                StoryBuddy
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <h1 className="text-4xl md:text-5xl font-display font-extrabold tracking-tight text-foreground">
              Research Metrics
            </h1>
            <p className="text-base text-foreground/70 max-w-[65ch]">
              Aggregate run analytics and per-job Langfuse trace breakdowns.
            </p>

            <details className="group mt-2">
              <summary className="inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:text-primary-deep cursor-pointer select-none list-none [&::-webkit-details-marker]:hidden transition-colors w-fit">
                <Info weight="bold" className="w-4 h-4 transition-transform group-open:rotate-12" />
                How are these calculated?
              </summary>
              <div className="mt-4 p-4 sm:p-5 rounded-2xl bg-surface neo-border neo-shadow-sm text-sm text-foreground/80 space-y-3 max-w-3xl leading-relaxed">
                <p><strong className="text-foreground">Job Pass Rate:</strong> Percentage of <em>concluded</em> jobs marked <span className="text-success font-bold">complete</span> versus <span className="text-destructive font-bold">failed</span>. Moderation blocks or unrecoverable pipeline errors count as failed. Runs still in progress are excluded from both sides.</p>
                <p><strong className="text-foreground">Scene Pass Rate:</strong> Percentage of individual scenes that cleared the consistency judge, across every job that got far enough to be judged. A job that fails before generating a scene records nothing here, so this measures judge yield — not pipeline reliability.</p>
                <p><strong className="text-foreground">Est. Total Cost:</strong> Sum of estimated USD costs for all jobs based on OpenRouter (LLM) and Fal.ai (Image) usage. Varies by model preset.</p>
                <p><strong className="text-foreground">Scenes:</strong> Represented as <code className="px-1.5 py-0.5 rounded-md bg-muted/50 font-mono text-xs font-bold text-primary">Passed / Total</code>. E.g., <code>4/6</code> means 4 scenes passed the consistency judge before the job concluded or failed.</p>
                <p><strong className="text-foreground">Regens:</strong> The total number of times the Gemma consistency judge rejected an image and forced a regeneration loop.</p>
              </div>
            </details>
          </div>
        </div>

        {/* Aggregate Stats Grid */}
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <div className="rounded-3xl neo-border bg-surface p-5 sm:p-6 neo-shadow-sm flex flex-col justify-between gap-4">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Total Runs</div>
            <div className="text-4xl font-display font-extrabold text-foreground">{stats.totalRuns}</div>
          </div>
          <div className="rounded-3xl neo-border bg-surface p-5 sm:p-6 neo-shadow-sm flex flex-col justify-between gap-4">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Job Pass Rate</div>
            <div className="flex flex-col gap-1">
              <div className="text-4xl font-display font-extrabold text-primary">
                {(stats.jobPassRate * 100).toFixed(1)}%
              </div>
              <div className="text-xs font-medium text-foreground/40">
                {stats.complete}/{stats.complete + stats.failed} concluded
              </div>
            </div>
          </div>
          <div className="rounded-3xl neo-border bg-surface p-5 sm:p-6 neo-shadow-sm flex flex-col justify-between gap-4">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Scene Pass Rate</div>
            <div className="flex flex-col gap-1">
              <div className="text-4xl font-display font-extrabold text-foreground">
                {(stats.scenePassRate * 100).toFixed(1)}%
              </div>
              <div className="text-xs font-medium text-foreground/40">judge yield</div>
            </div>
          </div>
          <div className="rounded-3xl neo-border bg-surface p-5 sm:p-6 neo-shadow-sm flex flex-col justify-between gap-4">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Est. Total Cost</div>
            <div className="flex items-baseline gap-1">
              <div className="text-4xl font-display font-extrabold text-foreground">${stats.estCost.toFixed(2)}</div>
              <div className="text-xs font-medium text-foreground/40">USD</div>
            </div>
          </div>
        </div>

        {/* Status breakdown — these three sum to Total Runs */}
        <div className="grid grid-cols-1 gap-3 sm:gap-4 sm:grid-cols-3">
          <div className="rounded-2xl neo-border bg-surface p-4 neo-shadow-sm flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Complete</div>
            <div className="text-xl font-display font-bold text-success flex items-center gap-2">
              {stats.complete} <CheckCircle weight="fill" className="w-5 h-5" />
            </div>
          </div>
          <div className="rounded-2xl neo-border bg-surface p-4 neo-shadow-sm flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Failed</div>
            <div className="text-xl font-display font-bold text-destructive flex items-center gap-2">
              {stats.failed} <XCircle weight="fill" className="w-5 h-5" />
            </div>
          </div>
          <div className="rounded-2xl neo-border bg-surface p-4 neo-shadow-sm flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">In Progress</div>
            <div className="text-xl font-display font-bold text-foreground/70 flex items-center gap-2">
              {stats.inProgress} <Clock weight="fill" className="w-5 h-5" />
            </div>
          </div>
        </div>

        {/* Per-Run History Section */}
        <div className="space-y-4">
          <h2 className="text-2xl font-display font-bold text-foreground">Recent Jobs</h2>

          {/* Desktop Table (hidden on mobile) */}
          <div className="hidden md:block overflow-hidden rounded-3xl neo-border bg-surface neo-shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-foreground/80">
                <thead className="border-b border-muted bg-muted/20 text-xs font-semibold uppercase tracking-wider text-foreground/50">
                  <tr>
                    <th scope="col" className="px-6 py-4">Job ID</th>
                    <th scope="col" className="px-6 py-4">Status</th>
                    <th scope="col" className="px-6 py-4">Created</th>
                    <th scope="col" className="px-6 py-4">Style</th>
                    <th scope="col" className="px-6 py-4">Scenes</th>
                    <th scope="col" className="px-6 py-4">Regens</th>
                    <th scope="col" className="px-6 py-4">Cost</th>
                    <th scope="col" className="px-6 py-4 text-right">Trace</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-muted/40">
                  {jobs.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-6 py-12 text-center text-foreground/50">
                        No jobs recorded yet.
                      </td>
                    </tr>
                  ) : (
                    jobs.map((job) => {
                      const { shortId, formattedDate, scenesDisplay, costDisplay } = formatJob(job);

                      return (
                        <tr key={job.id} className="hover:bg-muted/10 transition-colors">
                          <td className="whitespace-nowrap px-6 py-4 font-mono font-medium text-foreground">
                            {shortId}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4">
                            <span
                              className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider ${
                                job.status === "complete"
                                  ? "bg-success/15 text-success"
                                  : job.status === "failed"
                                  ? "bg-destructive/15 text-destructive"
                                  : "bg-muted text-foreground/70"
                              }`}
                            >
                              {job.status}
                            </span>
                            {job.status === "failed" && job.failure_reason && (
                              <div className="mt-1 max-w-xs truncate text-[11px] text-destructive/80 font-medium" title={job.failure_reason}>
                                {failureLabel(job.failure_reason)}
                              </div>
                            )}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-xs text-foreground/60 font-medium">
                            {formattedDate}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-xs text-foreground/80 font-medium">
                            {job.style_preset_id || "—"}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-foreground/70">
                            {scenesDisplay}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-foreground/70">
                            {job.regen_count ?? "—"}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 font-mono text-xs text-foreground/70">
                            {costDisplay}
                          </td>
                          <td className="whitespace-nowrap px-6 py-4 text-right">
                            {job.langfuse_trace_url ? (
                              <a
                                href={job.langfuse_trace_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center justify-end gap-1.5 font-bold text-primary hover:text-primary-deep transition-colors"
                              >
                                View
                                <ArrowRight weight="bold" className="h-4 w-4" />
                              </a>
                            ) : (
                              <span className="text-foreground/30">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Mobile Stacked Cards (hidden on desktop) */}
          <div className="grid grid-cols-1 gap-4 md:hidden">
            {jobs.length === 0 ? (
              <div className="rounded-3xl neo-border bg-surface p-8 text-center text-foreground/50 neo-shadow-sm">
                No jobs recorded yet.
              </div>
            ) : (
              jobs.map((job) => {
                const { shortId, formattedDate, scenesDisplay, costDisplay } = formatJob(job);

                return (
                  <div key={job.id} className="rounded-2xl neo-border bg-surface p-5 neo-shadow-sm flex flex-col gap-4">
                    {/* Card Header: ID & Status */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex flex-col gap-1">
                        <div className="font-mono font-bold text-foreground text-base">
                          {shortId}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-foreground/50 font-medium">
                          <Clock weight="bold" className="w-3.5 h-3.5" />
                          {formattedDate}
                        </div>
                      </div>
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider ${
                          job.status === "complete"
                            ? "bg-success/15 text-success"
                            : job.status === "failed"
                            ? "bg-destructive/15 text-destructive"
                            : "bg-muted text-foreground/70"
                        }`}
                      >
                        {job.status}
                      </span>
                    </div>

                    {/* Failure Reason if failed */}
                    {job.status === "failed" && job.failure_reason && (
                      <div className="rounded-lg bg-destructive/10 p-3 text-xs text-destructive/90 font-medium">
                        {failureLabel(job.failure_reason)}
                      </div>
                    )}

                    {/* Metric Row */}
                    <div className="grid grid-cols-3 gap-2 py-3 border-y border-muted/40">
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Scenes</span>
                        <span className="font-mono text-sm font-medium text-foreground/80 mt-0.5">{scenesDisplay}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Regens</span>
                        <span className="font-mono text-sm font-medium text-foreground/80 mt-0.5">{job.regen_count ?? "—"}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Cost</span>
                        <span className="font-mono text-sm font-medium text-foreground/80 mt-0.5">{costDisplay}</span>
                      </div>
                    </div>

                    {/* Footer: Style & Trace Link */}
                    <div className="flex items-center justify-between">
                      <div className="text-xs font-medium text-foreground/60">
                        {job.style_preset_id ? (
                          <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-muted/40">
                            {job.style_preset_id}
                          </span>
                        ) : "No Style"}
                      </div>
                      {job.langfuse_trace_url ? (
                        <a
                          href={job.langfuse_trace_url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1.5 text-sm font-bold text-primary hover:text-primary-deep transition-colors"
                        >
                          View Trace
                          <ArrowRight weight="bold" className="h-4 w-4" />
                        </a>
                      ) : (
                        <span className="text-xs text-foreground/30 font-medium">No trace</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
