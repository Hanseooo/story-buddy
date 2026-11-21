import { ArrowSquareOut, FileText, Pencil } from "@phosphor-icons/react/dist/ssr";
import { DOC_CHAPTERS, githubUrl } from "./entries";
import { CHANGELOG_POINTS, PAPER_CORRECTIONS, PAPER_TYPOS, type Correction } from "./paper";

export const metadata = {
  title: "StoryBuddy Research Documents",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const LINK = `inline-flex min-h-11 max-w-full items-center gap-1.5 rounded-lg text-primary hover:text-primary-deep hover:underline ${FOCUS}`;

const LINK_TIGHT = LINK.replace("min-h-11", "min-h-9");

const STATUS_LABEL: Record<Correction["status"], string> = {
  open: "Open",
  unconfirmed: "Unconfirmed, owner to confirm",
  settled: "Settled",
  "repo-right": "Repo is right",
};

const fileName = (repoPath: string) => repoPath.split("/").pop()!;

function CorrectionRow({ item }: { item: Correction }) {
  const sources = [...new Set(item.pins.map((pin) => pin.file))];
  return (
    <li
      data-testid={`correction-${item.id}`}
      className="rounded-2xl bg-background p-4 neo-border"
    >
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-mono text-xs font-bold text-foreground/60">{item.id}</span>
        <h4 className="font-sans text-base font-bold">{item.topic}</h4>
        <span
          className={`rounded-full px-2 py-0.5 font-sans text-xs font-bold text-foreground ${
            item.status === "open" || item.status === "unconfirmed" ? "bg-secondary/40" : "bg-primary/15"
          }`}
        >
          {STATUS_LABEL[item.status]}
        </span>
        {item.decision && <span className="font-mono text-xs text-foreground/60">{item.decision}</span>}
      </div>
      <p className="mt-1 max-w-[70ch] text-sm text-foreground/70">
        <span className="font-bold">Paper says:</span> {item.paper}
      </p>
      <p className="max-w-[70ch] text-sm text-foreground">
        <span className="font-bold">Use:</span> {item.value}
      </p>
      <p className="flex flex-wrap items-center gap-x-3 gap-y-0 text-sm">
        <span className="text-foreground/60">Source:</span>
        {sources.map((file) => (
          <a key={file} href={githubUrl(file)} target="_blank" rel="noopener noreferrer" className={`${LINK_TIGHT} font-mono font-bold`}>
            <span className="min-w-0 [overflow-wrap:anywhere]">{fileName(file)}</span>
            <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
            <span className="sr-only"> (source, opens in a new tab)</span>
          </a>
        ))}
        {item.open && (
          <a href={item.open.url} target="_blank" rel="noopener noreferrer" className={`${LINK_TIGHT} font-bold`}>
            <span>
              {item.open.id}, issue {item.open.url.split("/").pop()}
            </span>
            <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        )}
      </p>
    </li>
  );
}

function PaperPanel() {
  const open = PAPER_CORRECTIONS.filter((c) => c.status === "open");
  const unconfirmed = PAPER_CORRECTIONS.filter((c) => c.status === "unconfirmed");
  const closed = PAPER_CORRECTIONS.filter((c) => c.status === "settled" || c.status === "repo-right");
  return (
    <section
      aria-labelledby="paper-panel"
      className="space-y-6 rounded-3xl bg-secondary/10 p-5 neo-border sm:p-6"
    >
      <div className="flex flex-col gap-1">
        <h2 id="paper-panel" className="font-display text-2xl font-extrabold tracking-tight">
          What the paper must say
        </h2>
        <p className="max-w-[65ch] text-sm text-foreground/70">
          Where the paper and the repo disagree, with the value to print. Each value is checked against the source
          doc named under it. Fixing the paper is for the groupmates.
        </p>
      </div>

      <div className="space-y-3">
        <h3 className="font-sans text-lg font-bold">Open, not yet settled ({open.length})</h3>
        <ul className="space-y-3">
          {open.map((item) => (
            <CorrectionRow key={item.id} item={item} />
          ))}
        </ul>
      </div>

      <div className="space-y-3">
        <h3 className="font-sans text-lg font-bold">Unconfirmed, owner to confirm ({unconfirmed.length})</h3>
        <ul className="space-y-3">
          {unconfirmed.map((item) => (
            <CorrectionRow key={item.id} item={item} />
          ))}
        </ul>
      </div>

      <div className="space-y-3">
        <h3 className="font-sans text-lg font-bold">Settled, or the repo is right ({closed.length})</h3>
        <ul className="space-y-3">
          {closed.map((item) => (
            <CorrectionRow key={item.id} item={item} />
          ))}
        </ul>
      </div>

      <div className="space-y-2">
        <h3 className="font-sans text-lg font-bold">From the research changelog, section 1</h3>
        <ol className="ml-5 list-decimal space-y-1 text-sm text-foreground/80">
          {CHANGELOG_POINTS.map((point) => (
            <li key={point} className="max-w-[70ch] pl-1 [overflow-wrap:anywhere]">
              {point}
            </li>
          ))}
        </ol>
        <a
          href={githubUrl("docs/capstone/research-changelog.md")}
          target="_blank"
          rel="noopener noreferrer"
          className={`${LINK} text-sm font-bold`}
        >
          Read each point in full in research-changelog.md
          <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
      </div>

      <div className="space-y-2">
        <h3 className="flex items-center gap-2 font-sans text-lg font-bold">
          <Pencil weight="bold" className="size-5 shrink-0 text-primary" aria-hidden />
          Typos to fix in the paper
        </h3>
        <ul className="space-y-1 text-sm">
          {PAPER_TYPOS.map((typo) => (
            <li key={typo.wrong} className="max-w-[70ch] [overflow-wrap:anywhere]">
              <span className="font-bold">&ldquo;{typo.wrong}&rdquo;</span> should be{" "}
              <span className="font-bold">&ldquo;{typo.right}&rdquo;</span>. <span className="text-foreground/70">{typo.where}.</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export default function DocsPage() {
  return (
    <main className="space-y-8 pt-4 lg:space-y-10">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Research documents</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          The files behind the study, grouped by paper chapter. Each one opens on GitHub in a new tab, always at its
          latest version, and shows when it last changed.
        </p>
      </div>

      <PaperPanel />

      <ul className="space-y-6">
        {DOC_CHAPTERS.map((chapter) => (
          <li key={chapter.id} className="rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6">
            <h2 className="flex flex-col gap-1">
              <span className="font-display text-xl font-extrabold tracking-tight">{chapter.title}</span>
            </h2>
            <p className="text-sm text-foreground/60">{chapter.blurb}</p>

            <ul className="mt-3 ml-2.5 space-y-1 border-l-2 border-primary/15 pl-4 sm:pl-6">
              {chapter.entries.map((entry) => (
                <li key={entry.path} className="py-1">
                  <a
                    href={githubUrl(entry.path)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`${LINK} font-mono text-sm font-bold`}
                  >
                    <FileText weight="bold" className="size-4 shrink-0" aria-hidden />
                    <span className="min-w-0 [overflow-wrap:anywhere]">{fileName(entry.path)}</span>
                    {entry.startHere && (
                      <span className="shrink-0 rounded-full bg-secondary/30 px-2 py-0.5 font-sans text-xs font-bold text-foreground">
                        Start here
                      </span>
                    )}
                    <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
                    <span className="sr-only"> (opens on GitHub in a new tab)</span>
                  </a>
                  <p className="font-mono text-xs text-foreground/60 [overflow-wrap:anywhere]">
                    {entry.path.slice(0, entry.path.lastIndexOf("/") + 1)} · changed{" "}
                    <time dateTime={entry.lastChanged}>{entry.lastChanged}</time>
                  </p>
                  <p className="max-w-[70ch] text-sm text-foreground/70">{entry.answers}</p>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </main>
  );
}
