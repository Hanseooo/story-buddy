"use client";

import { useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowsClockwise, WarningCircle } from "@phosphor-icons/react";
import * as Sentry from "@sentry/nextjs";

export default function ResearchPageError({ error, unstable_retry }: { error: Error & { digest?: string }; unstable_retry: () => void }) {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") Sentry.captureException(error);
    else console.error("Research page error caught:", error);
  }, [error]);

  return (
    <div role="alert" className="flex min-h-[60dvh] items-center justify-center p-6">
      <div className="w-full max-w-md rounded-[24px] border border-primary/15 bg-surface p-8 text-center shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
        <WarningCircle className="mx-auto mb-4 size-12 text-destructive" weight="duotone" aria-hidden />
        <h1 className="mb-2 font-display text-2xl font-extrabold">We couldn&apos;t show this page</h1>
        <p className="mb-6 text-sm text-foreground/70">Something went wrong while drawing it. Try again, or go back to the methodology page.</p>
        <div className="flex flex-col gap-3">
          <button
            type="button"
            onClick={unstable_retry}
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-on-primary hover:bg-primary-deep focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <ArrowsClockwise className="size-5" weight="bold" aria-hidden />
            Try again
          </button>
          <Link
            href="/research"
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-primary/20 px-5 text-sm font-bold hover:bg-muted/40 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <ArrowLeft className="size-5" weight="bold" aria-hidden />
            Back to Methodology
          </Link>
        </div>
      </div>
    </div>
  );
}
