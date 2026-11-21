import Link from "next/link";
import { ArrowLeft, ArrowRight } from "@phosphor-icons/react/dist/ssr";
import ResearchHeader from "../_shared/components/ResearchHeader";
import { HUB_GROUPS, RESEARCH_PAGES, READING_ORDER } from "../_shared/readingOrder";
import { CORPUS } from "./(reference)/methodology/data";
import { FIGURES, NODE_COUNTS } from "./(reference)/pipeline/data";
import { JUDGES } from "./(reference)/results/data";

export const metadata = {
  title: "StoryBuddy Research",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// Each number comes from the data file of the page it links to, so it changes when that page does.
const [untrained, trained] = JUDGES;
const FACTS = [
  { value: String(NODE_COUNTS.total), label: "nodes in the story pipeline", href: "/research/pipeline" },
  { value: String(CORPUS.find((c) => c.label === "books")!.count), label: "picture books in the study", href: "/research/methodology" },
  {
    value: `${trained.f1} vs ${untrained.f1}`,
    label: "F1 of the fine-tuned judge vs its untrained base",
    href: "/research/results",
  },
];

// The research hub (US-01). Static on purpose (D-26, ADR-065): no session and no profile read, so it renders the same
// logged in and out and works with Supabase down. The page list is readingOrder.ts, the same one Previous/Next use.
export default function ResearchHubPage() {
  const first = READING_ORDER[0];
  return (
    <div className="min-h-[100dvh] bg-background text-foreground">
      <ResearchHeader viewer={null} showAccount={false} />
      <main className="mx-auto max-w-5xl space-y-10 p-4 font-sans sm:p-6 lg:space-y-14 lg:p-10">
        {/* The way out of the research site (old hub: "Back to Landing"). "/" sends a signed-in user to their own home. */}
        <Link
          href="/"
          className={`inline-flex min-h-11 w-fit items-center gap-2 rounded-xl px-2 text-sm font-bold text-foreground/70 hover:text-foreground ${FOCUS}`}
        >
          <ArrowLeft weight="bold" className="size-4" aria-hidden />
          Back to StoryBuddy
        </Link>

        <div className="grid items-center gap-8 md:grid-cols-[1fr_1.1fr]">
          <div className="flex flex-col gap-4">
            <p className="text-xs font-bold uppercase tracking-widest text-primary">Capstone research</p>
            <h1 className="font-display text-4xl font-extrabold leading-[1.05] tracking-tight md:text-5xl">
              StoryBuddy research
            </h1>
            <p className="max-w-[55ch] text-base leading-relaxed text-foreground/75 md:text-lg">
              Every research page, in the order of the paper. Each page names the paper sections it feeds and ends with
              links to the previous and next page.
            </p>
            <Link
              href={first.href}
              className={`mt-2 inline-flex min-h-12 w-fit items-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-on-primary hover:bg-primary-deep ${FOCUS}`}
            >
              Start reading: {first.title}
              <ArrowRight weight="bold" className="size-4" aria-hidden />
            </Link>
          </div>
          <Link
            href={first.href}
            aria-label={`${FIGURES.ipo.alt} Opens ${first.title}.`}
            className={`block overflow-hidden rounded-3xl bg-surface p-3 neo-border neo-shadow-sm hover:bg-primary/5 ${FOCUS}`}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={FIGURES.ipo.png} alt="" width={2528} height={1860} className="h-auto w-full rounded-2xl" />
          </Link>
        </div>

        <ul aria-label="At a glance" className="grid gap-3 sm:grid-cols-3">
          {FACTS.map((fact) => (
            <li key={fact.href} className="relative rounded-3xl bg-surface p-5 neo-border neo-shadow-sm hover:bg-primary/5 focus-within:outline-secondary focus-within:outline-3 focus-within:outline-offset-3">
              <p className="font-display text-3xl font-extrabold tracking-tight text-primary">{fact.value}</p>
              <Link
                href={fact.href}
                className="mt-1 block text-sm font-bold text-foreground/80 after:absolute after:inset-0 after:rounded-3xl focus-visible:outline-none"
              >
                {fact.label}
              </Link>
            </li>
          ))}
        </ul>

        {HUB_GROUPS.map((group) => (
          <section key={group} aria-labelledby={`group-${group}`} className="space-y-4">
            <h2 id={`group-${group}`} className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">
              {group}
            </h2>
            <ol className="grid gap-3 md:grid-cols-2">
              {RESEARCH_PAGES.filter((page) => page.group === group).map((page) => {
                const step = READING_ORDER.indexOf(page) + 1;
                return (
                  <li
                    key={page.href}
                    className="relative flex gap-4 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm focus-within:outline-secondary focus-within:outline-3 focus-within:outline-offset-3 hover:bg-primary/5"
                  >
                    <span
                      aria-hidden
                      className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 font-display text-sm font-extrabold text-primary"
                    >
                      {step > 0 ? String(step).padStart(2, "0") : "·"}
                    </span>
                    <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                      <Link
                        href={page.href}
                        className="font-display text-xl font-extrabold leading-snug after:absolute after:inset-0 after:rounded-3xl focus-visible:outline-none"
                      >
                        {page.title}
                      </Link>
                      <p className="max-w-[60ch] text-sm text-foreground/80">{page.line}</p>
                      {page.paper.length > 0 && (
                        <p className="text-xs font-bold uppercase tracking-wide text-foreground/60">
                          {`Paper: ${page.paper.join(", ")}`}
                        </p>
                      )}
                    </div>
                    <ArrowRight weight="bold" className="mt-1 size-5 shrink-0 text-primary" aria-hidden />
                  </li>
                );
              })}
            </ol>
          </section>
        ))}
      </main>
    </div>
  );
}
