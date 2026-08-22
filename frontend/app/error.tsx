"use client";

import { useEffect } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { House, ArrowsClockwise, WarningCircle, Sparkle, ArrowLeft } from "@phosphor-icons/react";
import * as Sentry from "@sentry/nextjs";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log exception safely without swallowing or echoing sensitive payload
    if (process.env.NODE_ENV === "production") {
      Sentry.captureException(error);
    } else {
      console.error("ErrorBoundary caught runtime exception:", error);
    }
  }, [error]);

  return (
    <div className="min-h-[100dvh] w-full bg-background text-foreground flex flex-col justify-between overflow-x-hidden selection:bg-primary selection:text-on-primary">
      {/* Navigation Header */}
      <header className="w-full bg-primary text-on-primary shadow-sm">
        <nav
          aria-label="Error page navigation"
          className="mx-auto flex min-h-[72px] w-full max-w-7xl items-center justify-between px-5 sm:px-8 lg:px-12"
        >
          <Link
            href="/"
            className="flex min-h-[44px] items-center gap-2.5 font-display text-xl font-extrabold tracking-[-0.03em] focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 rounded-lg"
          >
            <div className="grid size-10 place-items-center rounded-[11px_11px_11px_4px] bg-surface shadow-sm overflow-hidden">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/logo.png" alt="" className="h-full w-full object-contain scale-[1.35]" />
            </div>
            <span>StoryBuddy</span>
          </Link>

          <Link
            href="/"
            className="flex min-h-[44px] items-center gap-2 text-sm font-bold text-on-primary/90 hover:text-on-primary transition-colors focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 rounded-lg px-3 py-1.5"
          >
            <ArrowLeft className="size-4" weight="bold" />
            <span>Return Home</span>
          </Link>
        </nav>
      </header>

      {/* Main Content Stage */}
      <main className="flex-1 flex items-center justify-center px-4 py-10 sm:py-16">
        <div className="w-full max-w-4xl mx-auto flex flex-col items-center text-center">
          
          {/* Error Visual Stage */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="relative w-full max-w-lg mb-8 sm:mb-10"
          >
            {/* Soft glow background */}
            <div className="absolute -inset-2 bg-warning/15 rounded-[32px] blur-xl" aria-hidden="true" />

            {/* Badge */}
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10 bg-warning text-on-warning px-4 py-1.5 rounded-full font-display font-bold text-xs tracking-wider uppercase shadow-sm flex items-center gap-1.5 border border-warning/40">
              <Sparkle className="size-3.5 fill-current" weight="fill" />
              <span>Temporary Pause</span>
            </div>

            {/* Surface Card Frame */}
            <div className="relative bg-surface rounded-3xl p-6 sm:p-8 neo-border neo-shadow">
              <div className="flex flex-col items-center justify-center bg-background/50 rounded-2xl p-8 border border-muted/80 text-center">
                <div className="size-16 rounded-2xl bg-warning/15 text-warning flex items-center justify-center mb-4">
                  <WarningCircle className="size-10" weight="duotone" />
                </div>
                <p className="font-kid font-bold text-base text-foreground/80">
                  The magic pencil paused for a moment
                </p>
                <div className="w-12 h-1 bg-warning/40 rounded-full mt-3" aria-hidden="true" />
              </div>
            </div>
          </motion.div>

          {/* Copy Section */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="space-y-4 max-w-xl mx-auto"
          >
            <h1 className="font-display text-3xl sm:text-4xl lg:text-5xl font-extrabold text-foreground tracking-tight leading-tight">
              Something took an unexpected turn
            </h1>
            
            <p className="font-kid text-lg sm:text-xl text-foreground/80 leading-relaxed max-w-[52ch] mx-auto">
              Your work is saved. You can try refreshing this page or return home to pick up your story.
            </p>
          </motion.div>

          {/* Actions */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 w-full max-w-md"
          >
            {/* Primary Retry Button */}
            <button
              type="button"
              onClick={() => reset()}
              className="w-full sm:w-auto inline-flex min-h-[48px] items-center justify-center gap-2.5 px-6 py-3 rounded-2xl bg-primary text-on-primary font-kid font-extrabold text-base shadow-sm hover:bg-primary-deep active:scale-[0.98] transition-all duration-150 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 whitespace-nowrap cursor-pointer"
            >
              <ArrowsClockwise className="size-5" weight="bold" />
              <span>Try Again</span>
            </button>

            {/* Secondary Home Button */}
            <Link
              href="/"
              className="w-full sm:w-auto inline-flex min-h-[48px] items-center justify-center gap-2.5 px-6 py-3 rounded-2xl bg-secondary text-on-secondary font-kid font-extrabold text-base shadow-sm hover:bg-[#e5ba4e] active:scale-[0.98] transition-all duration-150 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 whitespace-nowrap"
            >
              <House className="size-5" weight="bold" />
              <span>Back to My Storybook</span>
            </Link>
          </motion.div>

          <form action="/auth/signout" method="post" className="mt-4">
            <button
              type="submit"
              className="min-h-[44px] rounded-xl border border-primary/20 px-5 py-2 text-sm font-kid font-bold text-primary hover:bg-primary/5 transition-colors focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
            >
              Log out
            </button>
          </form>

        </div>
      </main>

      {/* Footer */}
      <footer className="w-full py-6 px-5 border-t border-muted/60 text-center font-kid text-xs text-foreground/60">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>&copy; {new Date().getFullYear()} StoryBuddy</span>
          <Link href="/" className="hover:text-primary transition-colors">
            StoryBuddy Home
          </Link>
        </div>
      </footer>
    </div>
  );
}
