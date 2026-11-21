"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowLeft, ArrowRight } from "@phosphor-icons/react";
import { neighbours } from "../readingOrder";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const BOX = `flex min-h-11 flex-1 flex-col gap-0.5 rounded-2xl bg-surface p-4 neo-border hover:bg-primary/5 ${FOCUS}`;

// The end of every page in the reading order (SH-04): Previous and Next name their target. Long titles wrap (SH-10).
// The first page has no Previous and the last has no Next; the hub and Runs show nothing.
export default function PageNav() {
  const { previous, next } = neighbours(usePathname() ?? "");
  if (!previous && !next) return null;

  return (
    <nav aria-label="Previous and next page" className="mt-12 flex flex-col gap-3 sm:flex-row">
      {previous ? (
        <Link href={previous.href} className={BOX}>
          <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-foreground/60">
            <ArrowLeft weight="bold" className="size-3.5" aria-hidden />
            Previous
          </span>
          <span className="font-display text-lg font-extrabold leading-snug">{previous.title}</span>
        </Link>
      ) : (
        <span className="hidden flex-1 sm:block" aria-hidden />
      )}
      {next && (
        <Link href={next.href} className={`${BOX} sm:items-end sm:text-right`}>
          <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-foreground/60">
            Next
            <ArrowRight weight="bold" className="size-3.5" aria-hidden />
          </span>
          <span className="font-display text-lg font-extrabold leading-snug">{next.title}</span>
        </Link>
      )}
    </nav>
  );
}
