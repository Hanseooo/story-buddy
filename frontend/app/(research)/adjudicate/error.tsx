"use client";

import { useEffect } from "react";
import Link from "next/link";
import { WarningCircle, ArrowsClockwise, ArrowLeft } from "@phosphor-icons/react";
import * as Sentry from "@sentry/nextjs";

export default function AdjudicateError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") {
      Sentry.captureException(error);
    } else {
      console.error("Adjudicate error caught:", error);
    }
  }, [error]);

  return (
    <div className="w-full flex-1 min-h-[calc(100dvh-5rem)] flex items-center justify-center p-6 bg-background text-foreground">
      <div className="max-w-md w-full text-center bg-surface border border-primary/15 rounded-[24px] p-8 shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
        <div className="size-16 rounded-2xl bg-destructive/15 text-destructive flex items-center justify-center mx-auto mb-5">
          <WarningCircle className="size-10" weight="duotone" />
        </div>
        <h1 className="font-display text-2xl md:text-3xl font-extrabold text-foreground tracking-tight mb-2">
          Unable to load adjudication
        </h1>
        <p className="font-sans text-sm md:text-base text-foreground/70 mb-8 leading-relaxed">
          We encountered an issue loading conflicted pairs. You can try refreshing or return to the Research Lab.
        </p>
        <div className="flex flex-col gap-3 w-full">
          <button
            type="button"
            onClick={reset}
            className="w-full min-h-[48px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-primary text-on-primary font-bold text-sm shadow-[0_6px_18px_rgba(49,85,217,0.10)] hover:bg-primary-deep active:scale-[0.98] transition-all cursor-pointer focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <ArrowsClockwise className="size-5" weight="bold" />
            <span>Try again</span>
          </button>
          <Link
            href="/research"
            className="w-full min-h-[48px] inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-background border border-primary/20 text-foreground font-bold text-sm hover:bg-muted/40 active:scale-[0.98] transition-all focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <ArrowLeft className="size-5" weight="bold" />
            <span>Back to Research Lab</span>
          </Link>

          <form action="/auth/signout" method="post">
            <button
              type="submit"
              className="w-full min-h-[48px] inline-flex items-center justify-center px-5 py-2.5 rounded-xl border border-primary/20 text-primary font-bold text-sm hover:bg-muted/40 active:scale-[0.98] transition-all focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
            >
              Log out
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
