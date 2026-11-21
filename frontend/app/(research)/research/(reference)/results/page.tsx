import ChartFigure from "../../../_shared/components/ChartFigure";
import ScrollTable from "../../../_shared/components/ScrollTable";
import Source from "../../../_shared/components/Source";
import {
  ACCURACY,
  ACCURACY_NOTE,
  AGREEMENT,
  BOUNDED_WORDING,
  CHARTS,
  CHARTS_AS_OF,
  CHECKPOINTS,
  CHECKPOINT_TIE,
  COMPARISON,
  CONTRADICTION,
  JUDGES,
  NO_CURVE_SOURCE,
  PARTIAL_SENTENCES,
  RECOMMENDATIONS,
  RESAMPLES,
  RESULT_DATE,
  SEEDS,
  SENSITIVITY,
  SOURCES,
  TEST,
  TIED_STEP,
  TRADEOFF,
  TRAIN,
  TRAINING,
  TRAINING_SETTINGS,
  UNREADABLE_NOTE,
  VALIDATION,
  calledDifferent,
  wrong,
} from "./data";
import OnThisPage from "../../../_shared/components/OnThisPage";

export const metadata = {
  title: "StoryBuddy Judge Results",
};

const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const TH = "px-2 py-2 text-left text-xs font-semibold uppercase tracking-widest text-foreground/60";
const TD = "px-2 py-2 tabular-nums whitespace-nowrap";
const H3 = "font-display text-xl font-extrabold tracking-tight";
const PROSE = "max-w-[70ch] text-foreground/80";
const LIST = `${PROSE} list-disc space-y-2 pl-5 marker:text-primary`;

// Chart colours. Blue against coral was checked for colour-blind separation, and both clear 3:1 on the card.
const RIGHT = "bg-primary";
const WRONG = "bg-coral";
const OTHER = "bg-foreground/60";

const [UNTRAINED, SEED_1, SEED_0, SEED_2] = JUDGES;

const percent = (part: number, whole: number) => `${((part / whole) * 100).toFixed(1)}%`;

function Swatch({ tone }: { tone: string }) {
  return <span aria-hidden className={`inline-block size-2.5 shrink-0 rounded-sm ${tone}`} />;
}

const DATA_FILE = "frontend/app/(research)/research/(reference)/results/data.ts";
const chartOf = (id: string) => CHARTS.find((chart) => chart.id === id)!;

// A chart's shared frame, from the chart's entry in data.ts.
function Chart({ id, caption, children }: { id: string; caption: React.ReactNode; children: React.ReactNode }) {
  const { alt, png } = chartOf(id);
  return (
    <ChartFigure id={id} alt={alt} asOf={CHARTS_AS_OF} png={png} source={DATA_FILE} caption={caption}>
      {children}
    </ChartFigure>
  );
}

