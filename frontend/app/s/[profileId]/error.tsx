"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { WarningCircle, ArrowsClockwise, Books } from "@phosphor-icons/react";
import * as Sentry from "@sentry/nextjs";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const params = useParams();
  const profileId = (params as { profileId?: string })?.profileId;
  const bookshelfHref = profileId ? `/s/${profileId}` : "/";

  useEffect(() => {
    if (process.env.NODE_ENV === "production") {
      Sentry.captureException(error);
    } else {
      console.error("Student section error caught:", error);
    }
  }, [error]);

  return (
    <div className="w-full flex-1 min-h-[calc(100dvh-5rem)] bg-background text-foreground flex flex-col items-center justify-center p-6 text-center">
      <div className="max-w-md w-full flex flex-col items-center bg-surface border border-primary/15 rounded-[24px] p-8 shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
        {/* Visual Badge */}
        <div className="size-16 rounded-2xl bg-warning/15 text-warning flex items-center justify-center mb-5">
          <WarningCircle className="size-10" weight="duotone" />
        </div>

        {/* Copy */}
        <h1 className="font-display text-2xl md:text-3xl font-extrabold text-foreground tracking-tight mb-2">
          The magic pencil took a break
        </h1>
        <p className="font-kid text-base md:text-lg text-foreground/75 leading-relaxed mb-8 max-w-[36ch]">
          Don&apos;t worry, your stories are safe! You can try this again or head back to your bookshelf.
        </p>

        {/* Actions */}
        <div className="flex flex-col gap-3 w-full">
          <button
            type="button"
            onClick={reset}
            className="w-full min-h-[48px] inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-primary text-on-primary font-kid font-bold text-base shadow-[0_6px_18px_rgba(49,85,217,0.10)] hover:bg-primary-deep active:scale-[0.98] transition-all cursor-pointer focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <ArrowsClockwise className="size-5" weight="bold" />
            <span>Try again</span>
          </button>

          <Link
            href={bookshelfHref}
            className="w-full min-h-[48px] inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-background border border-primary/20 text-foreground font-kid font-bold text-base hover:bg-muted/40 active:scale-[0.98] transition-all focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <Books className="size-5" weight="bold" />
            <span>Back to Bookshelf</span>
          </Link>

          <form action="/auth/signout" method="post">
            <button
              type="submit"
              className="w-full min-h-[48px] inline-flex items-center justify-center px-6 py-3 rounded-xl border border-primary/20 text-primary font-kid font-bold text-base hover:bg-muted/40 active:scale-[0.98] transition-all focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
            >
              Log out
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
