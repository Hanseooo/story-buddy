import Link from "next/link";
import { ArrowRight } from "@phosphor-icons/react/dist/ssr";
import Source from "../../../_shared/components/Source";
import { CORPUS, DESIGN, RESPONDENTS, SETTING, SITES, SOURCES, SPIRAL } from "./data";
import OnThisPage from "../../../_shared/components/OnThisPage";

export const metadata = {
  title: "StoryBuddy Methodology at a Glance",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const PROSE = "max-w-[70ch] text-foreground/80";
const CHIP = "inline-block rounded-full bg-secondary/30 px-2.5 py-0.5 text-xs font-bold whitespace-nowrap text-foreground";

// Where each corpus count is stated, by its source key.
const CORPUS_WHERE = { methodology: "methodology.md §3.3", groupGuide: "group-guide.md, Objective 2" } as const;

const TERMS = [
  { term: "SDLC", meaning: "software development life cycle: the order in which software is planned, built and checked." },
  { term: "Reference", meaning: "the picture of a character that later pages are drawn to match." },
  { term: "Consistency Judge", meaning: "the checker that compares a drawn page with a character's reference and answers Same or Different." },
  { term: "Held-out test set", meaning: "stories kept apart from training and used once at the end to measure the judge." },
];

const SECTIONS = [
  { id: "design", label: "Research design" },
  { id: "setting", label: "Setting" },
  { id: "site", label: "Implementation site" },
  { id: "corpus", label: "Corpus" },
  { id: "respondents", label: "Respondents" },
  { id: "terms", label: "Words used" },
];

export default function MethodologyPage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Methodology at a glance</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          The research design, where the stories came from, how many there are, and who answers the two questionnaires. Each section names
          the file it comes from.
        </p>
      </div>

      <OnThisPage sections={SECTIONS} />

      <section aria-labelledby="design" className="space-y-4">
        <h2 id="design" className={H2}>Research design</h2>
        <p className={PROSE}>
          {`The study uses a quantitative-developmental design with two parts: ${DESIGN.parts[0]}, and ${DESIGN.parts[1]}:`}
        </p>
        <ul className={`${PROSE} list-disc space-y-1 pl-6`}>
          {DESIGN.procedures.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
        <p className={PROSE}>{`The development process follows ${SPIRAL.definition}`}</p>
        <p>
          <Link
            href="/research/sdlc"
            className={`inline-flex min-h-11 items-center gap-2 rounded-xl border border-primary/20 bg-surface px-3 text-sm font-bold text-primary hover:bg-primary/5 ${FOCUS}`}
          >
            Development loops and their gates
            <ArrowRight weight="bold" className="size-4" aria-hidden />
          </Link>
        </p>
        <Source path={SOURCES.methodology} where="the opening paragraphs and §1.1" />
      </section>

      <section aria-labelledby="setting" className="space-y-4">
        <h2 id="setting" className={H2}>Setting</h2>
        <p className={PROSE}>
          {`${SETTING.school}. ${SETTING.agreement}. The methodology says ${SETTING.development}.`}
        </p>
        <Source path={SOURCES.methodology} where="§3.2" />
        <Source path={SOURCES.ethics} where="the basis the study rests on" />
      </section>

      <section aria-labelledby="site" className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="site" className={H2}>Implementation site</h2>
          <span className={CHIP}>Undecided</span>
        </div>
        <p className={PROSE}>Where the system is put in front of its users has two options. Neither is chosen yet.</p>
        <ul className="grid gap-4 sm:grid-cols-2">
          {[SITES.a, SITES.b].map((site) => (
            <li key={site} className={`${CARD} text-foreground/80`}>{site}</li>
          ))}
        </ul>
        <Source path={SOURCES.methodology} where="§3.2, Implementation site" />
      </section>

      <section aria-labelledby="corpus" className="space-y-4">
        <h2 id="corpus" className={H2}>Corpus</h2>
        <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {CORPUS.map((c) => (
            <div key={c.label} className={`${CARD} space-y-1`}>
              <dt className="font-display text-4xl font-extrabold tabular-nums">{c.count}</dt>
              <dd className="font-bold">{c.label}</dd>
              <dd className="text-sm text-foreground/60">{CORPUS_WHERE[c.source]}</dd>
            </div>
          ))}
        </dl>
        <p className={PROSE}>
          Of the 15 donated stories, 12 were generated into books and three stay quarantined on purpose. The 42 books are the 30 from
          synthetic stories plus the 12 from donated stories.
        </p>
        <Source path={SOURCES.methodology} where="§3.3" />
        <Source path={SOURCES.groupGuide} where="Objective 2" />
      </section>

      <section aria-labelledby="respondents" className="space-y-4">
        <h2 id="respondents" className={H2}>Respondents</h2>
        <ul className="grid gap-4 sm:grid-cols-2">
          <li className={`${CARD} space-y-1`}>
            <p className="font-bold">Expert validators</p>
            <p className={PROSE}>{RESPONDENTS.expert}</p>
          </li>
          <li className={`${CARD} space-y-1`}>
            <p className="font-bold">ISO/IEC 25010 respondents</p>
            <p className={PROSE}>{RESPONDENTS.iso}</p>
          </li>
        </ul>
        <p>
          <Link
            href="/research/instruments"
            className={`inline-flex min-h-11 items-center gap-2 rounded-xl border border-primary/20 bg-surface px-3 text-sm font-bold text-primary hover:bg-primary/5 ${FOCUS}`}
          >
            Evaluation instruments
            <ArrowRight weight="bold" className="size-4" aria-hidden />
          </Link>
        </p>
        <Source path={SOURCES.expert} where="Who and how" />
        <Source path={SOURCES.iso} where="Design" />
      </section>

      <section aria-labelledby="terms" className="space-y-4">
        <h2 id="terms" className={H2}>Words used on this page</h2>
        <dl className={`${CARD} space-y-3`}>
          {TERMS.map((t) => (
            <div key={t.term}>
              <dt className="font-bold">{t.term}</dt>
              <dd className={PROSE}>{t.meaning}</dd>
            </div>
          ))}
        </dl>
      </section>
    </main>
  );
}
