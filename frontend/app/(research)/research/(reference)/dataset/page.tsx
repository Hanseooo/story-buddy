import { CheckCircle, XCircle } from "@phosphor-icons/react/dist/ssr";
import { TAXONOMY_LABELS, type TaxonomyState } from "../../../_shared/constants";
import ChartFigure from "../../../_shared/components/ChartFigure";
import ScrollTable from "../../../_shared/components/ScrollTable";
import Source from "../../../_shared/components/Source";
import {
  AGREEMENT,
  CHARACTER_KINDS,
  CONSTRUCTED,
  DEFINITIONS,
  DOCUMENTED_TOOL_REASONS,
  DONATED_CANDIDATES,
  EXAMPLES,
  EXPLORATORY,
  FLOW_DIAGRAM,
  LABEL_FACTS,
  OWNER_TOOL_REASONS,
  PAIR_FACTS,
  PROCESS_STEPS,
  REASON_PAIRS,
  RECORD_FIELDS,
  ROSTER_MISSES,
  SOURCES,
  SPLITS,
  TRAINING_RECORD,
  TRAIN_DIFFERENT,
  VERBATIM_RECORD,
  type Example,
} from "./data";

export const metadata = {
  title: "StoryBuddy Judge Dataset",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const TH = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-widest text-foreground/60";
const TD = "px-3 py-2 tabular-nums";
const PROSE = "max-w-[70ch] text-foreground/80";
const LIST = "max-w-[70ch] list-disc space-y-2 pl-5 text-foreground/80 marker:text-primary";
const SPLIT_NAMES = { train: "Train", val: "Validation" } as const;

const sum = (key: "stories" | "characters" | "pairs" | "same" | "different") =>
  SPLITS.reduce((total, split) => total + split[key], 0);

const reasonKeys = (Object.keys(REASON_PAIRS) as (keyof TaxonomyState)[]).sort(
  (a, b) => REASON_PAIRS[b] - REASON_PAIRS[a]
);

const answer = (same: boolean) => (same ? "Same" : "Different");

function ratersLine(answers: Example["raterAnswers"]) {
  if (!answers) return "Not shown to the raters. A script set the label.";
  if (answers[0] === answers[1]) return `Both raters first answered ${answer(answers[0])}.`;
  return `One rater first answered ${answer(answers[0])} and the other ${answer(answers[1])}. The owner settled it.`;
}

function ExampleCard({ example }: { example: Example }) {
  const { record } = example;
  return (
    <article className={`${CARD} space-y-4`}>
      <header className="flex flex-wrap items-center gap-2">
        {record.same_character ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-success/15 px-3 py-1 text-sm font-bold text-success">
            <CheckCircle weight="fill" className="size-4" aria-hidden />
            <span>Same character</span>
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-destructive/15 px-3 py-1 text-sm font-bold text-destructive">
            <XCircle weight="fill" className="size-4" aria-hidden />
            <span>Different character</span>
          </span>
        )}
        {record.failure_reasons.map((reason) => (
          <span key={reason} className="rounded-full bg-muted/60 px-3 py-1 text-sm font-semibold text-foreground/80">
            {TAXONOMY_LABELS[reason].label}
          </span>
        ))}
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {[
          { caption: "Reference", image: example.reference },
          { caption: "Book page", image: example.page },
        ].map(({ caption, image }) => (
          <figure key={caption} className="space-y-2">
            <figcaption className="text-xs font-semibold uppercase tracking-widest text-foreground/60">{caption}</figcaption>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={image.src}
              alt={image.alt}
              width={768}
              height={576}
              loading="lazy"
              className="h-auto w-full rounded-2xl border border-primary/10 bg-muted/20"
            />
          </figure>
        ))}
      </div>

      <p className="max-w-[70ch] text-sm text-foreground/80">{example.note}</p>
      <p className="text-sm text-foreground/80">{ratersLine(example.raterAnswers)}</p>
      <details className="rounded-2xl bg-muted/30">
        <summary className={`min-h-11 cursor-pointer rounded-2xl px-4 py-3 text-sm font-bold ${FOCUS}`}>Frozen record</summary>
        <pre className="whitespace-pre-wrap break-words px-4 pb-4 font-mono text-xs text-foreground/80">{JSON.stringify(example.record, null, 2)}</pre>
      </details>
      <p className="font-mono text-xs text-foreground/60">
        {SPLIT_NAMES[record.split]} split · {record.pair_type === "constructed" ? "constructed pair" : "natural pair"} · pair {record.pair_id}
      </p>
    </article>
  );
}

