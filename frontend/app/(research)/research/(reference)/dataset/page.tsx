import { ArrowSquareOut, CheckCircle, XCircle } from "@phosphor-icons/react/dist/ssr";
import { TAXONOMY_LABELS, type TaxonomyState } from "../../../_shared/constants";
import { githubUrl } from "../docs/entries";
import { AGREEMENT, EXAMPLES, REASON_PAIRS, RECORD_FIELDS, SOURCES, SPLITS, TRAINING_RECORD, type Example, type SourceKey } from "./data";

export const metadata = {
  title: "StoryBuddy Judge Dataset",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const TH = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-widest text-foreground/60";
const TD = "px-3 py-2 tabular-nums";
const SPLIT_NAMES = { train: "Train", val: "Validation" } as const;

const sum = (key: "stories" | "characters" | "pairs" | "same" | "different") =>
  SPLITS.reduce((total, split) => total + split[key], 0);

const reasonKeys = (Object.keys(REASON_PAIRS) as (keyof TaxonomyState)[]).sort(
  (a, b) => REASON_PAIRS[b] - REASON_PAIRS[a]
);

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
        {SPLIT_NAMES[record.split]} split · {record.pair_type === "constructed" ? "constructed pair" : "pipeline pair"} · pair {record.pair_id}
      </p>
    </article>
  );
}

