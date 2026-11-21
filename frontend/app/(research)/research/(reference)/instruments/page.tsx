import Source from "../../../_shared/components/Source";
import { ANALYSIS_TBD, EXPERT, ISO, ISO_GROUPS, PENDING, QUESTIONS, SOURCES } from "./data";

export const metadata = {
  title: "StoryBuddy Evaluation Instruments",
};

const CARD = "rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6";
const H2 = "font-display text-2xl font-extrabold tracking-tight md:text-3xl";
const H3 = "font-display text-xl font-extrabold tracking-tight";
const PROSE = "max-w-[70ch] text-foreground/80";
const CHIP = "inline-block rounded-full bg-secondary/30 px-2.5 py-0.5 text-xs font-bold whitespace-nowrap text-foreground";
const NUMBER = "flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-bold tabular-nums text-primary";

export default function InstrumentsPage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Evaluation instruments</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          The two questionnaires, word for word as the tracked copies print them. Neither survey has been run, so no results are shown.
        </p>
      </div>

      <section aria-labelledby="expert" className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="expert" className={H2}>Expert questionnaire</h2>
          <span className={CHIP}>{PENDING}</span>
        </div>
        <p className="text-sm font-bold uppercase tracking-widest text-foreground/60">Objective 3</p>
        <div className={`${CARD} space-y-2`}>
          <p className={PROSE}>{EXPERT.evaluators}</p>
          <p className={PROSE}>{EXPERT.procedure}</p>
          <p className={PROSE}>{EXPERT.format} {EXPERT.answerStyle}</p>
          <p className={PROSE}>
            Analysis method: <span className={CHIP}>{ANALYSIS_TBD}</span>
          </p>
        </div>
        <h3 className={H3}>The seven questions</h3>
        <p className="max-w-[70ch] text-sm text-foreground/60">
          The text under each question is a guide for the answer. It is not a separate question.
        </p>
        <ol aria-label="The seven questions" className="space-y-3">
          {QUESTIONS.map((q) => (
            <li key={q.n} value={q.n} className={`${CARD} flex gap-3`}>
              <span aria-hidden className={NUMBER}>{q.n}</span>
              <div className="min-w-0 space-y-1">
                <p className="font-bold">{q.heading}</p>
                <p className="max-w-[70ch] text-sm text-foreground/60">{q.prompt}</p>
              </div>
            </li>
          ))}
        </ol>
        <Source path={SOURCES.expert} where="Who and how; III. Questions" />
      </section>

      <section aria-labelledby="iso" className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="iso" className={H2}>ISO/IEC 25010 questionnaire</h2>
          <span className={CHIP}>{PENDING}</span>
        </div>
        <p className="text-sm font-bold uppercase tracking-widest text-foreground/60">Objective 5</p>
        <div className={`${CARD} space-y-2`}>
          <p className={PROSE}>23 statements under 6 headings. {ISO.scale}</p>
          <p className={PROSE}>Respondents rate each statement on a Likert scale: {ISO.rating}</p>
          <p className={PROSE}>{ISO.respondents}</p>
          <p className={PROSE}>{ISO.statistics} Both are checks of the questionnaire itself, and this study does not use them.</p>
          <p className={PROSE}>{ISO.consent}</p>
          <p className="text-sm text-foreground/60">The mean is the average rating of a statement.</p>
        </div>
        <div className="space-y-8">
          {ISO_GROUPS.map((g) => (
            <div key={g.letter} className="space-y-3">
              <h3 className={H3}>{`${g.letter}. ${g.name}`}</h3>
              <p className="max-w-[70ch] text-sm text-foreground/60">{g.description}</p>
              <ol aria-label={`${g.name} items`} className="space-y-2">
                {g.items.map((i) => (
                  <li key={i.n} value={i.n} className="flex gap-3 rounded-2xl bg-surface p-3 neo-border">
                    <span aria-hidden className={NUMBER}>{i.n}</span>
                    <span className="min-w-0 self-center">{i.text}</span>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
        <Source path={SOURCES.iso} where="Design; the questionnaire sections A to F" />
      </section>
    </main>
  );
}
