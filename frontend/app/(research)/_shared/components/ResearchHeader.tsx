"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignOut } from "@phosphor-icons/react";
import { RESEARCH_TABS } from "../constants";
import type { ResearchViewer } from "../viewer";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// Not sticky: the annotate and adjudicate task bars below it already stick to the top.
export default function ResearchHeader({ viewer }: { viewer: ResearchViewer | null }) {
  const pathname = usePathname() ?? "/research/metrics";
  const tabs = RESEARCH_TABS.filter((tab) => tab.visibleTo(viewer));
  const roleChip =
    viewer?.role === "researcher" ? (viewer.isAdjudicator ? "Adjudicator" : "Annotator") : null;

  return (
    <header className="border-b border-primary/10 bg-background">
      <div className="mx-auto flex max-w-7xl items-center gap-1 px-3 py-2 sm:gap-4 sm:px-6">
        <Link
          href="/research"
          aria-label="StoryBuddy research home"
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

        <nav aria-label="Research" className="flex min-w-0 flex-1 gap-0.5">
          {tabs.map((tab) => {
            const active = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
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

        {viewer ? (
          <div className="flex shrink-0 items-center gap-1 sm:gap-2">
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
            className={`inline-flex min-h-11 shrink-0 items-center whitespace-nowrap rounded-xl border border-primary/20 px-2 text-sm font-bold text-primary hover:bg-primary/5 sm:px-3 ${FOCUS}`}
          >
            Researcher sign in
          </Link>
        )}
      </div>
    </header>
  );
}