export default function DatasetPage() {
  const { pairs, books, natural, constructed, laterAttempt } = PAIR_FACTS;
  const kept = LABEL_FACTS.kept;

  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Judge dataset</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          What the consistency judge was trained and tested on, and how &quot;same character&quot; was decided. Every
          number names the file it comes from.
        </p>
      </div>

      <section aria-labelledby="words" className="space-y-4">
        <h2 id="words" className={H2}>Words used on this page</h2>
        <dl className={`${CARD} grid gap-x-8 gap-y-4 sm:grid-cols-2`}>
          {DEFINITIONS.map(({ term, meaning }) => (
            <div key={term} className="space-y-1">
              <dt className="font-bold text-foreground">{term}</dt>
              <dd className="text-sm text-foreground/80">{meaning}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section aria-labelledby="pairs" className="space-y-4">
        <h2 id="pairs" className={H2}>What is a pair?</h2>
        <p className={PROSE}>
          A pair is two pictures. The first is a character&apos;s <strong>reference</strong>, the one portrait the app
          drew of that character before it drew the book. The second is one drawing of a book page where that
          character should appear. The label says whether both pictures show the same character.
        </p>
        <p className={PROSE}>
          The app often draws a page several times before it keeps one. Every attempt counts as a page drawing,
          including the rejected ones, because the judge has to check every attempt when the app runs.{" "}
          {laterAttempt} of the {natural} natural pairs use a second or later attempt. A page with two characters
          makes two pairs, one for each character&apos;s reference.
        </p>
        <p className={PROSE}>
          The dataset has {pairs} pairs from {books} books. Of these, {natural} are natural pairs: drawn by the app
          and labelled by people. {constructed} are constructed pairs: made by a script and labelled by no one.
          Synthetic stories were written by the researchers for this purpose. Donated stories were written by
          children, and they are used for the test only.
        </p>
        <Source path={SOURCES.runbook} where="“Counts recounted for the research page refresh (2026-11-21)”" />
        <Source path={SOURCES.adr060} where="why rejected attempts count" />
      </section>

      <section aria-labelledby="process" className="space-y-4">
        <h2 id="process" className={H2}>From story to test, in ten steps</h2>
        <ol aria-label="The ten steps from story to test" className="max-w-[70ch] list-decimal space-y-3 pl-6 text-foreground/80 marker:font-bold marker:text-primary">
          {PROCESS_STEPS.map((step) => (
            <li key={step.name} className="pl-1">
              <strong className="text-foreground">{step.name}.</strong> {step.text}
            </li>
          ))}
        </ol>

        <ChartFigure
          id="dataset-build-flow"
          wide
          alt="The ten steps from story to held-out test: stories, generated books, pairs, two raters, adjudication, freeze, splits, training, checkpoint choice and one read of the test set."
          asOf={FLOW_DIAGRAM.asOf}
          png={FLOW_DIAGRAM.png}
          source={FLOW_DIAGRAM.source}
          sourceNoun="the editable diagram"
          caption={<strong className="text-foreground">Dataset build and annotation flow. On a narrow screen, scroll the diagram sideways.</strong>}
        >
          <div
            role="region"
            aria-label="Dataset flow diagram. It scrolls sideways on a narrow screen."
            tabIndex={0}
            className={`overflow-x-auto rounded-2xl border border-primary/10 bg-white ${FOCUS}`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={FLOW_DIAGRAM.svg}
              alt="The ten steps from story to held-out test: stories, generated books, pairs, two raters, adjudication, freeze, splits, training, checkpoint choice and one read of the test set."
              width={1240}
              height={604}
              className="h-auto w-full min-w-[60rem] lg:min-w-0"
            />
          </div>
        </ChartFigure>
        <Source path={SOURCES.runbook} where="“Dataset handoff (2026-09-30)”" />
      </section>

      <section aria-labelledby="record" className="space-y-4">
        <h2 id="record" className={H2}>One record</h2>
        <p className={PROSE}>
          Each pair is one row in the dataset&apos;s manifest file. This is validation row 033b8372e89e4c06, as stored.
          Cut text is marked with “…”. It scrolls sideways inside its box.
        </p>
        <div
          role="region"
          aria-label="One record, as stored"
          tabIndex={0}
          className={`overflow-x-auto rounded-2xl bg-muted/30 neo-border ${FOCUS}`}
        >
          <pre className="w-max min-w-full p-4 font-mono text-xs text-foreground/80">{JSON.stringify(VERBATIM_RECORD, null, 2)}</pre>
        </div>
        <p className={PROSE}>
          Read it as: a validation pair from synthetic story syn-025, drawn by the app, whose final answer is Same,
          with no reasons ticked.
        </p>

        <ScrollTable label="What each field of a record means">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30">
              <th scope="col" className={TH}>Field</th>
              <th scope="col" className={TH}>Meaning</th>
            </tr>
          </thead>
          <tbody>
            {RECORD_FIELDS.map(({ field, meaning }) => (
              <tr key={field} className="border-b border-primary/10 align-top last:border-b-0">
                <th scope="row" className="px-3 py-2 text-left font-mono font-bold">{field}</th>
                <td className="px-3 py-2">{meaning}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <p className="text-sm text-foreground/60">
          The record is row 033b8372e89e4c06 of <span className="font-mono">manifest.val.jsonl</span> in the registered
          freeze. The freeze is kept on the team&apos;s machines, not in the repo.
        </p>
        <Source path={SOURCES.manifest} where="the comments on ManifestRecord" />
      </section>

      <section aria-labelledby="labelling" className="space-y-4">
        <h2 id="labelling" className={H2}>How a pair was labelled</h2>
        <ul className={LIST}>
          <li>
            <strong>Same</strong>: species, face, body colours and countable body parts (eyes, ears, tail, horns, wings,
            limbs) all match the reference. Pose, expression, clothing, art style and lighting may change.
          </li>
          <li>
            <strong>Different</strong>: at least one of those features is wrong, or the character is absent. The rater
            has to tick a reason from the list below. If no reason applies, the answer is Same.
          </li>
          <li>A rater saw only the two images, never the story. The judge sees the same.</li>
        </ul>

        <h3 className="font-display text-xl font-extrabold tracking-tight">Who decided</h3>
        <ul className={LIST}>
          <li>Two group members labelled all {natural} natural pairs, each on their own, seeing only the two pictures.</li>
          <li>
            The study owner settled the {LABEL_FACTS.conflicted} pairs whose labels differed on any field, {LABEL_FACTS.differedOnSameDifferent}{" "}
            of them on Same or Different. The owner could see which rater gave which label.
          </li>
          <li>
            The owner also relabelled {LABEL_FACTS.aiAssisted} pairs with AI assistance, after both raters had answered
            Different for clothing or style alone. This is reported as a deviation from the plan.
          </li>
          <li>Constructed pairs were not labelled by anyone.</li>
        </ul>

        <div className="max-w-[70ch] space-y-1 rounded-2xl bg-secondary/15 p-4 text-foreground/90">
          <p className="font-bold text-foreground">Clothing or art style alone is Same.</p>
          <p className="text-sm">
            A rater ticks Wrong Clothing or Wrong Style only when the pair is already Different for another reason.
          </p>
        </div>

        <ScrollTable label="Reasons a pair is Different">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30">
              <th scope="col" className={TH}>Reason</th>
              <th scope="col" className={TH}>Counts</th>
              <th scope="col" className={TH}>Does not count</th>
              <th scope="col" className={TH}>Pairs</th>
            </tr>
          </thead>
          <tbody>
            {reasonKeys.map((reason) => (
              <tr key={reason} className="border-b border-primary/10 align-top last:border-b-0">
                <th scope="row" className="px-3 py-2 text-left font-bold">{TAXONOMY_LABELS[reason].label}</th>
                <td className="px-3 py-2">{TAXONOMY_LABELS[reason].description}</td>
                <td className="px-3 py-2 text-foreground/70">{TAXONOMY_LABELS[reason].doesNotCount}</td>
                <td className={TD}>{REASON_PAIRS[reason]}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <p className="max-w-[70ch] text-sm text-foreground/70">
          A pair can carry more than one reason, so the last column adds up to more than the {sum("different")}{" "}
          Different pairs.
        </p>

        <h3 className="font-display text-xl font-extrabold tracking-tight">What changed, and what is known to be wrong</h3>
        <ul className={LIST}>
          <li>
            The AI-assisted review changed no test label. Ordinary adjudication settled conflicted test pairs as it did
            every split, and it changed one test label.
          </li>
          <li>
            In all, {LABEL_FACTS.changed} final labels differ from both raters&apos; first answer: the raters said
            Different and the final label is Same. {LABEL_FACTS.aiAssisted} are the AI-assisted pairs and {LABEL_FACTS.changedByAdjudication}{" "}
            came from ordinary adjudication.
          </li>
          <li>
            Known errors, kept because the freeze is registered: {kept.total} final labels are Different with only Wrong
            Clothing or Wrong Style ticked. The rulebook says those are Same. They are train {kept.train}, validation{" "}
            {kept.validation}, test {kept.test}.
          </li>
        </ul>
        <p className="max-w-[70ch] rounded-2xl bg-muted/30 p-4 text-sm text-foreground/80">
          The rulebook&apos;s opening describes one rater labelling twice. That plan was replaced on 2026-09-23 by the
          two raters and owner adjudication described here. The rulebook is frozen, so its text was left as written.
        </p>
        <Source path={SOURCES.rulebook} where="Steps 1 to 5" />
        <Source path={SOURCES.preregistration} where="§12, amendments of 2026-09-23 and 2026-09-30" />
        <Source path={SOURCES.runbook} where="“Counts recounted for the research page refresh (2026-11-21)”" />
      </section>

      <section aria-labelledby="tool" className="space-y-4">
        <h2 id="tool" className={H2}>Why the team built its own labelling tool</h2>
        <p className={PROSE}>The team built a labelling page instead of using spreadsheets or an off-the-shelf tool. The owner gave these reasons.</p>
        <ul className={LIST}>
          {OWNER_TOOL_REASONS.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
        <p className={PROSE}>The repo also documents these reasons.</p>
        <ul className={LIST}>
          {DOCUMENTED_TOOL_REASONS.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
        <p className={PROSE}>
          A demo of the tool exists, but it needs signing in as a researcher, so it cannot be opened from this page. The
          example pairs below show what a rater sees: two pictures.
        </p>
        <Source path={SOURCES.annotationSurface} where="§1a, the owner’s reasons" />
        <Source path={SOURCES.adr026} where="the decision and its reasons" />
        <Source path={SOURCES.labellingDemo} where="how the demo works" />
      </section>

      <section aria-labelledby="splits" className="space-y-4">
        <h2 id="splits" className={H2}>How the splits were made, and why</h2>

        <ScrollTable label="Pairs in each split">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30">
              <th scope="col" className={TH}>Split</th>
              <th scope="col" className={TH}>Stories from</th>
              <th scope="col" className={TH}>Stories</th>
              <th scope="col" className={TH}>Characters</th>
              <th scope="col" className={TH}>Pairs</th>
              <th scope="col" className={TH}>Same</th>
              <th scope="col" className={TH}>Different</th>
            </tr>
          </thead>
          <tbody>
            {SPLITS.map((split) => (
              <tr key={split.name} className="border-b border-primary/10">
                <th scope="row" className="px-3 py-2 text-left font-bold">{split.name}</th>
                <td className={TD}>{split.storiesFrom}</td>
                <td className={TD}>{split.stories}</td>
                <td className={TD}>{split.characters}</td>
                <td className={TD}>{split.pairs}</td>
                <td className={TD}>{split.same}</td>
                <td className={TD}>{split.different}</td>
              </tr>
            ))}
            <tr className="bg-muted/20 font-bold">
              <th scope="row" className="px-3 py-2 text-left">All</th>
              <td className={TD} />
              <td className={TD}>{sum("stories")}</td>
              <td className={TD}>{sum("characters")}</td>
              <td className={TD}>{sum("pairs")}</td>
              <td className={TD}>{sum("same")}</td>
              <td className={TD}>{sum("different")}</td>
            </tr>
          </tbody>
        </ScrollTable>

        <ul className={LIST}>
          <li>Splits are by story. Each story got its split when it was entered, and all its characters and pages go with it.</li>
          <li>No story or character is in two splits, so the judge is tested on characters it never saw.</li>
          <li>Train is 24 synthetic stories and validation is 6. Each of the three art styles has 8 train stories and 2 validation stories.</li>
          <li>
            The held-out test set is every donated story that finished: 12 of the {DONATED_CANDIDATES} donated candidate
            stories. The other 3 failed in the app and are not in the dataset.
          </li>
          <li>
            <strong>Why the test set is donated stories only.</strong> There are too few donated characters to spare any
            for training. Testing only on them also means the score is measured on real children&apos;s writing, so a gap
            between synthetic and real stories shows up in the result.
          </li>
          <li>
            Constructed pairs are in train only. They come from {CONSTRUCTED.matches} hand-picked character matches of the same
            species and art style, {CONSTRUCTED.humanMatches} of them human with human. Each match is a character&apos;s reference set against
            every training page of the other character.
          </li>
          <li>
            {`Of train's ${TRAIN_DIFFERENT.total} Different pairs, ${TRAIN_DIFFERENT.constructed} are constructed and ${TRAIN_DIFFERENT.natural} come from the app. Separately, ${natural} of all ${pairs} pairs come from the app.`}
          </li>
          <li>
            Two of the constructed pairs reuse an image pair the raters had labelled Same, so the training file holds
            those two image pairs with both answers. The dataset is registered and was left as it is.
          </li>
          <li>
            No class balancing was planned. Validation has only {SPLITS[1].different} Different pairs, and every checkpoint
            choice rests on them.
          </li>
          <li>{`A separate exploratory freeze excluded ${EXPLORATORY.excluded} disputed synthetic training pairs, leaving ${EXPLORATORY.trainPairs}. The completed three-seed training used the registered freeze and kept all ${SPLITS[0].pairs} pairs.`}</li>
          <li>
            Reason not recorded: why stories syn-025 to syn-030 became validation. Reason not recorded: why validation
            is 6 stories.
          </li>
        </ul>

        <h3 className="font-display text-xl font-extrabold tracking-tight">Human and non-human pairs</h3>
        <p className={PROSE}>
          This table counts each generated character by its species. {`An earlier version of this table matched character names to the intake roster and counted ${ROSTER_MISSES} animals or machines as human.`}{" "}
          The counts cover all pairs, including constructed ones.
        </p>
        <ScrollTable label="Human and non-human training and validation pairs">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30">
              <th scope="col" className={TH}>Split</th>
              <th scope="col" className={TH}>Human characters</th>
              <th scope="col" className={TH}>Non-human characters</th>
              <th scope="col" className={TH}>Human pairs</th>
              <th scope="col" className={TH}>Non-human pairs</th>
            </tr>
          </thead>
          <tbody>
            {CHARACTER_KINDS.map((row) => (
              <tr key={row.split} className="border-b border-primary/10">
                <th scope="row" className="px-3 py-2 text-left font-bold">{row.split}</th>
                <td className={TD}>{row.humanCharacters}</td>
                <td className={TD}>{row.nonHumanCharacters}</td>
                <td className={TD}>{row.humanPairs}</td>
                <td className={TD}>{row.nonHumanPairs}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path={SOURCES.runbook} where="“What the registered freeze contains” and “Counts recounted for the research page refresh (2026-11-21)”" />
        <Source path={SOURCES.preregistration} where="§2, §3 and the style-allocation amendment" />
      </section>

      <section aria-labelledby="agreement" className="space-y-4">
        <h2 id="agreement" className={H2}>How much the two raters agreed</h2>
        <p className={PROSE}>
          Agreement is how often the two raters gave the same Same-or-Different answer. Cohen&apos;s κ corrects that
          for the agreement chance alone would give.
        </p>

        <ScrollTable label="Agreement between the two raters">
          <thead>
            <tr className="border-b border-primary/15 bg-muted/30">
              <th scope="col" className={TH}>Pairs compared</th>
              <th scope="col" className={TH}>Pairs</th>
              <th scope="col" className={TH}>Cohen&apos;s κ</th>
              <th scope="col" className={TH}>Agreement</th>
            </tr>
          </thead>
          <tbody>
            {AGREEMENT.map((row) => (
              <tr key={row.slice} className="border-b border-primary/10 last:border-b-0">
                <th scope="row" className="px-3 py-2 text-left font-bold">{row.slice}</th>
                <td className={TD}>{row.pairs}</td>
                <td className={TD}>{row.kappa}</td>
                <td className={TD}>{row.agreement}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>

        <ul className={LIST}>
          <li>
            The non-human κ of 0 is not &quot;no agreement&quot;. Both raters said Same on 24 of the 25 pairs, which leaves κ
            nothing to measure.
          </li>
          <li>
            Both raters were briefed by the owner, who also settled their disagreements. κ cannot catch a
            misunderstanding they shared.
          </li>
        </ul>
        <Source path={SOURCES.runbook} where="“Registered agreement and sensitivity analyses (2026-10-09)”" />
        <Source path={SOURCES.groupGuide} where="§5.2 and §6, for the limits" />
      </section>

      <section aria-labelledby="examples" className="space-y-4">
        <h2 id="examples" className={H2}>Six example pairs</h2>
        <p className={PROSE}>
          These six were hand-picked to show the rules at work. They are not a random sample and say nothing about
          how often each case occurs. All six are synthetic pairs from the train and validation splits, shown
          with their final labels. Open &quot;Frozen record&quot; on a card to see what is stored for that pair.
        </p>
        <p className={PROSE}>
          No test pair is shown. The test set comes from children&apos;s donated stories, and its images are not
          published.
        </p>

        <div className="space-y-6">
          {EXAMPLES.map((example) => (
            <ExampleCard key={example.record.pair_id} example={example} />
          ))}
        </div>
      </section>

      <section aria-labelledby="training" className="space-y-4">
        <h2 id="training" className={H2}>One training record, whole</h2>
        <p className={PROSE}>
          The model is trained on a prompt and the answer it should give. Every training record uses the same prompt.
          This is the record for the constructed tortoise pair above.
        </p>
        <p className="text-xs font-semibold uppercase tracking-widest text-foreground/60">Prompt</p>
        <pre className="whitespace-pre-wrap break-words rounded-2xl bg-muted/30 p-4 font-mono text-xs text-foreground/80">{TRAINING_RECORD.prompt}</pre>
        <p className="text-xs font-semibold uppercase tracking-widest text-foreground/60">Answer the model is trained to give</p>
        <pre className="whitespace-pre-wrap break-words rounded-2xl bg-muted/30 p-4 font-mono text-xs text-foreground/80">{JSON.stringify(JSON.parse(TRAINING_RECORD.target), null, 2)}</pre>
        <p className={PROSE}>
          Three of the answer&apos;s fields were never labelled: attributes_present, style_match and subjects_unique. They
          hold the same fixed value in every training record (an empty list, false and true), so they say nothing about
          this pair.
        </p>
        <Source path={SOURCES.buildDataset} where="constructed_records and render_rationale" />
        <Source path={SOURCES.runbook} where="“What the registered freeze contains”, for the two contradictory pairs" />
      </section>
    </main>
  );
}