export default function DatasetPage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Judge dataset</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          What the consistency judge was trained and tested on, and how &quot;same character&quot; was decided. Every
          number names the file it comes from.
        </p>
      </div>

      <section aria-labelledby="pairs" className="space-y-4">
        <h2 id="pairs" className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">What is in it</h2>
        <p className="max-w-[70ch] text-foreground/80">
          A pair is one reference picture of a character and one book page. Its label says whether the page shows
          that same character. The registered dataset holds {sum("pairs")} pairs from {sum("stories")} generated
          books. Synthetic stories were written by the researchers for this purpose. Donated stories were written
          by children, and they are used for the test only.
        </p>

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

        <ul className="max-w-[70ch] list-disc space-y-2 pl-5 text-foreground/80 marker:text-primary">
          <li>No story or character is in more than one split, so the judge is tested on characters it never saw.</li>
          <li>
            {`Of the train split's Different pairs, ${SPLITS[0].constructed} are constructed: one character's reference set against another character's page. The other ${sum("pairs") - SPLITS[0].constructed} pairs came out of the pipeline.`}
          </li>
          <li>Two of those constructed pairs reuse an image pair the raters had labelled Same, so the training file holds those two image pairs with both answers. The dataset is registered and was left as it is.</li>
          <li>The judge trains on synthetic stories and is tested on children&apos;s. A gap between the two shows up in the test result.</li>
        </ul>
        <Source file="runbook" where="“What the registered freeze contains”" />
        <Source file="preregistration" where="§2 and §3" />
      </section>

      <section aria-labelledby="labelling" className="space-y-4">
        <h2 id="labelling" className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">How a pair was labelled</h2>
        <ul className="max-w-[70ch] list-disc space-y-2 pl-5 text-foreground/80 marker:text-primary">
          <li>Two group members each labelled every pipeline pair once.</li>
          <li>Where their labels disagreed, the study owner settled the pair.</li>
          <li>A rater saw only the two images, never the story. The judge sees the same.</li>
          <li>
            <strong>Same</strong> when species, face, body colours and body features all match the reference.
          </li>
          <li>
            <strong>Different</strong> needs a difference the rater can name from the list below. Without one, the
            answer is Same.
          </li>
          <li>Clothing, art style and lighting are not identity. Each of them alone is Same.</li>
        </ul>

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

        <div className="max-w-[70ch] space-y-2 rounded-2xl bg-secondary/15 p-4 text-sm text-foreground/80">
          <p className="font-bold text-foreground">Two things to know before reading the rulebook</p>
          <p>
            Its opening describes one rater labelling twice. That plan was replaced on 2026-09-23 by the two raters
            and owner adjudication described above. The rulebook is frozen, so its text was left as written.
          </p>
          <p>
            Ten pairs that both raters had marked Different for clothing or style alone were reviewed with AI
            assistance and set to Same with the owner&apos;s approval. Nine are train pairs and one is validation.
            No test label changed. It is reported as a deviation.
          </p>
        </div>
        <Source file="rulebook" where="Steps 1 to 5" />
        <Source file="preregistration" where="§12, amendments of 2026-09-23 and 2026-09-30" />
        <Source file="runbook" where="“What the registered freeze contains”, for the pair counts" />
      </section>

      <section aria-labelledby="agreement" className="space-y-4">
        <h2 id="agreement" className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">How much the two raters agreed</h2>
        <p className="max-w-[70ch] text-foreground/80">
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

        <ul className="max-w-[70ch] list-disc space-y-2 pl-5 text-foreground/80 marker:text-primary">
          <li>
            The non-human κ of 0 is not &quot;no agreement&quot;. Both raters said Same on 24 of the 25 pairs, which leaves κ
            nothing to measure.
          </li>
          <li>
            Both raters were briefed by the owner, who also settled their disagreements. κ cannot catch a
            misunderstanding they shared.
          </li>
        </ul>
        <Source file="runbook" where="“Registered agreement and sensitivity analyses (2026-10-09)”" />
        <Source file="groupGuide" where="§5.2 and §6, for the limits" />
      </section>

      <section aria-labelledby="examples" className="space-y-4">
        <h2 id="examples" className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">Six example pairs</h2>
        <p className="max-w-[70ch] text-foreground/80">
          These six were hand-picked to show the rules at work. They are not a random sample and say nothing about
          how often each case occurs. All six are synthetic pairs from the train and validation splits, shown
          with their final labels. Open &quot;Frozen record&quot; on a card to see what is stored for that pair.
        </p>
        <p className="max-w-[70ch] text-foreground/80">
          No test pair is shown. The test set comes from children&apos;s donated stories, and its images are not
          published.
        </p>

        <div className="space-y-6">
          {EXAMPLES.map((example) => (
            <ExampleCard key={example.record.pair_id} example={example} />
          ))}
        </div>
      </section>

      <section aria-labelledby="record" className="space-y-4">
        <h2 id="record" className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">What a record holds</h2>
        <p className="max-w-[70ch] text-foreground/80">
          Each pair is one row in the dataset&apos;s manifest. The cards above show that row as it is stored, without the
          two image file paths. The table says what each field is and who filled it in.
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
        <Source file="manifest" where="the comments on ManifestRecord" />

        <h3 className="font-display text-xl font-extrabold tracking-tight">One training record, whole</h3>
        <p className="max-w-[70ch] text-foreground/80">
          The model is trained on a prompt and the answer it should give. Every training record uses the same prompt.
          This is the record for the constructed tortoise pair above.
        </p>
        <p className="text-xs font-semibold uppercase tracking-widest text-foreground/60">Prompt</p>
        <pre className="whitespace-pre-wrap break-words rounded-2xl bg-muted/30 p-4 font-mono text-xs text-foreground/80">{TRAINING_RECORD.prompt}</pre>
        <p className="text-xs font-semibold uppercase tracking-widest text-foreground/60">Answer the model is trained to give</p>
        <pre className="whitespace-pre-wrap break-words rounded-2xl bg-muted/30 p-4 font-mono text-xs text-foreground/80">{JSON.stringify(JSON.parse(TRAINING_RECORD.target), null, 2)}</pre>
        <p className="max-w-[70ch] text-foreground/80">
          Three of the answer&apos;s fields were never labelled: attributes_present, style_match and subjects_unique. They
          hold the same fixed value in every training record (an empty list, false and true), so they say nothing about
          this pair.
        </p>
        <Source file="buildDataset" where="constructed_records and render_rationale" />
        <Source file="runbook" where="“What the registered freeze contains”, for the two contradictory pairs" />
      </section>
    </main>
  );
}
