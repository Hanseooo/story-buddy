"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignOut } from "@phosphor-icons/react";
import { RESEARCH_TABS } from "../constants";
import type { ResearchViewer } from "../viewer";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// Sticky and as wide as the content column on the static pages (showAccount off); the annotate and adjudicate
// pages keep the wide header, and their task bars already stick to the top.
// The logo leaves the research site for StoryBuddy's home; the middleware sends a signed-in user on to their own home.
// The row wraps: on a phone the tabs fill the first line and the account block drops to a second.
// showAccount is off on the static pages (ADR-065): they read no session, so they cannot say who is signed in.
export default function ResearchHeader({
  viewer,
  showAccount = true,
}: {
  viewer: ResearchViewer | null;
  showAccount?: boolean;
}) {
  const pathname = usePathname() ?? "/research/metrics";
  const tabs = RESEARCH_TABS.filter((tab) => tab.visibleTo(viewer));
  const roleChip =
    viewer?.role === "researcher" ? (viewer.isAdjudicator ? "Adjudicator" : "Annotator") : null;

  return (
    <header className={`border-b border-primary/10 bg-background ${showAccount ? "" : "sticky top-0 z-40"}`}>
      <div
        className={`mx-auto flex flex-wrap items-center gap-1 py-2 sm:gap-4 ${
          showAccount ? "max-w-7xl px-3 sm:px-6" : "max-w-5xl px-4 sm:px-6 lg:px-10"
        }`}
      >
        <Link
          href="/"
          aria-label="StoryBuddy home"
          className={`flex shrink-0 items-center gap-2 rounded-lg ${FOCUS}`}
        >
          <span className="grid size-11 place-items-center overflow-hidden rounded-[9px_9px_9px_3px] bg-surface shadow-sm">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="" className="h-full w-full scale-[1.35] object-contain" />
          </span>
          <span className="hidden font-display text-lg font-extrabold tracking-tight text-primary lg:block">
            StoryBuddy
          </span>
        </Link>

        <nav aria-label="Research" className="flex min-w-0 flex-1 flex-wrap gap-0.5">
          {tabs.map((tab) => {
            const active = pathname === tab.href || (!tab.exact && pathname.startsWith(`${tab.href}/`));
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`inline-flex min-h-11 shrink-0 items-center rounded-xl px-2 text-sm font-bold transition-colors sm:px-3 ${FOCUS} ${
                  active ? "bg-primary text-on-primary" : "text-foreground/70 hover:bg-muted/50"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>

        {!showAccount ? null : viewer ? (
          <div className="ml-auto flex shrink-0 items-center gap-1 sm:gap-2">
            {viewer.displayName && (
              <span className="hidden max-w-[16ch] truncate text-sm font-medium text-foreground/70 md:block">
                {viewer.displayName}
              </span>
            )}
            {roleChip && (
              <span className="whitespace-nowrap rounded-full bg-admin/10 px-2 py-1 text-xs font-bold text-admin sm:px-2.5">
                {roleChip}
              </span>
            )}
            <form action="/auth/signout" method="post">
              <button
                type="submit"
                aria-label="Log out"
                className={`inline-flex min-h-11 min-w-11 items-center justify-center gap-1.5 rounded-xl px-2 text-sm font-bold text-foreground/70 hover:bg-muted/50 ${FOCUS}`}
              >
                <SignOut weight="bold" className="size-4" aria-hidden />
                <span className="hidden sm:inline">Log out</span>
              </button>
            </form>
          </div>
        ) : (
          <Link
            href={`/login?next=${pathname}`}
            className={`ml-auto inline-flex min-h-11 shrink-0 items-center whitespace-nowrap rounded-xl border border-primary/20 px-2 text-sm font-bold text-primary hover:bg-primary/5 sm:px-3 ${FOCUS}`}
          >
            Researcher sign in
          </Link>
        )}
      </div>
    </header>
  );
}
