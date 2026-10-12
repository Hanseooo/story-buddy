import Link from "next/link";
import { ArrowRight, Warning } from "@phosphor-icons/react/dist/ssr";
import ScrollTable from "../../../_shared/components/ScrollTable";
import Source from "../../../_shared/components/Source";
import { AUDIT, BY_KIND, CHECKS, DEFECTS, EXAMPLES, KLEIN, LIMITATIONS, PHASE_05, SOURCES, TRIED, type Share } from "./data";

export const metadata = {
  title: "StoryBuddy Findings and Limitations",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const H3 = "font-display text-xl font-extrabold tracking-tight";
const TH = "px-3 py-2 text-left text-xs font-semibold uppercase tracking-widest text-foreground/60";
const TD = "px-3 py-2 align-top";
const PROSE = "max-w-[70ch] text-foreground/80";
const CHIP = "inline-block rounded-full bg-secondary/30 px-2.5 py-0.5 text-xs font-bold whitespace-nowrap text-foreground";

// Bar colours, as on the results page: blue for the shipped editor or a caught defect, coral for a defect or a wrong call.
const GOOD = "bg-primary";
const BAD = "bg-coral";
const OTHER = "bg-foreground/60";

const SECTIONS = [
  { id: "kinds", label: "By character kind" },
  { id: "defects", label: "Common defects" },
  { id: "examples", label: "Image examples" },
  { id: "checks", label: "Automatic checks" },
  { id: "editors", label: "Scene editors" },
  { id: "tried", label: "What was tried" },
  { id: "limits", label: "Limitations" },
];

const percent = ({ part, whole }: Share) => `${((part / whole) * 100).toFixed(1)}%`;
const count = ({ part, whole }: Share) => `${part} of ${whole}`;

// One labelled bar. The label and the value are text, and the bar itself is hidden from a screen reader.
function Bar({ label, value, width, tone }: { label: string; value: string; width: string; tone: string }) {
  return (
    <li className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 text-sm sm:grid-cols-[11rem_1fr_5rem]">
      <span>{label}</span> <span className="font-bold tabular-nums sm:order-last sm:text-right">{value}</span>
      <span aria-hidden className="col-span-2 block h-3 rounded-r bg-muted/60 sm:col-span-1">
        <span className={`block h-full min-w-0.5 rounded-r ${tone}`} style={{ width }} />
      </span>
    </li>
  );
}

// A named set of bars that are read against each other.
function BarGroup({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <div role="group" aria-label={title} className="space-y-2">
      <p className="font-bold">{title}</p>
      <ul className="space-y-2">{children}</ul>
      {note && <p className="text-sm text-foreground/60">{note}</p>}
    </div>
  );
}

export default function LimitationsPage() {
  const { reference, page } = CHECKS;

  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Findings and limitations</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          {`What goes wrong in the books StoryBuddy draws, how often, what was tried to fix it, and what the study must state as a limit. About half of the reviewed pages have at least one major defect: ${AUDIT.defective} of ${AUDIT.pages}. Every number names the file it comes from.`}
        </p>
      </div>

      <div className={`${CARD} flex gap-3`}>
        <Warning weight="duotone" className="mt-0.5 size-6 shrink-0 text-coral" aria-hidden />
        <div className="space-y-1">
          <p className="font-bold">Read these numbers as provisional</p>
          <p className={PROSE}>
            {`The ${AUDIT.pages} pages and ${AUDIT.references} reference pictures used AI-assisted visual assessment on ${AUDIT.date}. The owner has not confirmed the scores, so every audit number here is provisional. Only synthetic stories were reviewed. No child's story is shown or counted on this page.`}
          </p>
        </div>
      </div>

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

      <section aria-labelledby="kinds" className="space-y-4">
        <h2 id="kinds" className={H2}>Human and non-human characters</h2>
        <p className={PROSE}>
          Pages tagged as containing non-human characters have more defects than human-only pages in this audit,
          including mixed human and non-human casts. Reference counts classify the reference pictures themselves;
          page counts use the audit&apos;s tags rather than the fine-tuning character slices.
        </p>
        <div className={`${CARD} space-y-6`}>
          {BY_KIND.map((row) => (
            <BarGroup key={row.title} title={row.title}>
              <Bar label="Human characters" value={count(row.human)} width={percent(row.human)} tone={BAD} />
              <Bar label="Non-human characters" value={count(row.nonHuman)} width={percent(row.nonHuman)} tone={BAD} />
            </BarGroup>
          ))}
        </div>
        <p className={PROSE}>
          {`The audit tags ${BY_KIND[0].nonHuman.whole} of ${AUDIT.pages} shipped pages as containing non-human characters; the other ${BY_KIND[0].human.whole} are human-only. Donated stories are mostly about humans, so the overall rate likely overstates what a classroom story gets. The human-only group is too small to call a rate, and no donated story was reviewed.`}
        </p>
        <Source path={SOURCES.groupGuide} where="§5.3" />
        <Source path={SOURCES.stageAudit} where="“Provisional results”, Shipped pages and References" />
      </section>

      <section aria-labelledby="defects" className="space-y-4">
        <h2 id="defects" className={H2}>The most common major defects</h2>
        <p className={PROSE}>
          {`Of the ${AUDIT.pages} reviewed pages, how many carry each defect. A page can carry more than one.`}
        </p>
        <ScrollTable label="The most common major defects">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Defect</th>
              <th scope="col" className={`${TH} text-right`}>Pages</th>
              <th scope="col" className={TH}>What it looks like</th>
            </tr>
          </thead>
          <tbody>
            {DEFECTS.map((defect) => (
              <tr key={defect.code} className="border-b border-primary/5 last:border-0">
                <th scope="row" className={`${TD} text-left font-bold`}>{defect.name}</th>
                <td className={`${TD} text-right font-bold tabular-nums`}>{defect.pages}</td>
                <td className={`${TD} text-foreground/80`}>{defect.looksLike}</td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path={SOURCES.stageAudit} where="“Provisional results”, Where the 77 come from" />
        <Source path={SOURCES.groupGuide} where="§5.3, for what each defect looks like" />
      </section>

      <section aria-labelledby="examples" className="space-y-6">
        <h2 id="examples" className={H2}>Examples of visible limitations</h2>
        <p className={PROSE}>
          Hand-picked synthetic examples illustrate these failures; they do not establish their frequency or
          current performance. They are training-split captures from the provisional October 8, 2026 audit,
          made with generation prompt version 4. They are illustrations, not new independent human labels.
        </p>
        <div className="space-y-8">
          {EXAMPLES.map((example) => (
            <article key={example.storyId} className="grid gap-5 border-t border-primary/10 pt-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:gap-8">
              <div className="space-y-3">
                <h3 className={H3}>{example.title}</h3>
                <p className="text-sm text-foreground/60">{example.style} · synthetic · training split</p>
                <div className="space-y-1">
                  <p className="text-sm font-bold">Requested</p>
                  <blockquote className="text-sm text-foreground/80">“{example.requirement}”</blockquote>
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-bold">Visible in the image</p>
                  <p className="text-sm text-foreground/80">{example.observation}</p>
                </div>
                <p className="text-xs text-foreground/60">{example.storyId} · {example.role}</p>
              </div>
              <div className={`grid content-start gap-4 ${example.images.length > 1 ? "sm:grid-cols-2" : ""}`}>
                {example.images.map((image) => (
                  <figure key={image.src} className="min-w-0 space-y-2">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={image.src}
                      alt={image.alt}
                      width={768}
                      height={576}
                      loading="lazy"
                      className="h-auto w-full rounded-2xl border border-primary/10 bg-muted/20"
                    />
                    <figcaption className="text-xs text-foreground/60">{image.caption}</figcaption>
                  </figure>
                ))}
              </div>
            </article>
          ))}
        </div>
        <p className={PROSE}>
          <Link href="/research/dataset#examples" className={`inline-flex min-h-11 items-center gap-1.5 rounded-lg font-bold text-primary hover:text-primary-deep hover:underline ${FOCUS}`}>
            See reference/page identity-drift examples
            <ArrowRight weight="bold" className="size-4" aria-hidden />
          </Link>
        </p>
        <Source path={SOURCES.examples} where="Selected examples, requirements and source provenance" />
        <Source path={SOURCES.stageAudit} where="Provisional review and its limitations" />
      </section>

      <section aria-labelledby="checks" className="space-y-4">
        <h2 id="checks" className={H2}>What the automatic checks caught</h2>
        <p className={PROSE}>
          The pipeline checks each reference picture and each page with an AI judge before it ships them. This is
          what those stored checks had said about the images the reviewers scored.
        </p>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className={`${CARD} space-y-4`}>
            <h3 className={H3}>The reference check</h3>
            <BarGroup title={`Of the ${reference.defective} defective references`}>
              <Bar
                label="The check failed it"
                value={count({ part: reference.defectiveFailed, whole: reference.defective })}
                width={percent({ part: reference.defectiveFailed, whole: reference.defective })}
                tone={GOOD}
              />
            </BarGroup>
            <BarGroup title={`Of the ${reference.acceptable} acceptable references`}>
              <Bar
                label="The check failed it anyway"
                value={count({ part: reference.acceptableFailed, whole: reference.acceptable })}
                width={percent({ part: reference.acceptableFailed, whole: reference.acceptable })}
                tone={BAD}
              />
            </BarGroup>
            <p className="text-sm text-foreground/80">
              The check finds most bad references. The pipeline then ships the best of the failing draws, so every
              defect it found still reached the pages.
            </p>
          </div>
          <div className={`${CARD} space-y-4`}>
            <h3 className={H3}>The page check</h3>
            <BarGroup title={`Of the ${page.defective} defective pages`}>
              <Bar
                label="The check passed it"
                value={count({ part: page.defectivePassed, whole: page.defective })}
                width={percent({ part: page.defectivePassed, whole: page.defective })}
                tone={BAD}
              />
            </BarGroup>
            <BarGroup title={`Of the ${page.acceptable} acceptable pages`}>
              <Bar
                label="The check failed it anyway"
                value={count({ part: page.acceptableFailed, whole: page.acceptable })}
                width={percent({ part: page.acceptableFailed, whole: page.acceptable })}
                tone={BAD}
              />
            </BarGroup>
            <p className="text-sm text-foreground/80">
              The page check compares a page with its reference picture. A mistake copied from the reference
              matches the reference, so it passes.
            </p>
          </div>
        </div>
        <Source path={SOURCES.stageAudit} where="“Provisional results”, References and Page gate" />
      </section>

      <section aria-labelledby="editors" className="space-y-4">
        <h2 id="editors" className={H2}>The scene editor against two others</h2>
        <p className={PROSE}>
          The scene editor is the image model that draws each page from the reference pictures. StoryBuddy ships
          Qwen-Image-Edit. Two other editors were set against it, and neither replaced it.
        </p>
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <div className={`${CARD} space-y-4`}>
            <h3 className={H3}>FLUX.2 klein, October 2026</h3>
            <p className="text-sm text-foreground/80">
              {`${KLEIN.pages} random pages, drawn by both editors and scored with the editor's name hidden. klein's style may be recognisable, so the blinding is partial.`}
            </p>
            <BarGroup title="Pages with a duplicate character">
              <Bar
                label="Qwen-Image-Edit"
                value={count({ part: KLEIN.duplicates.qwen, whole: KLEIN.pages })}
                width={percent({ part: KLEIN.duplicates.qwen, whole: KLEIN.pages })}
                tone={GOOD}
              />
              <Bar
                label="klein"
                value={count({ part: KLEIN.duplicates.klein, whole: KLEIN.pages })}
                width={percent({ part: KLEIN.duplicates.klein, whole: KLEIN.pages })}
                tone={OTHER}
              />
            </BarGroup>
            <BarGroup title="Pages where the character lost its identity">
              <Bar
                label="Qwen-Image-Edit"
                value={count({ part: KLEIN.identityLost.qwen, whole: KLEIN.pages })}
                width={percent({ part: KLEIN.identityLost.qwen, whole: KLEIN.pages })}
                tone={GOOD}
              />
              <Bar
                label="klein"
                value={count({ part: KLEIN.identityLost.klein, whole: KLEIN.pages })}
                width={percent({ part: KLEIN.identityLost.klein, whole: KLEIN.pages })}
                tone={OTHER}
              />
            </BarGroup>
            <p className="text-sm text-foreground/80">
              klein drew as many duplicates and lost the character more often. It was rejected, and Qwen-Image-Edit
              stays (ADR-063).
            </p>
          </div>
          <div className={`${CARD} space-y-4`}>
            <h3 className={H3}>OmniGen2, July 2026</h3>
            <p className="text-sm text-foreground/80">
              One invented character, a three-eyed lizard-bird. How often it stayed recognisable on a page, with
              its reference picture and without it.
            </p>
            <BarGroup title="Qwen-Image-Edit">
              <Bar label="With the reference" value={PHASE_05.qwen.withReference} width={PHASE_05.qwen.withReference} tone={GOOD} />
              <Bar label="Without it" value={PHASE_05.qwen.without} width={PHASE_05.qwen.without} tone={OTHER} />
            </BarGroup>
            <BarGroup title="OmniGen2 (tried as a backup)">
              <Bar label="With the reference" value={PHASE_05.omnigen.withReference} width={PHASE_05.omnigen.withReference} tone={GOOD} />
              <Bar label="Without it" value={PHASE_05.omnigen.without} width={PHASE_05.omnigen.without} tone={OTHER} />
            </BarGroup>
            <p className="text-sm text-foreground/80">
              This was a build check, scored without blinding, and it is not a finding of the study. Both runs
              failed the gate set in advance. Qwen-Image-Edit stayed the editor, and the failed gate is carried as a
              limitation.
            </p>
          </div>
        </div>
        <Source path={SOURCES.groupGuide} where="§5.4 for klein and §5.1 for OmniGen2" />
        <Source path={SOURCES.probes} where="“Blinded klein screen”" />
        <Source path={SOURCES.phase05} where="Probe 1" />
      </section>

      <section aria-labelledby="tried" className="space-y-4">
        <h2 id="tried" className={H2}>What was tried in October</h2>
        <p className={PROSE}>
          The October tests the group guide lists, one row each. Tests that failed are listed with the rest.
        </p>
        <ScrollTable label="What was tried in October">
          <thead>
            <tr className="border-b border-primary/10">
              <th scope="col" className={TH}>Tried</th>
              <th scope="col" className={TH}>Result</th>
              <th scope="col" className={TH}>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {TRIED.map((row) => (
              <tr key={row.tried} className="border-b border-primary/5 last:border-0">
                <th scope="row" className={`${TD} w-[30%] text-left font-bold`}>{row.tried}</th>
                <td className={`${TD} text-foreground/80`}>{row.result}</td>
                <td className={TD}>
                  <span className={CHIP}>{row.outcome}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </ScrollTable>
        <Source path={SOURCES.groupGuide} where="§5.4" />
        <Source path={SOURCES.probes} where="“Findings and changes”, for each test's plan and result" />
      </section>

      <section aria-labelledby="limits" className="space-y-4">
        <h2 id="limits" className={H2}>Limitations to state</h2>
        <p className={PROSE}>What the study says out loud as a weakness, in the group guide&apos;s own words.</p>
        <ol className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {LIMITATIONS.map((limit) => (
            <li key={limit.title} className={`${CARD} space-y-2`}>
              <span className={CHIP}>{limit.area}</span>
              <h3 className={H3}>{limit.title}</h3>
              <p className="text-sm text-foreground/80">{limit.body}</p>
            </li>
          ))}
        </ol>
        <p className={PROSE}>
          <Link
            href="/research/results"
            className={`inline-flex min-h-11 items-center gap-1.5 rounded-lg font-bold text-primary hover:text-primary-deep hover:underline ${FOCUS}`}
          >
            See the judge results
            <ArrowRight weight="bold" className="size-4" aria-hidden />
          </Link>
        </p>
        <Source path={SOURCES.groupGuide} where="§6" />
        <Source path={SOURCES.probes} where="“Limitations to carry into the write-up”" />
      </section>
    </main>
  );
}
