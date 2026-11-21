import PipelineMap from "@/components/PipelineMap";
import ChartFigure from "../../../_shared/components/ChartFigure";
import ScrollTable from "../../../_shared/components/ScrollTable";
import Source from "../../../_shared/components/Source";
import { githubUrl } from "../docs/entries";
import { CAPS, CORPUS_WORD_LIMIT, FIGURES, MODULES, NODE_COUNTS, SOURCES } from "./data";

export const metadata = {
  title: "Conceptual framework and pipeline",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const TH = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-widest text-foreground/60";
const TD = "px-3 py-2";
const PROSE = "max-w-[70ch] text-foreground/80";
const CUE = "text-sm text-foreground/60";
const LINK = `inline-flex min-h-11 items-center rounded-lg font-mono text-sm font-bold text-primary hover:text-primary-deep hover:underline sm:min-h-0 ${FOCUS}`;

const SECTIONS = [
  { id: "ipo", label: "IPO model" },
  { id: "diagram", label: "Pipeline diagram" },
  { id: "nodes", label: "The 14 nodes" },
  { id: "modules", label: "Paper modules" },
  { id: "caps", label: "Limits" },
  { id: "failures", label: "When a check fails" },
  { id: "reveal", label: "At the reveal" },
];

const DEFINITIONS: [string, string][] = [
  ["Node", "One step of the pipeline. The pipeline is a graph: nodes joined by arrows."],
  ["Baseline mode", `The original run. ${NODE_COUNTS.baseline} nodes. The study corpus was made in this mode.`],
  ["Teacher-review mode", `${NODE_COUNTS.teacherReview} nodes: the baseline ones plus three that let a teacher decide on a flagged story or picture. It has been the default since 2026-11-21.`],
  ["Check", "A safety check or the consistency check. A check fails when it flags a story, a reference or a page."],
  ["Reference", "The one picture of a character that every later page is drawn from."],
  ["Page drawing", "The picture on one page of the book."],
];

function Diagram({ figure, caption, alt }: { figure: (typeof FIGURES)[keyof typeof FIGURES]; caption: React.ReactNode; alt: string }) {
  return (
    <ChartFigure
      id={figure.id}
      alt={alt}
      asOf={figure.asOf}
      png={figure.png}
      source={figure.source}
      sourceNoun="the editable diagram"
      caption={caption}
    >
      <div
        role="region"
        aria-label={`${alt} It scrolls sideways on a narrow screen.`}
        tabIndex={0}
        className={`overflow-x-auto rounded-2xl border border-primary/10 bg-white ${FOCUS}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={figure.png} alt={alt} className="h-auto w-full min-w-[40rem] md:min-w-0" />
      </div>
    </ChartFigure>
  );
}

export default function PipelinePage() {
  const words = CAPS.find((c) => c.key === "words")!;
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Conceptual framework and pipeline</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          How a child&apos;s story becomes a picture book, and what the pipeline does when a check fails. This page supports
          Figures 1 and 2 and Appendices A and B of the paper. Every fact names the file it comes from.
        </p>
      </div>

      <section aria-labelledby="terms" className={`${CARD} space-y-3`}>
        <h2 id="terms" className="font-bold">Terms used on this page</h2>
        <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-[max-content_1fr]">
          {DEFINITIONS.map(([term, meaning]) => (
            <div key={term} className="contents">
              <dt className="font-bold">{term}</dt>
              <dd className="max-w-[70ch] text-foreground/80">{meaning}</dd>
            </div>
          ))}
        </dl>
      </section>

      <nav aria-label="On this page">
        <ul className="flex flex-wrap gap-2">
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a
                href={`#${section.id}`}
                className={`inline-flex min-h-11 items-center rounded-xl border border-primary/20 bg-surface px-3 text-sm font-bold text-primary hover:bg-primary/5 ${FOCUS}`}
              >
                {section.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      <section aria-labelledby="ipo" className="space-y-4">
        <h2 id="ipo" className={H2}>The IPO model</h2>
        <p className={PROSE}>
          IPO means input, process, output. The input is the child&apos;s story. The process is the pipeline below. The output
          is the finished picture book.
        </p>
        <Diagram
          figure={FIGURES.ipo}
          alt={FIGURES.ipo.alt}
          caption={<strong className="text-foreground">Figure 1: the IPO model.</strong>}
        />
      </section>

      <section aria-labelledby="diagram" className="space-y-4">
        <h2 id="diagram" className={H2}>The pipeline diagram</h2>
        <p className={PROSE}>
          The current LangGraph pipeline, with the three teacher-review nodes. LangGraph is the library that runs the nodes in
          order.
        </p>
        <Diagram
          figure={FIGURES.pipeline}
          alt={FIGURES.pipeline.alt}
          caption={<strong className="text-foreground">Figure 2: the current pipeline.</strong>}
        />
        <Source path={SOURCES.graph} where="every node is one add_node call" />
      </section>

      <section aria-labelledby="nodes" className="space-y-4">
        <h2 id="nodes" className={H2}>The {NODE_COUNTS.total} nodes</h2>
        <p className={PROSE}>
          Each node has one plain line below. A tag shows whether it runs in both modes or only in teacher-review mode.
        </p>
        <PipelineMap />
        <Source path={SOURCES.graph} where="the node names are checked against this file by a test" />
      </section>

      <section aria-labelledby="modules" className="space-y-4">
        <h2 id="modules" className={H2}>The paper&apos;s modules and the graph nodes</h2>
        <p className={PROSE}>
          The paper names ten modules. Seven are graph nodes. Three are not: Story Memory Manager, Style Preset and Prompt
          Optimizer. The paper&apos;s &ldquo;prompt optimizer&rdquo; is not a graph node. The paper also says &ldquo;11 modules&rdquo;, which is the
          baseline node count, not the module count.
        </p>
        <p className={CUE}>This table scrolls sideways on a narrow screen.</p>
        <ScrollTable label="The paper's modules and the graph nodes that run them">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Paper module</th>
              <th scope="col" className={TH}>Graph node or nodes</th>
            </tr>
          </thead>
          <tbody>
            {MODULES.map((row) => (
              <tr key={row.module} className="border-b border-primary/5 last:border-0 align-top">
                <th scope="row" className={`${TD} w-[34%] text-left font-bold`}>{row.module}</th>
                <td className={`${TD} text-foreground/80`}>
                  {row.nodes.length > 0 ? <span className="font-mono">{row.nodes.join(", ")}</span> : row.plain}
                </td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path={SOURCES.architecture} where="the module-to-node table, and the paper's module names in docs/capstone/methodology.md" />
      </section>

      <section aria-labelledby="caps" className="space-y-4">
        <h2 id="caps" className={H2}>Limits the pipeline enforces</h2>
        <p className={PROSE}>
          Each limit is read from the code. The link opens the file, and a test checks the line.
        </p>
        <p className={CUE}>This table scrolls sideways on a narrow screen.</p>
        <ScrollTable label="Limits the pipeline enforces">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Limit</th>
              <th scope="col" className={`${TH} text-right`}>Value</th>
              <th scope="col" className={TH}>Source line</th>
            </tr>
          </thead>
          <tbody>
            {CAPS.map((cap) => (
              <tr key={cap.key} className="border-b border-primary/5 last:border-0 align-top">
                <th scope="row" className={`${TD} text-left font-bold`}>{cap.label}</th>
                <td className={`${TD} text-right font-bold tabular-nums`}>
                  {cap.value}
                  {cap.key === "words" && (
                    <span className="block text-xs font-normal text-foreground/60">{`${CORPUS_WORD_LIMIT} when the corpus was made`}</span>
                  )}
                </td>
                <td className={TD}>
                  <a href={githubUrl(`${cap.file}#L${cap.line}`)} target="_blank" rel="noopener noreferrer" className={LINK}>
                    <span className="break-all">{`${cap.file}:${cap.line}`}</span>
                    <span className="sr-only"> (opens on GitHub in a new tab)</span>
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <p className={CUE}>
          {`The ${CORPUS_WORD_LIMIT}-word limit for the corpus comes from ${SOURCES.adr068.split("/").pop()}. The ${words.value}-word limit applies to stories submitted after 2026-10-11.`}
        </p>
      </section>

      <section aria-labelledby="failures" className="space-y-4">
        <h2 id="failures" className={H2}>When a check fails</h2>
        <div className="grid gap-4 md:grid-cols-2">
          <div className={`${CARD} space-y-2`}>
            <h3 className="font-bold">Baseline mode</h3>
            <p className={PROSE}>The job stops. No partial book is made, and no placeholder page is shown.</p>
            <Source path={SOURCES.adr025} where="“never a placeholder or partial book”" />
          </div>
          <div className={`${CARD} space-y-2`}>
            <h3 className="font-bold">Teacher-review mode</h3>
            <p className={PROSE}>
              The job is held for the teacher. The teacher can allow it, ask for one new picture, or stop it (ADR-080).
            </p>
            <Source path={SOURCES.adr080} where="the teacher hold" />
          </div>
        </div>
      </section>

      <section aria-labelledby="reveal" className="space-y-4">
        <h2 id="reveal" className={H2}>At the reveal</h2>
        <p className={PROSE}>
          The reveal is where the child sees each character&apos;s reference before the pages are drawn (ADR-082). Two things
          happen there, in teacher-review jobs only.
        </p>
        <ul className="max-w-[70ch] list-disc space-y-2 pl-5 text-foreground/80 marker:text-primary">
          <li>
            <strong className="text-foreground">Other versions.</strong> Unchosen reference draws are kept. The child can
            pick any of them. Each is safety-checked before it is shown.
          </li>
          <li>
            <strong className="text-foreground">Magic pencil.</strong> The child writes a change of about 200 characters.
            The picture is edited once, and the child keeps the result or goes back.
          </li>
        </ul>
        <Source path={SOURCES.adr082} where="decisions 1, 2 and 6" />
      </section>
    </main>
  );
}