// One judge's counts as a 2 by 2 table: the labellers' answer down the side, the judge's answer across the top.
function Matrix({ judge }: { judge: (typeof JUDGES)[number] }) {
  const cell = "px-2 py-2 text-center tabular-nums";
  return (
    <div className="space-y-2">
      <p className="font-bold">{judge.name}</p>
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">{`${judge.name}: counts of the ${TEST.pairs} test pairs`}</caption>
        <thead>
          <tr>
            <td />
            <th scope="col" className={`${TH} text-center`}>Judge said Different</th>
            <th scope="col" className={`${TH} text-center`}>Judge said Same, or was unreadable</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row" className="px-2 py-2 text-left text-xs font-bold">Really Different</th>
            <td className={`${cell} bg-primary/15`}>{`${judge.caught} caught`}</td>
            <td className={`${cell} bg-coral/15`}>{`${judge.missed} missed`}</td>
          </tr>
          <tr>
            <th scope="row" className="px-2 py-2 text-left text-xs font-bold">Really Same</th>
            <td className={`${cell} bg-coral/15`}>{`${judge.falseAlarms} false alarms`}</td>
            <td className={`${cell} bg-primary/15`}>{`${judge.correctSame} correct`}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

// The pairs a judge called Different, as one bar scaled against the judge that called the most.
function CalledBar({ judge, most }: { judge: (typeof JUDGES)[number]; most: number }) {
  return (
    <li className="space-y-1.5 text-sm">
      <div className="flex flex-col gap-x-4 gap-y-1 sm:flex-row sm:flex-wrap">
        <p className="font-bold">{`${judge.name}: ${calledDifferent(judge)} called Different`}</p>
        <p className="flex flex-wrap gap-x-4 gap-y-1">
          <span className="inline-flex items-center gap-1.5">
            <Swatch tone={RIGHT} />
            {"Catches "}
            <span className="font-bold tabular-nums">{judge.caught}</span>
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Swatch tone={WRONG} />
            {"False alarms "}
            <span className="font-bold tabular-nums">{judge.falseAlarms}</span>
          </span>
        </p>
      </div>
      <div aria-hidden className="flex h-3 gap-0.5" style={{ width: percent(calledDifferent(judge), most) }}>
        <div className={`min-w-0.5 ${RIGHT}`} style={{ flexGrow: judge.caught }} />
        <div className={`rounded-r ${WRONG}`} style={{ flexGrow: judge.falseAlarms }} />
      </div>
    </li>
  );
}

// Validation scores by checkpoint, one line per seed. The selected checkpoint is a filled dot and the tied
// alternative a ring. The values are in the runbook table named under the chart.
const SERIES = [
  { seed: 0, label: "Seed 0", stroke: "stroke-coral", fill: "fill-coral", dash: "6 3" },
  { seed: 1, label: "Seed 1", stroke: "stroke-primary", fill: "fill-primary", dash: undefined },
  { seed: 2, label: "Seed 2", stroke: "stroke-foreground/60", fill: "fill-foreground/60", dash: "2 3" },
] as const;

const SELECTED = { 0: SEED_0.checkpoint, 1: SEED_1.checkpoint, 2: SEED_2.checkpoint } as const;

function Lines({ title, pick, top }: { title: string; pick: (p: (typeof CHECKPOINTS)[0][number]) => number; top: number }) {
  const W = 320;
  const H = 150;
  const x = (step: number) => 8 + (step / 183) * (W - 16);
  const y = (value: number) => H - 8 - (value / top) * (H - 16);
  return (
    <div className="min-w-0 space-y-1">
      <p className="text-sm font-bold">{title}</p>
      <svg viewBox={`0 0 ${W} ${H}`} aria-hidden className="h-auto w-full rounded-lg bg-muted/30">
        {SERIES.map(({ seed, stroke, fill, dash }) => {
          const points = CHECKPOINTS[seed];
          const selected = SELECTED[seed];
          const tied = seed === 0 || seed === 1 ? TIED_STEP[seed] : undefined;
          return (
            <g key={seed}>
              <polyline
                points={points.map((p) => `${x(p.step)},${y(pick(p))}`).join(" ")}
                fill="none"
                strokeWidth={1.75}
                strokeDasharray={dash}
                className={stroke}
              />
              {points
                .filter((p) => p.step === selected || p.step === tied)
                .map((p) => (
                  <circle
                    key={p.step}
                    cx={x(p.step)}
                    cy={y(pick(p))}
                    r={4.5}
                    strokeWidth={2}
                    className={p.step === selected ? `${fill} ${stroke}` : `fill-surface ${stroke}`}
                  />
                ))}
            </g>
          );
        })}
      </svg>
      <p className="flex justify-between text-xs text-foreground/60">
        <span>Checkpoint 10</span>
        <span>{`Top of scale ${top}`}</span>
        <span>183</span>
      </p>
    </div>
  );
}

// One score on a 0 to 1 track. The name and the number are text, and the bar itself is hidden from a screen reader.
function ScoreBar({ label, value, primary = false }: { label: string; value: string; primary?: boolean }) {
  return (
    <li className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 text-sm sm:grid-cols-[5.5rem_1fr_3rem]">
      <span className={primary ? "font-bold" : undefined}>{label}</span>{" "}
      <span className="font-bold tabular-nums sm:order-last sm:text-right">{value}</span>
      <span aria-hidden className="col-span-2 block h-3 rounded-r bg-muted/60 sm:col-span-1">
        <span className={`block h-full rounded-r ${primary ? RIGHT : OTHER}`} style={{ width: percent(Number(value), 1) }} />
      </span>
    </li>
  );
}

type Part = { label: string; count: number; tone: string };

// One group of test pairs, split in two by the judge's answer. Each part is named and counted in text.
function SplitBar({ title, first, second }: { title: string; first: Part; second: Part }) {
  return (
    <li className="space-y-1.5 text-sm">
      <div className="flex flex-col gap-x-4 gap-y-1 sm:flex-row sm:flex-wrap">
        <p>{title}</p>
        <p className="flex flex-wrap gap-x-4 gap-y-1">
          {[first, second].map((part) => (
            <span key={part.label} className="inline-flex items-center gap-1.5">
              <Swatch tone={part.tone} />
              {`${part.label} `}
              <span className="font-bold tabular-nums">{part.count}</span>
            </span>
          ))}
        </p>
      </div>
      <div aria-hidden className="flex h-3 gap-0.5">
        <div className={`min-w-0.5 ${first.tone}`} style={{ width: percent(first.count, first.count + second.count) }} />
        <div className={`flex-1 rounded-r ${second.tone}`} />
      </div>
    </li>
  );
}

const SECTIONS = [
  { id: "howto", label: "How to read this page" },
  { id: "summary", label: "What the scores show" },
  { id: "tested", label: "What was tested" },
  { id: "training", label: "How the judge was trained" },
  { id: "scores", label: "F1, precision and recall" },
  { id: "answers", label: "What each judge did" },
  { id: "table", label: "Every value" },
  { id: "accuracy", label: "Why accuracy misleads" },
  { id: "unreadable", label: "Unreadable answers" },
  { id: "comparison", label: "Seed 1 vs untrained" },
  { id: "sensitivity", label: "Ambiguous reference dropped" },
  { id: "reading", label: "What we take from this" },
  { id: "recommend", label: "What we recommend" },
  { id: "limits", label: "What this does not show" },
];

export default function ResultsPage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Judge results</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          {`Training the judge did not make it better at catching a different character on this run. The untrained model has the higher F1: ${UNTRAINED.f1}, against ${SEED_1.f1} for the trained judge picked in advance. This is a partial result from ${RESULT_DATE}. Every number names the file it comes from.`}
        </p>
      </div>

      <OnThisPage sections={SECTIONS} />

      <section aria-labelledby="howto" className={`${CARD} space-y-4`}>
        <h2 id="howto" className={H2}>How to read this page</h2>
        <p className={PROSE}>
          The judge looks at a character&apos;s reference picture and one book page, and answers Same or Different.
          Raising a problem means answering Different. The labels below are this project&apos;s sense of each word.
        </p>
        <dl className={`${PROSE} space-y-3`}>
          <div>
            <dt className="font-bold text-foreground">Catch</dt>
            <dd>The labellers said Different, and the judge said Different.</dd>
          </div>
          <div>
            <dt className="font-bold text-foreground">Miss</dt>
            <dd>
              The labellers said Different, but the judge said Same or its answer could not be read. In the app, a
              page with the wrong-looking character reaches the child.
            </dd>
          </div>
          <div>
            <dt className="font-bold text-foreground">False alarm</dt>
            <dd>
              The labellers said Same, but the judge said Different. In the app, this is an unneeded redraw. It costs
              more and makes the book slower.
            </dd>
          </div>
          <div>
            <dt className="font-bold text-foreground">Precision</dt>
            <dd>Of the pairs the judge flagged, how many were really Different.</dd>
          </div>
          <div>
            <dt className="font-bold text-foreground">Recall</dt>
            <dd>{`Of the ${TEST.different} really Different pairs, how many the judge flagged.`}</dd>
          </div>
          <div>
            <dt className="font-bold text-foreground">F1</dt>
            <dd>One score that is high only when precision and recall are both high. It is the main number. It was chosen before the results were seen.</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="summary" className="space-y-4">
        <h2 id="summary" className={H2}>What the scores show</h2>
        <p className="max-w-[70ch] rounded-2xl bg-secondary/15 p-4 font-bold text-foreground">{TRADEOFF}</p>
        <ul className={LIST}>
          <li>
            <strong className="text-foreground">The untrained model catches more.</strong>{" "}
            {`It flagged ${UNTRAINED.caught} of the ${TEST.different} Different pairs. Its cost was ${UNTRAINED.falseAlarms} false alarms on the ${TEST.same} Same pairs.`}
          </li>
          <li>
            <strong className="text-foreground">Seed 1 almost never says Different.</strong>{" "}
            {`It said Different on ${calledDifferent(SEED_1)} of ${TEST.pairs} pairs, against ${calledDifferent(UNTRAINED)} for the untrained model. ${SEED_1.caught} of those were right. It caught ${SEED_1.caught} of the ${TEST.different} real differences and missed ${SEED_1.missed}.`}
          </li>
          <li>
            <strong className="text-foreground">Seed 0 behaves like seed 1. Seed 2 behaves like the untrained model.</strong>{" "}
            {`Seed 2 flagged ${calledDifferent(SEED_2)} pairs, ${SEED_2.falseAlarms} of them false alarms, with slightly lower scores. No trained run beat the untrained model on F1.`}
          </li>
        </ul>
        <p className={PROSE}>
          Accuracy alone would hide this, and the comparison below is partial. Both are explained further down.
        </p>
      </section>

      <section aria-labelledby="tested" className="space-y-4">
        <h2 id="tested" className={H2}>What was tested</h2>
        <p className={PROSE}>
          A pair is one reference picture of a character and one book page. A judge answers Same when the page
          shows that character, and Different when it does not.
        </p>
        <p className={PROSE}>
          {`The test set has ${TEST.pairs} pairs: ${TEST.different} Different and ${TEST.same} Same. They come from children's donated stories. No story or character in the test set is in the training data, so each judge is tested on characters it never saw.`}
        </p>
        <p className={PROSE}>
          Four judges were scored on these pairs. One is Qwen3.5-9B without our training. The other three are
          separate training runs of that model, called seed 0, seed 1 and seed 2. Seed 1 was picked in advance, on
          validation data, as the one to compare with the untrained model. No seed was picked again after the
          test results were seen.
        </p>
        <p className={PROSE}>
          F1 on the Different class is the registered primary metric. Registered means it was written down before
          the results were seen.
        </p>
        <Source
          path={SOURCES.runbook}
          where="“Exact values of the partial comparison (copied 2026-10-11)” and “What the registered freeze contains”"
        />
        <Source path={SOURCES.groupGuide} where="§8, for the three definitions" />
        <Source path={SOURCES.preregistration} where="§5, for F1 as the primary metric" />
      </section>

      <section aria-labelledby="training" className="space-y-4">
        <h2 id="training" className={H2}>How the judge was trained</h2>
        <p className={PROSE}>
          The trained judges start from the same Qwen3.5-9B model as the untrained one. The method is QLoRA: the
          model&apos;s own weights stay frozen, and a small add-on called an adapter is trained on top. Each trained
          judge is the model plus one adapter.
        </p>
        <p className={PROSE}>
          {`The adapter learned from the ${TRAIN.records} training pairs, all from synthetic stories. One pass over them is an epoch. Training ran for three epochs: ${TRAINING.updatesPerEpoch} updates in each, ${TRAINING.updatesPerSeed} in a run.`}
        </p>
        <ScrollTable label="Training settings">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30">
              <th scope="col" className={TH}>Setting</th>
              <th scope="col" className={TH}>Value</th>
              <th scope="col" className={TH}>In plain words</th>
            </tr>
          </thead>
          <tbody>
            {TRAINING_SETTINGS.map(({ key, value, means }) => (
              <tr key={key} className="border-b border-primary/10 align-top last:border-b-0">
                <th scope="row" className="px-2 py-2 text-left font-mono text-xs font-bold">{key}</th>
                <td className={TD}>{value}</td>
                <td className="min-w-56 px-2 py-2">{means}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>

        <h3 className={H3}>Why three seeds</h3>
        <p className={PROSE}>
          A seed fixes the random choices in a training run, such as the order the pairs are shown in. The same
          data and settings with another seed give a slightly different judge. The plan registered in advance says
          one run on a dataset this small is noise. So it requires three runs, with seeds 0, 1 and 2, and all three
          reported, including a bad one. Picking the best seed on the test set is forbidden.
        </p>

        <h3 className={H3}>Which saved copy was used</h3>
        <p className={PROSE}>
          {`For each seed, the checkpoint with the best F1 on the validation pairs was used: checkpoint ${SEED_0.checkpoint} for seed 0, checkpoint ${SEED_1.checkpoint} for seed 1 and checkpoint ${SEED_2.checkpoint} for seed 2. Checkpoint ${SEED_1.checkpoint} is ${SEED_1.checkpoint} of the ${TRAINING.updatesPerSeed} updates, before the first epoch ends at update ${TRAINING.updatesPerEpoch}. Seed 1 was then picked as the one to compare, also on validation data.`}
        </p>
        <Source
          path={SOURCES.runbook}
          where="“Registered training settings (copied 2026-10-11)” and “Exact values of the partial comparison (copied 2026-10-11)”"
        />
        <Source path={SOURCES.trainConfig} where="the settings file itself" />
        <Source path={SOURCES.finetuneSpec} where="§6, for how a run is started" />
        <Source path={SOURCES.preregistration} where="§9.5, for the seeds and the choice of checkpoint" />
      </section>

      <section aria-labelledby="scores" className="space-y-4">
        <h2 id="scores" className={H2}>F1, precision and recall</h2>
        <p className={PROSE}>
          The untrained model has a higher F1 than each of the three trained judges. Seed 0 has high precision and low
          recall, as seed 1 does. Seed 2 has both below the untrained model&apos;s.
        </p>
        <Chart
          id="judge-f1-precision-recall"
          caption={
            <>
            <p>
              {`F1, precision and recall of each judge on the ${TEST.pairs} test pairs. Every bar runs from 0 to 1. The interval under each judge is the 95% interval of its F1, from ${RESAMPLES} resamples clustered by character. Every value is also in the table below.`}
            </p>
            <p className="flex flex-wrap gap-x-4 gap-y-1">
              <span className="inline-flex items-center gap-1.5">
                <Swatch tone={RIGHT} />
                F1, the primary metric
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Swatch tone={OTHER} />
                Precision and recall
              </span>
            </p>
            </>
          }
        >
          <ul className="space-y-6">
            {JUDGES.map((judge) => (
              <li key={judge.name} className="space-y-2">
                <p className="font-bold">{judge.name}</p>
                <ul className="space-y-2">
                  <ScoreBar label="F1" value={judge.f1} primary />
                  <ScoreBar label="Precision" value={judge.precision} />
                  <ScoreBar label="Recall" value={judge.recall} />
                </ul>
                <p className="text-sm text-foreground/70">{`F1 95% interval: ${judge.f1Interval}`}</p>
              </li>
            ))}
          </ul>
        </Chart>
        <Source path={SOURCES.runbook} where="“Exact values of the partial comparison (copied 2026-10-11)”" />
        <Source path={SOURCES.groupGuide} where="§5.2, for the reading in plain words" />
      </section>

      <section aria-labelledby="answers" className="space-y-4">
        <h2 id="answers" className={H2}>What each judge did with the pairs</h2>
        <p className={PROSE}>
          Every judge is scored on the same pairs. The terms are defined in the box at the top of the page.
        </p>

        <Chart
          id="judge-confusion-matrices"
          caption={
            <p>
              {`The untrained model and seed 1 on the ${TEST.pairs} test pairs. Each box counts pairs. Blue boxes are right answers and coral boxes are wrong ones. Every count is also in the table below.`}
            </p>
          }
        >
          <div className="grid gap-6 sm:grid-cols-2">
            <Matrix judge={UNTRAINED} />
            <Matrix judge={SEED_1} />
          </div>
        </Chart>

        <Chart
          id="judge-catches-false-alarms"
          caption={
            <p>
              {`The pairs each judge called Different, split into catches and false alarms. Every bar is drawn against the judge that called the most (${calledDifferent(UNTRAINED)}). Seed 1 rarely says Different, so its bar is short.`}
            </p>
          }
        >
          <ul className="space-y-5">
            {JUDGES.map((judge) => (
              <CalledBar key={judge.name} judge={judge} most={calledDifferent(UNTRAINED)} />
            ))}
          </ul>
        </Chart>

        <figure className={`${CARD} max-w-3xl space-y-5`}>
          <figcaption className="space-y-2 text-sm text-foreground/80">
            <p>
              {`Each judge's answers on the ${TEST.different} Different pairs and on the ${TEST.same} Same pairs. The two bars count different numbers of pairs, and each is drawn to its own full width. Every value is also in the table below.`}
            </p>
            <p className="flex flex-wrap gap-x-4 gap-y-1">
              <span className="inline-flex items-center gap-1.5">
                <Swatch tone={RIGHT} />
                Right answer
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Swatch tone={WRONG} />
                Wrong answer
              </span>
            </p>
          </figcaption>
          <ul className="space-y-6">
            {JUDGES.map((judge) => (
              <li key={judge.name} className="space-y-2">
                <p className="font-bold">{judge.name}</p>
                <ul className="space-y-3">
                  <SplitBar
                    title={`The ${TEST.different} Different pairs`}
                    first={{ label: "Caught", count: judge.caught, tone: RIGHT }}
                    second={{ label: "Missed", count: judge.missed, tone: WRONG }}
                  />
                  <SplitBar
                    title={`The ${TEST.same} Same pairs`}
                    first={{ label: "False alarms", count: judge.falseAlarms, tone: WRONG }}
                    second={{ label: "Correct", count: judge.correctSame, tone: RIGHT }}
                  />
                </ul>
              </li>
            ))}
          </ul>
        </figure>
        <Source path={SOURCES.runbook} where="“Exact values of the partial comparison (copied 2026-10-11)”" />
      </section>

      <section aria-labelledby="table" className="space-y-4">
        <h2 id="table" className={H2}>Every value in the charts</h2>
        <ScrollTable label="Results of the four judges">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30 align-bottom">
              <th scope="col" className={TH}>Judge</th>
              <th scope="col" className={TH}>F1</th>
              <th scope="col" className={TH}>F1 95% interval</th>
              <th scope="col" className={TH}>Precision</th>
              <th scope="col" className={TH}>Recall</th>
              <th scope="col" className={TH}>{`Caught (of ${TEST.different})`}</th>
              <th scope="col" className={TH}>{`Missed (of ${TEST.different})`}</th>
              <th scope="col" className={TH}>{`False alarms (of ${TEST.same})`}</th>
              <th scope="col" className={TH}>{`Correct Same (of ${TEST.same})`}</th>
              <th scope="col" className={TH}>{`Unreadable (of ${TEST.pairs})`}</th>
            </tr>
          </thead>
          <tbody>
            {JUDGES.map((judge) => (
              <tr key={judge.name} className="border-b border-primary/10 last:border-b-0">
                <th scope="row" className="min-w-44 px-2 py-2 text-left font-bold">{judge.name}</th>
                <td className={TD}>{judge.f1}</td>
                <td className={TD}>{judge.f1Interval}</td>
                <td className={TD}>{judge.precision}</td>
                <td className={TD}>{judge.recall}</td>
                <td className={TD}>{judge.caught}</td>
                <td className={TD}>{judge.missed}</td>
                <td className={TD}>{judge.falseAlarms}</td>
                <td className={TD}>{judge.correctSame}</td>
                <td className={TD}>{judge.unreadable}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <p className={PROSE}>
          {`The three trained seeds have a mean F1 of ${SEEDS.meanF1}, with a sample standard deviation of ${SEEDS.sampleSd}.`}
        </p>
        <Source path={SOURCES.runbook} where="“Exact values of the partial comparison (copied 2026-10-11)”" />
      </section>

      <section aria-labelledby="accuracy" className="space-y-4">
        <h2 id="accuracy" className={H2}>Why accuracy alone misleads</h2>
        <p className={PROSE}>
          Accuracy is the share of all pairs a judge got right. Accuracy is not the main measure, because 85.7% of
          the test pairs are Same. A judge that answered Same every time would score 85.7% and never raise a problem.
        </p>
        <ScrollTable label="Accuracy of the judges and of always answering Same">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30 align-bottom">
              <th scope="col" className={TH}>Judge</th>
              <th scope="col" className={TH}>Accuracy</th>
              <th scope="col" className={TH}>Same pairs judged right</th>
              <th scope="col" className={TH}>False-alarm rate</th>
              <th scope="col" className={TH}>Miss rate</th>
            </tr>
          </thead>
          <tbody>
            {ACCURACY.map((row) => (
              <tr key={row.name} className="border-b border-primary/10 last:border-b-0">
                <th scope="row" className="min-w-44 px-2 py-2 text-left font-bold">{row.name}</th>
                <td className={TD}>{row.accuracy}</td>
                <td className={TD}>{row.correctSame}</td>
                <td className={TD}>{row.falseAlarmRate}</td>
                <td className={TD}>{row.missRate}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <p className={PROSE}>{ACCURACY_NOTE}</p>
        <Source path={SOURCES.runbook} where="“Results figures recounted for the research page refresh (2026-11-21)”" />
        <Source path={SOURCES.preregistration} where="“Never accuracy”, for F1 as the primary metric" />
      </section>

      <section aria-labelledby="unreadable" className="space-y-4">
        <h2 id="unreadable" className={H2}>Unreadable answers</h2>
        <p className={PROSE}>
          An unreadable answer is output that did not parse. It is scored as Same, so on a Different pair it counts
          as a miss.
        </p>
        <dl className="grid max-w-3xl grid-cols-1 gap-3 sm:grid-cols-2">
          {JUDGES.map((judge) => (
            <div key={judge.name} className="rounded-2xl bg-surface p-4 neo-border">
              <dt className="text-sm text-foreground/70">{judge.name}</dt>
              <dd className="text-xl font-extrabold">{`${judge.unreadable} of ${TEST.pairs}`}</dd>
            </div>
          ))}
        </dl>
        <p className={PROSE}>{UNREADABLE_NOTE}</p>
        <Source path={SOURCES.groupGuide} where="§5.2" />
        <Source path={SOURCES.runbook} where="“Exact values of the partial comparison (copied 2026-10-11)”, for the counts" />
      </section>

      <section aria-labelledby="comparison" className="space-y-4">
        <h2 id="comparison" className={H2}>Seed 1 against the untrained model</h2>
        <p className={PROSE}>
          This is the registered comparison: the F1 of seed 1 minus the F1 of the untrained model.
        </p>
        <dl className="grid max-w-3xl grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            { term: "Gap in F1 (ΔF1)", value: COMPARISON.deltaF1 },
            { term: "95% interval of the gap", value: COMPARISON.interval },
            { term: "Exact McNemar p", value: COMPARISON.mcnemarP },
          ].map(({ term, value }) => (
            <div key={term} className="rounded-2xl bg-surface p-4 neo-border">
              <dt className="text-sm text-foreground/70">{term}</dt>
              <dd className="text-xl font-extrabold">{value}</dd>
            </div>
          ))}
        </dl>
        <ul className={LIST}>
          <li>{`Seed 1's F1 is 0.16 lower than the untrained model's.`}</li>
          <li>
            The 95% interval of that gap is almost all below zero, so there is no sign that training helped. It also
            does not prove that training made things worse, because the interval just reaches zero.
          </li>
          <li>
            {`McNemar's test (p = ${COMPARISON.mcnemarP}) asks which judge was right on more pairs. Seed 1 was wrong on fewer pairs (${wrong(SEED_1)} vs ${wrong(UNTRAINED)}), mostly by answering Same on a test set where most pairs are Same. It does not mean seed 1 finds problems better.`}
          </li>
        </ul>
        <Source
          path={SOURCES.runbook}
          where="“Exact values of the partial comparison (copied 2026-10-11)” and “Partial untuned versus fine-tuned comparison (2026-10-08)”"
        />
        <Source path={SOURCES.groupGuide} where="§5.2" />
        <Source path={SOURCES.preregistration} where="§1.2, for the comparison" />
      </section>

      <section aria-labelledby="sensitivity" className="space-y-4">
        <h2 id="sensitivity" className={H2}>With the ambiguous reference dropped</h2>
        <p className={PROSE}>
          {`This check was registered in advance. It drops one test character whose reference picture was ambiguous (${SENSITIVITY.droppedPairs} pairs). That leaves ${SENSITIVITY.pairs} pairs, ${SENSITIVITY.different} of them Different.`}
        </p>
        <ScrollTable label="Scores with the ambiguous reference dropped">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30">
              <th scope="col" className={TH}>Judge</th>
              <th scope="col" className={TH}>F1</th>
              <th scope="col" className={TH}>Precision</th>
              <th scope="col" className={TH}>Recall</th>
            </tr>
          </thead>
          <tbody>
            {JUDGES.map((judge) => (
              <tr key={judge.name} className="border-b border-primary/10 last:border-b-0">
                <th scope="row" className="px-2 py-2 text-left font-bold">{judge.name}</th>
                <td className={TD}>{judge.sensitivity.f1}</td>
                <td className={TD}>{judge.sensitivity.precision}</td>
                <td className={TD}>{judge.sensitivity.recall}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <p className={PROSE}>
          {`Seed 1 minus the untrained model: ΔF1 ${SENSITIVITY.deltaF1}, 95% interval ${SENSITIVITY.interval}, exact McNemar p = ${SENSITIVITY.mcnemarP}. The direction matches the primary analysis. The primary analysis, on every pair, stands. This check never replaces it.`}
        </p>
        <Source path={SOURCES.runbook} where="“Registered agreement and sensitivity analyses (2026-10-09)”" />
        <Source path={SOURCES.groupGuide} where="§5.2" />
      </section>

      <section aria-labelledby="reading" className="space-y-4">
        <h2 id="reading" className={H2}>What we take from this</h2>
        <p className={PROSE}>
          These are readings of the numbers above and of the plan registered in advance. Each rests on a document
          named under the list.
        </p>
        <ul className={LIST}>
          <li>
            <strong className="text-foreground">The objective is to evaluate the trained judge, not to show it wins.</strong>{" "}
            Its registered result is the trained judge&apos;s precision, recall and F1 against human labels, and the plan
            says that result does not depend on any comparison. A low F1 is still that result. It is partial
            because the prompted Gemma baseline is missing.
          </li>
          <li>
            <strong className="text-foreground">The trained judge is not used in the product.</strong> The plan ships a
            trained judge only if it beats the untrained model. StoryBuddy keeps its prompted Gemma judge. No formal
            decision under that rule was recorded.
          </li>
          <li>
            <strong className="text-foreground">The main work moved to the page-drawing pipeline.</strong> Paid
            evaluation stopped on 2026-10-07 for budget, and the owner made the pipeline the next workstream that
            day. This result came on 2026-10-08, so it did not cause the move.
          </li>
          <li>
            <strong className="text-foreground">Training changed the judge&apos;s answers. It did not improve them.</strong>{" "}
            {`Seed 1 called ${calledDifferent(SEED_1)} pairs Different where the untrained model called ${calledDifferent(UNTRAINED)}, and its unreadable answers went from ${UNTRAINED.unreadable} to ${SEED_1.unreadable}. The plan describes a trained judge that does not beat its base as “The LoRA did nothing”. Here the adapter did change the output.`}
          </li>
        </ul>

        <h3 className={H3}>A measured lead: the checkpoint tie</h3>
        <p className={PROSE}>
          Each seed&apos;s checkpoint was the one with the best F1 on the validation pairs. A checkpoint is a saved
          copy of the adapter. When two tie, the earlier one wins. That rule was fixed in advance. Seeds 0 and 1 had a
          tie, and the earlier step won both times.
        </p>
        <ScrollTable label="Checkpoint tie on the validation pairs">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30 align-bottom">
              <th scope="col" className={TH}>Seed</th>
              <th scope="col" className={TH}>Best validation F1</th>
              <th scope="col" className={TH}>Selected</th>
              <th scope="col" className={TH}>Tied alternative</th>
              <th scope="col" className={TH}>Unreadable of 86 (selected, alternative)</th>
            </tr>
          </thead>
          <tbody>
            {CHECKPOINT_TIE.map((row) => (
              <tr key={row.seed} className="border-b border-primary/10 last:border-b-0">
                <th scope="row" className="px-2 py-2 text-left font-bold">{`Seed ${row.seed}`}</th>
                <td className={TD}>{row.f1}</td>
                <td className={TD}>{row.selected}</td>
                <td className={TD}>{row.alternative}</td>
                <td className={TD}>{row.unreadable}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <p className={PROSE}>
          {`The unreadable answers follow on the test set: seeds 1 and 0 gave ${SEED_1.unreadable} and ${SEED_0.unreadable} of ${TEST.pairs}, and seed 2 gave ${SEED_2.unreadable}. Later in training, seed 0 from checkpoint 120 and seed 1 from checkpoint 130 caught none of the ${VALIDATION.different} Different validation pairs. So training longer would not have fixed those two seeds on this evidence. This is a lead, not a tested cause: no run compared the alternatives on the test set. The validation set has only ${VALIDATION.different} Different pairs, so every validation figure rests on ${VALIDATION.different} pairs.`}
        </p>
        <Chart
          id="judge-validation-checkpoints"
          caption={
            <p>
              {`Each line is one seed on the ${VALIDATION.pairs} validation pairs, by checkpoint. A filled dot is the checkpoint used. A ring is the checkpoint it tied with. Seeds 0 and 1 were tied with a later checkpoint that had no unreadable answers. Seed 2 had no tie.`}
            </p>
          }
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <Lines title="F1 on the Different class" pick={(p) => Number(p.f1)} top={0.5} />
            <Lines title="Unreadable answers" pick={(p) => p.unreadable} top={40} />
          </div>
          <ul className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
            {SERIES.map(({ seed, label, stroke, dash }) => (
              <li key={seed} className="inline-flex items-center gap-2">
                <svg aria-hidden viewBox="0 0 24 6" className="h-1.5 w-6">
                  <line x1="0" y1="3" x2="24" y2="3" strokeWidth={2} strokeDasharray={dash} className={stroke} />
                </svg>
                {label}
              </li>
            ))}
          </ul>
        </Chart>

        <h3 className={H3}>Why it happened is not known</h3>
        <p className={PROSE}>No cause was tested. These three explanations fit the numbers, and none has been checked.</p>
        <ul aria-label="Explanations that were not tested" className={LIST}>
          <li>
            <strong className="text-foreground">One sentence for every constructed pair.</strong>{" "}
            {`${TRAIN.constructed} of the ${TRAIN.different} Different training pairs are constructed, and all of them carry the same reason and the same sentence, written by a script. The model may have learned the sentence instead of the difference.`}
          </li>
          <li>
            <strong className="text-foreground">Different kinds of stories.</strong>{" "}
            {`Training used synthetic stories: ${TRAINING.nonHumanPairs} of ${TRAIN.records} training pairs (${((TRAINING.nonHumanPairs / TRAIN.records) * 100).toFixed(1)}%) are non-human, including constructed pairs. The test stories are children's, mostly about humans.`}
          </li>
          <li>
            <strong className="text-foreground">Answers cut off.</strong>{" "}
            {`A judge's answer is capped at ${TRAINING.generationCap} tokens, and the judge writes its reasons before its verdict. Whether the unreadable answers were cut off was not checked.`}
          </li>
        </ul>
        <p className={PROSE}>
          The plan says what may come next. Debugging uses training and validation data only. One more read of the
          test set is allowed, and only after a defect is found and fixed. Trying new settings does not count as a
          defect. No second read has been made.
        </p>
        <Source path={SOURCES.preregistration} where="§1.1 for the objective, §6 for the rule on shipping, §7 for what may come next" />
        <Source
          path={SOURCES.changelog}
          where="§1 items 3, 4 and 9, §2 for the move to the pipeline, and the 2026-10-11 rows for the four explanations"
        />
        <Source
          path={SOURCES.runbook}
          where="“Registered training settings (copied 2026-10-11)”, “What the registered freeze contains” and “Held-out resume context”"
        />
        <Source path={SOURCES.groupGuide} where="§5.3, for the kinds of stories" />
        <Source path={SOURCES.runbook} where="“Checkpoint tie” and “Validation scores by checkpoint”, for the lead and its chart" />
      </section>

      <section aria-labelledby="recommend" className="space-y-4">
        <h2 id="recommend" className={H2}>What we recommend</h2>
        <p className={PROSE}>
          Items 2 to 4 are drawn from measured facts. Whether they would fix the result is untested.
        </p>
        <ol className={`${PROSE} list-decimal space-y-3 pl-5 marker:font-bold marker:text-primary`}>
          {RECOMMENDATIONS.map((rec, index) => (
            <li key={rec.lead}>
              <strong className="text-foreground">{rec.lead}</strong>
              {rec.body && ` ${rec.body}`}
              {index === 4 && ` “${BOUNDED_WORDING}”`}
              {rec.untested && (
                <>
                  {" "}
                  <span className="inline-block rounded-full bg-secondary/30 px-2.5 py-0.5 text-xs font-bold whitespace-nowrap text-foreground">
                    Untested as a fix
                  </span>
                </>
              )}
            </li>
          ))}
        </ol>
        <Source path={SOURCES.groupGuide} where="§5.2, “What we recommend”" />
        <Source path={SOURCES.changelog} where="§1 item 4, for the bounded wording" />
      </section>

      <section aria-labelledby="limits" className="space-y-4">
        <h2 id="limits" className={H2}>What this does and does not show</h2>
        <ul className={LIST}>
          <li>
            {`The comparison is partial. ${PARTIAL_SENTENCES[0]} The full registered report is incomplete. ${PARTIAL_SENTENCES[1]}`}
          </li>
          <li>{NO_CURVE_SOURCE}</li>
          <li>
            It does not say fine-tuning can never work. It says this training run did not improve the judge under
            these data and settings.
          </li>
          <li>
            Training was completed on all three seeds. That training can be run and that it improves the judge are
            separate findings.
          </li>
          <li>
            {`The checkpoint and the seed were chosen on the validation split, which has ${VALIDATION.different} Different pairs out of ${VALIDATION.pairs}. The validation F1 behind that choice is ${SEED_0.validationF1} for seed 0, ${SEED_1.validationF1} for seed 1 and ${SEED_2.validationF1} for seed 2. Each of the three rests on four pairs.`}
          </li>
          <li>The trained judges learned from synthetic stories only. The test set is children&apos;s stories only.</li>
          <li>
            {`A constructed pair sets one character's reference against another character's page. It is Different by construction and no rater saw it. ${CONTRADICTION.pairs} of the ${TRAIN.constructed} constructed training pairs contradict a rated pair: the raters had labelled the same two image pairs Same. That is ${CONTRADICTION.records} of the ${TRAIN.records} training records. No validation or test pair is affected.`}
          </li>
          <li>
            {`Two raters labelled the test pairs. On the ${TEST.pairs} pairs they gave the same answer ${AGREEMENT.agreement} of the time. Cohen's κ, which corrects for chance agreement, is ${AGREEMENT.kappa}. Both raters were briefed by the owner, who also settled their disagreements, so κ cannot catch a misunderstanding they shared.`}
          </li>
        </ul>
        <Source
          path={SOURCES.runbook}
          where="“Partial untuned versus fine-tuned comparison (2026-10-08)”, “Exact values of the partial comparison (copied 2026-10-11)”, “What the registered freeze contains” and “Registered agreement and sensitivity analyses (2026-10-09)”"
        />
        <Source path={SOURCES.groupGuide} where="§4 and §5.2" />
      </section>
    </main>
  );
}
