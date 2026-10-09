import { createClient } from "@supabase/supabase-js";
import Link from "next/link";
import { CheckCircle, Clock, Lock, XCircle } from "@phosphor-icons/react/dist/ssr";
import LangfuseButton from "@/components/LangfuseButton";
import {
  computeAggregates,
  failedSplit,
  failureLabel,
  filterJobs,
  formatJob,
  JobRow,
  langfuseLinksOn,
  parseRunFilter,
  styleBreakdown,
} from "@/utils/metrics";
import { getResearchViewer } from "../../_shared/getResearchViewer";
import { canOpenRun, hideTitles, ResearchViewer } from "../../_shared/viewer";
import RunFilters from "./RunFilters";
import StatusPill from "./StatusPill";

export const revalidate = 0;

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

const pct = (rate: number | null) => (rate == null ? "—" : `${(rate * 100).toFixed(1)}%`);
const usd = (value: number | null) => (value == null ? "—" : `$${value.toFixed(4)}`);

function Tile({ label, value, note, tone = "text-foreground" }: { label: string; value: string; note: string; tone?: string }) {
  return (
    <div className="flex flex-col justify-between gap-3 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6">
      <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">{label}</div>
      <div className={`font-display text-3xl font-extrabold sm:text-4xl ${tone}`}>{value}</div>
      <p className="text-xs font-medium text-foreground/50">{note}</p>
    </div>
  );
}

function RunName({ job, viewer }: { job: JobRow; viewer: ResearchViewer | null }) {
  const name = job.title ?? `Run ${formatJob(job).shortId}`;
  if (canOpenRun(viewer, job)) {
    // after:inset-0 stretches this link over its row or card, so the whole row opens the run.
    return (
      <Link
        href={`/research/metrics/${job.id}`}
        aria-label={`Open run ${job.title ?? formatJob(job).shortId}`}
        className={`inline-flex min-h-11 items-center break-words font-bold text-foreground after:absolute after:inset-0 hover:text-primary ${FOCUS}`}
      >
        {name}
      </Link>
    );
  }
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono font-medium text-foreground">{name}</span>
      <span className="inline-flex items-center gap-1 text-xs text-foreground/60">
        <Lock weight="bold" className="size-3.5" aria-hidden />
        {viewer === null ? (
          <Link
            href={`/login?next=/research/metrics/${job.id}`}
            className={`relative z-10 inline-flex min-h-11 items-center font-bold text-primary hover:underline ${FOCUS}`}
          >
            Sign in to view
          </Link>
        ) : viewer.role === "researcher" ? (
          "Not approved yet"
        ) : (
          "Researchers only"
        )}
      </span>
    </div>
  );
}

