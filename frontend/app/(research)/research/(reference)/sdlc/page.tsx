import ChartFigure from "../../../_shared/components/ChartFigure";
import OnThisPage from "../../../_shared/components/OnThisPage";
import ScrollTable from "../../../_shared/components/ScrollTable";
import Source from "../../../_shared/components/Source";
import { DEVIATIONS, FIGURE, LOOPS, MODEL, PHASE_05, SOURCES, type Outcome } from "./data";

export const metadata = {
  title: "Development loops (SDLC)",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const TH = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-widest text-foreground/60";
const TD = "px-3 py-2 align-top";
const PROSE = "max-w-[70ch] text-foreground/80";
const CHIP = "inline-block rounded-full px-2.5 py-0.5 text-xs font-bold whitespace-nowrap text-foreground";

// The label is the outcome in words; the colour only repeats it.
const OUTCOME: Record<Outcome, { label: string; tone: string }> = {
  met: { label: "Recorded as met", tone: "bg-success/25" },
  split: { label: "Split", tone: "bg-secondary/40" },
  "not run": { label: "Not run", tone: "bg-destructive/20" },
  partial: { label: "Partial", tone: "bg-secondary/40" },
  relaxed: { label: "Relaxed for testing", tone: "bg-secondary/40" },
  open: { label: "Open", tone: "bg-foreground/10" },
};

const TERMS = [
  { term: "SDLC", meaning: "software development life cycle: the order in which software is planned, built and checked." },
  { term: "Loop", meaning: "one turn of the spiral: pick a goal, find its biggest risk, build and check, then plan the next turn." },
  { term: "Gate", meaning: "a pass/fail check, written before the work, that a loop must meet before the next one relies on it." },
  { term: "PR", meaning: "pull request: one reviewed change merged into the main code. Each has a number, such as #12." },
  { term: "Probe 4", meaning: "a planned test of the safety filters on about 26 Filipino and Taglish stories, harmful and harmless." },
];

const SECTIONS = [
  { id: "terms", label: "Terms" },
  { id: "model", label: "The model" },
  { id: "figure", label: "Figure 3" },
  { id: "loops", label: "Table 1: the loops" },
  { id: "deviations", label: "Where the work left the plan" },
  { id: "phase05", label: "Phase 0.5 result" },
  { id: "check", label: "How to check a loop" },
];

const span = (first: string | null, last: string | null) => (first && last ? `${first} to ${last}` : "—");

export default function SdlcPage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Development loops (SDLC)</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          How StoryBuddy was built: six loops, the risk each one addressed, and whether its gate was met. This page supports
          Figure 3 and Table 1 of the paper. Every loop traces to the merged pull requests in the SDLC record.
        </p>
      </div>

      <section aria-labelledby="terms" className={`${CARD} space-y-3`}>
        <h2 id="terms" className="font-bold">Terms used on this page</h2>
        <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-[max-content_1fr]">
          {TERMS.map((t) => (
            <div key={t.term} className="contents">
              <dt className="font-bold">{t.term}</dt>
              <dd className={PROSE}>{t.meaning}</dd>
            </div>
          ))}
        </dl>
      </section>

      <OnThisPage sections={SECTIONS} />

      <section aria-labelledby="model" className="space-y-4">
        <h2 id="model" className={H2}>The model</h2>
        <p className={PROSE}>{`The development process follows ${MODEL}`}</p>
        <p className={PROSE}>
          In plain words: the work ran in loops, and each loop went after one risk with a check written in advance. The record
          below shows where that held and where it did not. Loops overlap in time, because a pull request is placed by the risk
          it addresses, not by its date.
        </p>
        <Source path={SOURCES.methodology} where="§1.1 and §1.3" />
      </section>

      <section aria-labelledby="figure" className="space-y-4">
        <h2 id="figure" className={H2}>Figure 3: the spiral</h2>
        <ChartFigure
          id={FIGURE.id}
          wide
          alt={FIGURE.alt}
          asOf={FIGURE.asOf}
          png={FIGURE.png}
          source={FIGURE.source}
          sourceNoun="the editable diagram"
          caption={<strong className="text-foreground">Figure 3: the six development loops and their gate results.</strong>}
        >
          <div
            role="region"
            aria-label={`${FIGURE.alt} It scrolls sideways on a narrow screen.`}
            tabIndex={0}
            className={`overflow-x-auto rounded-2xl border border-primary/10 bg-white ${FOCUS}`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={FIGURE.png} alt={FIGURE.alt} className="h-auto w-full min-w-[40rem] md:min-w-0" />
          </div>
        </ChartFigure>
      </section>

      <section aria-labelledby="loops" className="space-y-4">
        <h2 id="loops" className={H2}>Table 1: the loops and their gates</h2>
        <ScrollTable label="Table 1: each loop, its risk, its pull requests, its gate and the gate result">
          <thead className="bg-muted/40">
            <tr>
              <th scope="col" className={TH}>Loop</th>
              <th scope="col" className={TH}>Risk it addressed</th>
              <th scope="col" className={TH}>Pull requests</th>
              <th scope="col" className={TH}>Gate</th>
              <th scope="col" className={TH}>Gate result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-foreground/10">
            {LOOPS.map((l) => (
              <tr key={l.loop}>
                <th scope="row" className={`${TD} min-w-28 text-left`}>
                  <span className="block font-bold whitespace-nowrap">Loop {l.loop}</span>
                  <span className="block text-sm font-normal text-foreground/60">Phase {l.phase}</span>
                </th>
                <td className={`${TD} min-w-48`}>{l.risk}</td>
                <td className={`${TD} min-w-48`}>
                  {l.prs === 0 ? (
                    <span>None: committed to main before PR #1.</span>
                  ) : (
                    <>
                      <span className="block font-bold">{l.prs} merged</span>
                      <span className="block text-sm text-foreground/60">{span(l.first, l.last)}</span>
                      <span className="block text-sm break-words">{l.prList}</span>
                    </>
                  )}
                </td>
                <td className={`${TD} min-w-56`}>{l.gate}</td>
                <td className={`${TD} min-w-56 space-y-1`}>
                  <span className={`${CHIP} ${OUTCOME[l.outcome].tone}`}>{OUTCOME[l.outcome].label}</span>
                  <span className="block">{l.result}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path={SOURCES.record} where="§2, the loop table, and §5, every merged pull request" />
      </section>

      <section aria-labelledby="deviations" className="space-y-4">
        <h2 id="deviations" className={H2}>Where the work left the plan</h2>
        <ol className={`${PROSE} list-decimal space-y-2 pl-6`}>
          {DEVIATIONS.map((d) => (
            <li key={d.title}>
              <strong className="text-foreground">{d.title}</strong> {d.detail}
            </li>
          ))}
        </ol>
        <Source path={SOURCES.record} where="§3" />
      </section>

      <section aria-labelledby="phase05" className="space-y-4">
        <h2 id="phase05" className={H2}>Phase 0.5 result, as recorded</h2>
        <div className={`${CARD} space-y-2`}>
          <p className={PROSE}>{PHASE_05.recorded}</p>
          <p className={PROSE}>
            In plain words: drawing from a reference kept the character on 80% of items, which met the first gate. It beat drawing
            without a reference by 25 points, short of the 30 required, so the second gate was missed.
          </p>
        </div>
        <Source path={SOURCES.phase05} where="the status line" />
      </section>

      <section aria-labelledby="check" className="space-y-4">
        <h2 id="check" className={H2}>How to check a loop</h2>
        <p className={PROSE}>
          The SDLC record lists every merged pull request with its merge commit. Run <code className="font-mono">git show</code>{" "}
          with that commit to see the PR number, the date and the title. A test checks every row against git. Which loop a pull
          request belongs to is a judgment, and the record says how it was made.
        </p>
        <Source path={SOURCES.record} where="§1, How to check it, and §4, assignments that needed a judgment" />
      </section>
    </main>
  );
}
