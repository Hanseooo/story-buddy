import Link from "next/link";
import { ArrowSquareOut } from "@phosphor-icons/react/dist/ssr";
import { githubUrl } from "../docs/entries";
import { OBJECTIVES } from "./data";

export const metadata = {
  title: "StoryBuddy Objectives and Answers",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const LINK = `inline-flex min-h-11 items-center gap-1 rounded-lg font-bold text-primary hover:text-primary-deep hover:underline sm:min-h-0 ${FOCUS}`;
const LABEL = "text-xs font-bold uppercase tracking-widest text-foreground/60";

export default function ObjectivesPage() {
  return (
    <main className="space-y-10 pt-4 lg:space-y-14">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Objectives and answers</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          The study&apos;s five objectives in the manuscript&apos;s order. Each has its answer so far, the files the answer comes from, and
          the page that explains it.
        </p>
      </div>

      <ol className="space-y-5">
        {OBJECTIVES.map((o) => (
          <li key={o.n}>
            <article className="space-y-4 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6">
              <header className="space-y-1">
                <h2 className="font-display text-2xl font-extrabold tracking-tight">{`Objective ${o.n}`}</h2>
                <p className="max-w-[70ch] text-foreground/80">{o.text}</p>
              </header>

              <div className="space-y-2">
                <p className={LABEL}>Answer</p>
                <p className="max-w-[70ch] font-bold">{o.answer.lead}</p>
                {o.answer.body.map((sentence) => (
                  <p key={sentence} className="max-w-[70ch] text-foreground/80">
                    {sentence}
                  </p>
                ))}
              </div>

              {o.evidence.length > 0 && (
                <div className="space-y-1">
                  <p className={LABEL}>Evidence</p>
                  <ul className="space-y-1 text-sm">
                    {o.evidence.map((e) => (
                      <li key={e.path}>
                        <a href={githubUrl(e.path)} target="_blank" rel="noopener noreferrer" className={`${LINK} font-mono`}>
                          <span className="break-all">{e.path}</span>
                          <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
                          <span className="sr-only">{`, ${e.label} (opens on GitHub in a new tab)`}</span>
                        </a>
                        <span className="block text-foreground/60" aria-hidden>
                          {e.label}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="space-y-1">
                <p className={LABEL}>Explained on</p>
                <Link href={o.explained.href} className={LINK}>
                  {o.explained.label}
                </Link>
              </div>
            </article>
          </li>
        ))}
      </ol>
    </main>
  );
}