export default async function RunsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);
  const [viewer, { data, error }] = await Promise.all([
    getResearchViewer(),
    supabase
      .from("jobs")
      .select(`
        id, status, created_at, style_preset_id, failure_reason, regen_count, image_count,
        scenes_total, scenes_passed, scenes_unchecked, usd_estimate, langfuse_trace_url,
        approved_at, title
      `)
      .order("created_at", { ascending: false }),
  ]);
  if (error) throw new Error(error.message);

  // A title is redacted (ADR-059) but can still identify a donated story (#108). It leaves the
  // server only for a viewer who can open that run.
  const jobs = hideTitles(viewer, (data ?? []) as JobRow[]);
  const stats = computeAggregates(jobs);
  const byStyle = styleBreakdown(jobs);
  const filter = parseRunFilter(await searchParams);
  const shown = filterJobs(jobs, filter);
  const styleIds = byStyle.flatMap((row) => (row.style ? [row.style] : []));
  const hasNoStyle = byStyle.some((row) => row.style === null);
  const showTrace = langfuseLinksOn();
  const concluded = stats.complete + stats.failed;

  return (
    <main className="mx-auto max-w-7xl space-y-8 p-4 font-sans sm:p-6 lg:space-y-10 lg:p-10">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Runs</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          Every story the pipeline has run, with research totals. Signed-in researchers can open a run to see the
          path it took through the graph.
        </p>
      </div>

      <section aria-label="Totals" className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
        <Tile label="Total runs" value={String(stats.totalRuns)} note="Every submitted story, newest first below." />
        <Tile
          label="Job pass rate"
          value={pct(concluded > 0 ? stats.jobPassRate : null)}
          note={`${stats.complete} of ${concluded} finished runs made a book.`}
          tone="text-primary"
        />
        <Tile
          label="Page pass rate"
          value={pct(stats.pagesTotal > 0 ? stats.scenePassRate : null)}
          note="Pages the judge passed, across runs that drew pages."
        />
        <Tile label="Est. total cost" value={`$${stats.estCost.toFixed(2)}`} note="Estimated OpenRouter and fal.ai spend, USD." />
        <Tile label="Unchecked pages" value={String(stats.uncheckedPages)} note="Pages the judge gave no answer on." />
        <Tile
          label="Images per page"
          value={stats.imagesPerPage == null ? "—" : stats.imagesPerPage.toFixed(2)}
          note="1.0 means no redraws."
        />
      </section>

      <section aria-label="Status" className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
        <div className="flex items-center justify-between rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Complete</div>
          <div className="flex items-center gap-2 font-display text-xl font-bold text-success">
            {stats.complete} <CheckCircle weight="fill" className="size-5" aria-hidden />
          </div>
        </div>
        <div className="flex flex-col gap-1 rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Failed</div>
            <div className="flex items-center gap-2 font-display text-xl font-bold text-destructive">
              {stats.failed} <XCircle weight="fill" className="size-5" aria-hidden />
            </div>
          </div>
          {stats.failed > 0 && <p className="text-xs font-medium text-foreground/60">{failedSplit(stats.failedByReason)}</p>}
        </div>
        <div className="flex items-center justify-between rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">In progress</div>
          <div className="flex items-center gap-2 font-display text-xl font-bold text-foreground/70">
            {stats.inProgress} <Clock weight="fill" className="size-5" aria-hidden />
          </div>
        </div>
      </section>

      {byStyle.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-display text-2xl font-bold">By style</h2>
          <div className="overflow-x-auto rounded-2xl bg-surface neo-border neo-shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-muted bg-muted/20 text-xs font-semibold uppercase tracking-wider text-foreground/50">
                <tr>
                  <th scope="col" className="px-4 py-3">Style</th>
                  <th scope="col" className="px-4 py-3">Runs</th>
                  <th scope="col" className="px-4 py-3">Job pass</th>
                  <th scope="col" className="px-4 py-3">Page pass</th>
                  <th scope="col" className="px-4 py-3">Avg cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-muted/40 font-mono text-xs">
                {byStyle.map((row) => (
                  <tr key={row.style ?? "none"}>
                    <th scope="row" className="px-4 py-3 font-sans font-bold">{row.style ?? "No style"}</th>
                    <td className="px-4 py-3">{row.runs}</td>
                    <td className="px-4 py-3">{pct(row.jobPassRate)}</td>
                    <td className="px-4 py-3">{pct(row.pagePassRate)}</td>
                    <td className="px-4 py-3">{usd(row.avgCost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 className="font-display text-2xl font-bold">All runs</h2>
          {shown.length > 0 && <RunFilters styles={styleIds} hasNoStyle={hasNoStyle} />}
        </div>

        {jobs.length === 0 ? (
          <div className="rounded-3xl bg-surface p-8 text-center neo-border neo-shadow-sm">
            <p className="font-bold">No runs recorded yet.</p>
            <p className="mt-1 text-sm text-foreground/60">A run appears here when a student submits a story.</p>
          </div>
        ) : shown.length === 0 ? (
          <div className="flex flex-col items-center gap-4 rounded-3xl bg-surface p-8 text-center neo-border neo-shadow-sm">
            <p className="font-bold">No runs match these filters</p>
            <RunFilters styles={styleIds} hasNoStyle={hasNoStyle} />
          </div>
        ) : (
          <>
            <div className="hidden overflow-x-auto rounded-3xl bg-surface neo-border neo-shadow-sm md:block">
              <table className="w-full text-left text-sm text-foreground/80">
                <thead className="border-b border-muted bg-muted/20 text-xs font-semibold uppercase tracking-wider text-foreground/50">
                  <tr>
                    <th scope="col" className="px-6 py-4">Run</th>
                    <th scope="col" className="px-6 py-4">Status</th>
                    <th scope="col" className="px-6 py-4">Style</th>
                    <th scope="col" className="px-6 py-4">Pages</th>
                    <th scope="col" className="px-6 py-4">Redraws</th>
                    <th scope="col" className="px-6 py-4">Cost</th>
                    <th scope="col" className="px-6 py-4">Created</th>
                    {showTrace && <th scope="col" className="px-6 py-4 text-right">Trace</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-muted/40">
                  {shown.map((job) => {
                    const { shortId, formattedDate, scenesDisplay, costDisplay } = formatJob(job);
                    return (
                      <tr key={job.id} className="relative transition-colors hover:bg-muted/10">
                        <td className="px-6 py-4"><RunName job={job} viewer={viewer} /></td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <StatusPill status={job.status} />
                          {job.status === "failed" && job.failure_reason && (
                            <div className="mt-1 text-[11px] font-medium text-destructive/80">{failureLabel(job.failure_reason)}</div>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-xs font-medium">{job.style_preset_id ?? "No style"}</td>
                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs">{scenesDisplay}</td>
                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs">{job.regen_count ?? "—"}</td>
                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs">{costDisplay}</td>
                        <td className="whitespace-nowrap px-6 py-4 text-xs text-foreground/60">{formattedDate}</td>
                        {showTrace && (
                          <td className="whitespace-nowrap px-6 py-4 text-right">
                            <LangfuseButton
                              url={job.langfuse_trace_url}
                              label={`Open Langfuse trace for ${job.title ?? `run ${shortId}`}`}
                            />
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <ul className="grid grid-cols-1 gap-4 md:hidden">
              {shown.map((job) => {
                const { shortId, formattedDate, scenesDisplay, costDisplay } = formatJob(job);
                return (
                  <li key={job.id} className="relative flex flex-col gap-4 rounded-2xl bg-surface p-5 neo-border neo-shadow-sm">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex min-w-0 flex-col gap-1">
                        <RunName job={job} viewer={viewer} />
                        <span className="text-xs font-medium text-foreground/50">{formattedDate}</span>
                      </div>
                      <StatusPill status={job.status} />
                    </div>
                    {job.status === "failed" && job.failure_reason && (
                      <div className="rounded-lg bg-destructive/10 p-3 text-xs font-medium text-destructive/90">
                        {failureLabel(job.failure_reason)}
                      </div>
                    )}
                    <dl className="grid grid-cols-3 gap-2 border-y border-muted/40 py-3">
                      <div><dt className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Pages</dt><dd className="font-mono text-sm">{scenesDisplay}</dd></div>
                      <div><dt className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Redraws</dt><dd className="font-mono text-sm">{job.regen_count ?? "—"}</dd></div>
                      <div><dt className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Cost</dt><dd className="font-mono text-sm">{costDisplay}</dd></div>
                    </dl>
                    <div className="flex items-center justify-between">
                      <span className="rounded-md bg-muted/40 px-2 py-1 text-xs font-medium">{job.style_preset_id ?? "No style"}</span>
                      {showTrace && (
                        <LangfuseButton url={job.langfuse_trace_url} label={`Open Langfuse trace for ${job.title ?? `run ${shortId}`}`} />
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </section>
    </main>
  );
}
