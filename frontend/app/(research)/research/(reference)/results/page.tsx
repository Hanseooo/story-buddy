import { ArrowSquareOut } from "@phosphor-icons/react/dist/ssr";
import { githubUrl } from "../docs/entries";
import {
  AGREEMENT,
  COMPARISON,
  CONTRADICTION,
  JUDGES,
  RESAMPLES,
  RESULT_DATE,
  SEEDS,
  SENSITIVITY,
  SOURCES,
  TEST,
  TRAIN,
  TRAINING,
  TRAINING_SETTINGS,
  UNREADABLE_SHARE,
  VALIDATION,
  calledDifferent,
  wrong,
  type SourceKey,
} from "./data";

export const metadata = {
  title: "StoryBuddy Judge Results",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
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

// Source and ScrollTable are copied from ../dataset/page.tsx. This is their second use: extract on a third.
function Source({ file, where }: { file: SourceKey; where: string }) {
  return (
    <p className="text-sm text-foreground/60">
      Source:{" "}
      <a
        href={githubUrl(SOURCES[file])}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex min-h-11 items-center gap-1 rounded-lg font-mono font-bold text-primary hover:text-primary-deep hover:underline sm:min-h-0 ${FOCUS}`}
      >
        <span className="break-all">{SOURCES[file]}</span>
        <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
        <span className="sr-only"> (opens on GitHub in a new tab)</span>
      </a>
      , {where}
    </p>
  );
}

// tabIndex: a table wider than the screen scrolls sideways, and a keyboard user needs to reach it.
function ScrollTable({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div role="region" aria-label={label} tabIndex={0} className={`overflow-x-auto rounded-2xl neo-border ${FOCUS}`}>
      <table className="w-full min-w-[36rem] border-collapse text-sm">
        <caption className="sr-only">{label}</caption>
        {children}
      </table>
    </div>
  );
}

function Swatch({ tone }: { tone: string }) {
  return <span aria-hidden className={`inline-block size-2.5 shrink-0 rounded-sm ${tone}`} />;
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

export default function ResultsPage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Judge results</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          {`Training the judge did not make it better at catching a different character on this run. The untrained model has the higher F1: ${UNTRAINED.f1}, against ${SEED_1.f1} for the trained judge picked in advance. This is a partial result from ${RESULT_DATE}. Every number names the file it comes from.`}
        </p>
      </div>

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
        <dl className={`${PROSE} space-y-2`}>
          <div>
            <dt className="inline font-bold text-foreground">Precision. </dt>
            <dd className="inline">Of the pairs the judge called Different, how many really were.</dd>
          </div>
          <div>
            <dt className="inline font-bold text-foreground">Recall. </dt>
            <dd className="inline">Of the pairs that really were Different, how many the judge caught.</dd>
          </div>
          <div>
            <dt className="inline font-bold text-foreground">F1. </dt>
            <dd className="inline">One number that balances precision and recall. 1.0 is perfect.</dd>
          </div>
        </dl>
        <p className={PROSE}>
          F1 on the Different class is the registered primary metric. Registered means it was written down before
          the results were seen.
        </p>
        <Source
          file="runbook"
          where="“Exact values of the partial comparison (copied 2026-10-11)” and “What the registered freeze contains”"
        />
        <Source file="groupGuide" where="§8, for the three definitions" />
        <Source file="preregistration" where="§5, for F1 as the primary metric" />
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
          file="runbook"
          where="“Registered training settings (copied 2026-10-11)” and “Exact values of the partial comparison (copied 2026-10-11)”"
        />
        <Source file="trainConfig" where="the settings file itself" />
        <Source file="finetuneSpec" where="§6, for how a run is started" />
        <Source file="preregistration" where="§9.5, for the seeds and the choice of checkpoint" />
      </section>

      <section aria-labelledby="scores" className="space-y-4">
        <h2 id="scores" className={H2}>F1, precision and recall</h2>
        <ul className={LIST}>
          <li>The untrained model has a higher F1 than each of the three trained judges.</li>
          <li>
            Seed 1 is more careful. When it says Different it is usually right, which is high precision. It misses
            most of the real differences, which is low recall.
          </li>
          <li>
            Seed 0 shows the same pattern. Seed 2 does not: its precision and its recall are both below the
            untrained model&apos;s.
          </li>
        </ul>

        <figure className={`${CARD} max-w-3xl space-y-5`}>
          <figcaption className="space-y-2 text-sm text-foreground/80">
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
          </figcaption>
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
        </figure>
        <Source file="runbook" where="“Exact values of the partial comparison (copied 2026-10-11)”" />
        <Source file="groupGuide" where="§5.2, for the reading in plain words" />
      </section>

      <section aria-labelledby="answers" className="space-y-4">
        <h2 id="answers" className={H2}>What each judge did with the pairs</h2>
        <p className={PROSE}>
          A caught pair is a Different pair the judge called Different. A missed pair is a Different pair it did
          not catch. A false alarm is a Same pair it called Different.
        </p>

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
        <Source file="runbook" where="“Exact values of the partial comparison (copied 2026-10-11)”" />
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
        <Source file="runbook" where="“Exact values of the partial comparison (copied 2026-10-11)”" />
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
        <p className={PROSE}>
          {`Seeds 0 and 1 gave unreadable answers on ${UNREADABLE_SHARE}, which is part of why their recall is low.`}
        </p>
        <Source file="groupGuide" where="§5.2" />
        <Source file="runbook" where="“Exact values of the partial comparison (copied 2026-10-11)”, for the counts" />
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
          <li>The gap is below zero because seed 1 has the lower F1.</li>
          <li>The interval of the gap includes zero. It just touches it.</li>
          <li>These results do not show that training improved the judge.</li>
        </ul>

        <div className="max-w-[70ch] space-y-2 rounded-2xl bg-secondary/15 p-4 text-sm text-foreground/80">
          <p className="font-bold text-foreground">What the McNemar p does and does not show</p>
          <p>This paragraph is arithmetic on the table above. The result file does not store it.</p>
          <p>
            {`The untrained model called ${calledDifferent(UNTRAINED)} pairs Different and was wrong on ${wrong(UNTRAINED)} pairs: ${UNTRAINED.falseAlarms} false alarms and ${UNTRAINED.missed} misses. Seed 1 called ${calledDifferent(SEED_1)} pairs Different and was wrong on ${wrong(SEED_1)}: ${SEED_1.falseAlarms} false alarms and ${SEED_1.missed} misses. McNemar's test compares which pairs each judge got right, so its small p goes with seed 1 being wrong on ${wrong(UNTRAINED) - wrong(SEED_1)} fewer pairs. It does not say seed 1 is the better detector. F1 is lower for seed 1 because it misses ${SEED_1.missed} of the ${TEST.different} Different pairs. A judge that answered Same every time would be right on ${TEST.same} of ${TEST.pairs} pairs and catch none.`}
          </p>
        </div>
        <Source
          file="runbook"
          where="“Exact values of the partial comparison (copied 2026-10-11)” and “Partial untuned versus fine-tuned comparison (2026-10-08)”"
        />
        <Source file="groupGuide" where="§5.2" />
        <Source file="preregistration" where="§1.2, for the comparison" />
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
        <Source file="runbook" where="“Registered agreement and sensitivity analyses (2026-10-09)”" />
        <Source file="groupGuide" where="§5.2" />
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

        <h3 className={H3}>Why it happened is not known</h3>
        <p className={PROSE}>No cause was tested. These four explanations fit the numbers, and none has been checked.</p>
        <ul aria-label="Explanations that were not tested" className={LIST}>
          <li>
            <strong className="text-foreground">Checkpoints chosen too early.</strong>{" "}
            {`Seeds 0 and 1 both use checkpoint ${SEED_1.checkpoint}, from before the first epoch ended. They are the two seeds with ${SEED_1.unreadable} and ${SEED_0.unreadable} unreadable answers. Seed 2 uses checkpoint ${SEED_2.checkpoint} and has ${SEED_2.unreadable}. The choice rested on ${VALIDATION.different} Different validation pairs, and three runs are too few to call this a pattern.`}
          </li>
          <li>
            <strong className="text-foreground">One sentence for every constructed pair.</strong>{" "}
            {`${TRAIN.constructed} of the ${TRAIN.different} Different training pairs are constructed, and all of them carry the same reason and the same sentence, written by a script. The model may have learned the sentence instead of the difference.`}
          </li>
          <li>
            <strong className="text-foreground">Different kinds of stories.</strong>{" "}
            {`Training used synthetic stories, which are ${TRAINING.syntheticNonHuman} non-human. The test stories are children's, mostly about humans.`}
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
        <Source file="preregistration" where="§1.1 for the objective, §6 for the rule on shipping, §7 for what may come next" />
        <Source
          file="changelog"
          where="§1 items 3, 4 and 9, §2 for the move to the pipeline, and the 2026-10-11 rows for the four explanations"
        />
        <Source
          file="runbook"
          where="“Registered training settings (copied 2026-10-11)”, “What the registered freeze contains” and “Held-out resume context”"
        />
        <Source file="groupGuide" where="§5.3, for the kinds of stories" />
      </section>

      <section aria-labelledby="limits" className="space-y-4">
        <h2 id="limits" className={H2}>What this does and does not show</h2>
        <ul className={LIST}>
          <li>
            The result is partial. The prompted Gemma judge is not in it: that run failed authentication, and paid
            evaluation has stopped for budget. The full registered report is incomplete.
          </li>
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
          file="runbook"
          where="“Partial untuned versus fine-tuned comparison (2026-10-08)”, “Exact values of the partial comparison (copied 2026-10-11)”, “What the registered freeze contains” and “Registered agreement and sensitivity analyses (2026-10-09)”"
        />
        <Source file="groupGuide" where="§4 and §5.2" />
      </section>
    </main>
  );
}
