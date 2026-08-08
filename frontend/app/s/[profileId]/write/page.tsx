"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { resetFailChain } from "@/components/FailureScreen";
import { motion } from "motion/react";

const MIN_STORY_WORDS = 5;
const MAX_STORY_WORDS = 800;

const PREFILL_KEY = "sb.prefill";
const CHAIN_KEY = "sb.failChain";

function countWords(text: string): number {
  const trimmed = text.trim();
  return trimmed === "" ? 0 : trimmed.split(/\s+/).length;
}

export default function WriteStoryPage() {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [postError, setPostError] = useState(false);
  const [chainCount, setChainCount] = useState(0);
  const router = useRouter();

  useEffect(() => {
    let prefill: string | null = null;
    try {
      prefill = sessionStorage.getItem(PREFILL_KEY);
      if (prefill !== null) {
        sessionStorage.removeItem(PREFILL_KEY);
      }
    } catch { /* storage unavailable */ }

    if (prefill !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setText(prefill);
      try {
        setChainCount(Number(sessionStorage.getItem(CHAIN_KEY) ?? 0));
      } catch { /* unavailable */ }
    } else {
      resetFailChain();
    }
  }, []);

  const wordCount = countWords(text);
  const overCap = wordCount > MAX_STORY_WORDS;
  const progress = Math.min((wordCount / MIN_STORY_WORDS) * 100, 100);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (wordCount < MIN_STORY_WORDS) return;

    setSubmitting(true);
    setPostError(false);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        setPostError(true);
        return;
      }
      const data = await res.json();
      router.push(`/process/${data.job_id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="h-[calc(100vh-76px)] sm:h-[calc(100vh-85px)] min-h-[500px] flex flex-col p-4 sm:p-8 lg:p-12 max-w-6xl mx-auto w-full relative">
      
      {/* The Magic Canvas Textarea */}
      <motion.textarea
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Once upon a time..."
        aria-label="story text"
        className="flex-1 w-full bg-transparent resize-none text-3xl sm:text-4xl lg:text-5xl leading-tight sm:leading-tight lg:leading-tight font-extrabold text-foreground placeholder-foreground/20 focus:outline-none caret-primary"
        autoFocus
      />

      {/* Floating Action Bar */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
        className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-4 bg-surface p-4 rounded-3xl border border-primary/10 shadow-[0_22px_60px_rgba(49,85,217,0.12)] shrink-0"
      >
        <div className="flex items-center gap-4 w-full sm:w-auto">
          {/* Word Count Indicator */}
          <div className="flex-1 sm:flex-none flex items-center gap-3 bg-background px-4 py-3 rounded-2xl border border-primary/10">
            <div className="relative w-10 h-10 flex items-center justify-center">
              <svg className="absolute inset-0 w-full h-full -rotate-90" viewBox="0 0 36 36">
                <circle cx="18" cy="18" r="16" fill="none" className="stroke-muted" strokeWidth="4" />
                <circle 
                  cx="18" 
                  cy="18" 
                  r="16" 
                  fill="none" 
                  className="stroke-secondary transition-all duration-300 ease-out" 
                  strokeWidth="4" 
                  strokeDasharray="100" 
                  strokeDashoffset={100 - progress} 
                  strokeLinecap="round" 
                />
              </svg>
              <span className="text-sm font-bold text-primary" aria-live="polite">{wordCount}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-extrabold text-foreground leading-none mb-1">
                {wordCount >= MIN_STORY_WORDS ? "Ready!" : "Keep going!"}
              </span>
              <span className="text-xs font-bold text-foreground/60 leading-none">
                {overCap ? <span className="text-destructive">Too long!</span> : `${MIN_STORY_WORDS} words min`}
              </span>
            </div>
          </div>

          {chainCount >= 3 && (
            <button
              type="button"
              className="text-sm font-extrabold text-primary hover:text-primary-deep hover:underline px-2 transition-colors"
              onClick={() => setText("")}
            >
              Start over
            </button>
          )}
        </div>

        <div className="w-full sm:w-auto flex flex-col sm:items-end">
          <motion.button 
            type="submit" 
            disabled={submitting || wordCount < MIN_STORY_WORDS || overCap}
            whileTap={{ y: (submitting || wordCount < MIN_STORY_WORDS || overCap) ? 0 : 4, boxShadow: (submitting || wordCount < MIN_STORY_WORDS || overCap) ? "" : "0 0px 0 var(--color-primary-deep)" }}
            className="w-full sm:w-auto min-h-[64px] px-8 rounded-2xl bg-primary text-on-primary text-xl font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-colors disabled:opacity-50 disabled:bg-muted disabled:text-foreground/40 disabled:shadow-none disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px] focus-visible:ring-offset-surface"
          >
            {submitting ? "Making magic..." : "Make my book"}
          </motion.button>
          
          {postError && (
            <p role="alert" className="text-destructive font-bold text-sm mt-2 text-center sm:text-right">
              Something went wrong. Try again!
            </p>
          )}
        </div>
      </motion.div>
    </form>
  );
}
