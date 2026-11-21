import Link from "next/link";
import { ArrowLeft, ArrowRight } from "@phosphor-icons/react/dist/ssr";
import ResearchHeader from "../_shared/components/ResearchHeader";
import { HUB_GROUPS, RESEARCH_PAGES, READING_ORDER } from "../_shared/readingOrder";

export const metadata = {
  title: "StoryBuddy Research",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// The research hub (US-01). Static on purpose (D-26, ADR-065): no session and no profile read, so it renders the same
// logged in and out and works with Supabase down. The page list is readingOrder.ts, the same one Previous/Next use.
export default function ResearchHubPage() {
  const first = READING_ORDER[0];
  return (
    <div className="min-h-[100dvh] bg-background text-foreground">
      <ResearchHeader viewer={null} showAccount={false} />
      <main className="mx-auto max-w-5xl space-y-10 p-4 font-sans sm:p-6 lg:space-y-12 lg:p-10">
        <div className="flex flex-col gap-3">
          {/* The way out of the research site (old hub: "Back to Landing"). "/" sends a signed-in user to their own home. */}
          <Link
            href="/"
            className={`inline-flex min-h-11 w-fit items-center gap-2 rounded-xl px-2 text-sm font-bold text-foreground/70 hover:text-foreground ${FOCUS}`}
          >
            <ArrowLeft weight="bold" className="size-4" aria-hidden />
            Back to StoryBuddy
          </Link>
          <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">StoryBuddy research</h1>
          <p className="max-w-[65ch] text-base text-foreground/70">
            Every research page, in the order of the paper. Each page names the paper sections it feeds and ends with links
            to the previous and next page.
          </p>
          <Link
            href={first.href}
            className={`inline-flex min-h-11 w-fit items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-on-primary hover:bg-primary-deep ${FOCUS}`}
          >
            Start reading: {first.title}
            <ArrowRight weight="bold" className="size-4" aria-hidden />
          </Link>
        </div>

        {HUB_GROUPS.map((group) => (
          <section key={group} aria-labelledby={`group-${group}`} className="space-y-4">
            <h2 id={`group-${group}`} className="font-display text-2xl font-extrabold tracking-tight md:text-3xl">
              {group}
            </h2>
            <ol className="grid gap-3 md:grid-cols-2">
              {RESEARCH_PAGES.filter((page) => page.group === group).map((page) => (
                <li
                  key={page.href}
                  className="relative flex flex-col gap-1.5 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm focus-within:outline-secondary focus-within:outline-3 focus-within:outline-offset-3 hover:bg-primary/5"
                >
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
                </li>
              ))}
            </ol>
          </section>
        ))}
      </main>
    </div>
  );
}
