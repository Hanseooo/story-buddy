import { redirect } from "next/navigation";
import LangfuseButton from "@/components/LangfuseButton";
import { formatJob } from "@/utils/metrics";
import StatusPill from "../StatusPill";
import BackLink from "./BackLink";
import { loadRun } from "./loadRun";
import { summarizeNodes } from "./nodeSummary";
import PipelineGraph from "./PipelineGraphView";
import Characters from "./sections/Characters";
import Pages from "./sections/Pages";
import RawJson from "./sections/RawJson";
import RunDetails from "./sections/RunDetails";
import Safety from "./sections/Safety";
import Story from "./sections/Story";
import SummaryStrip from "./SummaryStrip";

const MESSAGES = {
  not_found: { title: "Run not found", body: "There is no run with this id. It may have been typed or copied wrong." },
  not_approved: {
    title: "Not approved yet",
    body: "Researchers can open a run once a teacher approves its book. Failed and unapproved runs are open to the adjudicator only.",
  },
  researchers_only: { title: "Researchers only", body: "Run pages are for researcher accounts." },
} as const;

function RunMessage({ which }: { which: keyof typeof MESSAGES }) {
  const { title, body } = MESSAGES[which];
  return (
    <main className="mx-auto flex max-w-xl flex-col items-start gap-4 p-5 sm:p-8 lg:p-12">
      <BackLink />
      <h1 className="font-display text-3xl font-extrabold">{title}</h1>
      <p className="text-base text-foreground/70">{body}</p>
    </main>
  );
}

const STILL_GOING: Record<string, string> = {
  queued: "This run is waiting to start. Reload to see new steps.",
  running: "This run is still going. The page shows what was recorded so far; reload to see more.",
  awaiting_confirm: "This run is waiting for the child to confirm the characters. The page shows what was recorded so far.",
};

export default async function RunPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  const result = await loadRun(jobId);
  if (result.kind === "signed_out") redirect(`/login?next=${encodeURIComponent(`/research/metrics/${jobId}`)}`);
  if (result.kind === "not_found") return <RunMessage which="not_found" />;
  if (result.kind === "forbidden") return <RunMessage which={result.reason} />;

  const { run } = result;
  const { job } = run;
  const { shortId, formattedDate } = formatJob(job);
  const name = job.title ?? `Run ${shortId}`;

  return (
    <main className="mx-auto max-w-7xl space-y-8 p-5 font-sans sm:p-8 lg:space-y-10 lg:p-12">
      <header className="flex flex-col gap-3">
        <BackLink />
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-extrabold tracking-tight md:text-4xl">{name}</h1>
          <StatusPill status={job.status} />
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-foreground/60">
          <span>{job.style_preset_id ?? "No style"}</span>
          <span>{formattedDate}</span>
          <span className="break-all font-mono text-xs">{job.id}</span>
          <LangfuseButton url={job.langfuse_trace_url} />
        </div>
      </header>

      {STILL_GOING[job.status] && (
        <p role="status" className="rounded-2xl bg-warning/15 p-4 text-sm font-medium">{STILL_GOING[job.status]}</p>
      )}

      <SummaryStrip run={run} />

      {run.checkpointed ? (
        <>
          <PipelineGraph steps={run.steps} endedOn={run.ended_on} summaries={summarizeNodes(run)} />
          <Story story={run.story} />
          <Characters characters={run.characters} />
          <Pages scenes={run.scenes} characters={run.characters} objects={run.state?.objects ?? []} />
          <Safety run={run} />
          <RunDetails run={run} />
          <RawJson state={run.state} />
        </>
      ) : (
        <div className="rounded-3xl bg-surface p-8 text-center neo-border neo-shadow-sm">
          <p className="font-bold">No recorded steps for this run</p>
          <p className="mt-1 text-sm text-foreground/60">
            The pipeline left no checkpoint for it, so only the totals above are known.
          </p>
        </div>
      )}
    </main>
  );
}
