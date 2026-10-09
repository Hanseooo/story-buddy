"use client";

import { useEffect } from "react";
import { ArrowsClockwise, WarningCircle } from "@phosphor-icons/react";
import * as Sentry from "@sentry/nextjs";
import BackLink from "./BackLink";

export default function RunError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") Sentry.captureException(error);
    else console.error("Run page error caught:", error);
  }, [error]);

  return (
    <div role="alert" className="flex min-h-[60dvh] items-center justify-center p-6">
      <div className="flex w-full max-w-md flex-col items-center gap-4 rounded-[24px] border border-primary/15 bg-surface p-8 text-center shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
        <WarningCircle className="size-12 text-destructive" weight="duotone" aria-hidden />
        <h1 className="font-display text-2xl font-extrabold">Couldn&apos;t load this run</h1>
        <p className="text-sm text-foreground/70">The run service did not answer. Try again in a moment.</p>
        <button
          type="button"
          onClick={reset}
          className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-on-primary hover:bg-primary-deep focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
        >
          <ArrowsClockwise className="size-5" weight="bold" aria-hidden />
          Try again
        </button>
        <BackLink />
      </div>
    </div>
  );
}
