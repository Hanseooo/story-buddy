"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { House, MagicWand, ArrowLeft, BookOpen, Compass, Sparkle } from "@phosphor-icons/react";

export default function NotFound() {
  return (
    <div className="min-h-[100dvh] w-full bg-background text-foreground flex flex-col justify-between overflow-x-hidden selection:bg-primary selection:text-on-primary">
      {/* Header */}
      <header className="w-full bg-primary text-on-primary shadow-sm">
        <nav
          aria-label="404 page navigation"
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
          
          {/* Storybook 404 Visual Stage */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            data-testid="storybook-404-visual"
            className="relative w-full max-w-lg mb-8 sm:mb-10"
          >
            {/* Soft decorative glow background */}
            <div className="absolute -inset-2 bg-primary/10 rounded-[32px] blur-xl" aria-hidden="true" />

            {/* Floating Bookmark Badge */}
            <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10 bg-secondary text-on-secondary px-4 py-1.5 rounded-full font-display font-bold text-xs tracking-wider uppercase shadow-sm flex items-center gap-1.5 border border-secondary/30">
              <Sparkle className="size-3.5 fill-current" weight="fill" />
              <span>Page 404</span>
            </div>

            {/* Open Storybook Frame */}
            <div className="relative bg-surface rounded-3xl p-6 sm:p-8 neo-border neo-shadow transition-shadow">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-center bg-background/50 rounded-2xl p-5 border border-muted/80 min-h-[200px]">
                
                {/* Left Page (Unwritten Canvas) */}
                <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-surface border border-muted/60 text-center relative overflow-hidden group">
                  <div className="absolute top-0 right-0 w-8 h-8 bg-coral/20 rounded-bl-xl border-b border-l border-coral/30" aria-hidden="true" />
                  <div className="size-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-3 group-hover:scale-105 transition-transform duration-200">
                    <BookOpen className="size-8" weight="duotone" />
                  </div>
                  <span className="font-kid font-bold text-sm text-foreground/70">
                    Unwritten Page
                  </span>
                  <div className="w-12 h-1 bg-primary/20 rounded-full mt-2" aria-hidden="true" />
                </div>

                {/* Right Page (Magic Magic Wand / Secret Path) */}
                <div className="flex flex-col items-center justify-center p-4 rounded-xl bg-surface border border-dashed border-primary/30 text-center relative">
                  <div className="size-14 rounded-2xl bg-secondary/30 text-on-secondary flex items-center justify-center mb-3">
                    <MagicWand className="size-8 text-primary" weight="duotone" />
                  </div>
                  <span className="font-kid font-bold text-sm text-foreground/70">
                    Awaiting Your Magic
                  </span>
                  <div className="w-16 h-1 bg-secondary/50 rounded-full mt-2" aria-hidden="true" />
                </div>

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
              This page hasn&apos;t been written yet
            </h1>
            
            <p className="font-kid text-lg sm:text-xl text-foreground/80 leading-relaxed max-w-[52ch] mx-auto">
              Looks like this story took a secret shortcut off the map. Your characters, illustrations, and storybooks are waiting for you right where you left them.
            </p>
          </motion.div>

          {/* Action Hierarchy CTAs */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-4 w-full max-w-md"
          >
            {/* Primary Action (Cobalt button) */}
            <Link
              href="/"
              className="w-full sm:w-auto inline-flex min-h-[48px] items-center justify-center gap-2.5 px-6 py-3 rounded-2xl bg-primary text-on-primary font-kid font-extrabold text-base shadow-sm hover:bg-primary-deep active:scale-[0.98] transition-all duration-150 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 whitespace-nowrap"
            >
              <House className="size-5" weight="bold" />
              <span>Back to My Storybook</span>
            </Link>

            {/* Secondary Action (Sun Yellow button) */}
            <Link
              href="/signup"
              className="w-full sm:w-auto inline-flex min-h-[48px] items-center justify-center gap-2.5 px-6 py-3 rounded-2xl bg-secondary text-on-secondary font-kid font-extrabold text-base shadow-sm hover:bg-[#e5ba4e] active:scale-[0.98] transition-all duration-150 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 whitespace-nowrap"
            >
              <MagicWand className="size-5" weight="bold" />
              <span>Start a New Story</span>
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

          {/* Quick Nav Recovery Strip */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="mt-12 pt-8 border-t border-muted/70 w-full max-w-lg mx-auto"
          >
            <p className="font-kid text-sm text-foreground/60 mb-3 flex items-center justify-center gap-1.5">
              <Compass className="size-4 text-primary" weight="bold" />
              <span>Looking for another page?</span>
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm font-kid font-bold text-primary">
              <Link href="/join" className="hover:underline focus-visible:outline-secondary rounded">
                Enter Class Code
              </Link>
              <span className="text-muted" aria-hidden="true">•</span>
              <Link href="/login" className="hover:underline focus-visible:outline-secondary rounded">
                Teacher Sign In
              </Link>
            </div>
          </motion.div>

        </div>
      </main>

      {/* Footer */}
      <footer className="w-full py-6 px-5 border-t border-muted/60 text-center font-kid text-xs text-foreground/60">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>&copy; {new Date().getFullYear()} StoryBuddy. All story rights belong to the young authors.</span>
          <Link href="/" className="hover:text-primary transition-colors">
            StoryBuddy Home
          </Link>
        </div>
      </footer>
    </div>
  );
}
