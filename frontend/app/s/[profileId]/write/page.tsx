"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { resetFailChain } from "@/components/FailureScreen";
import { supabase } from "@/lib/supabaseClient";
import { motion } from "framer-motion";

const MIN_STORY_WORDS = 5;
const MAX_STORY_WORDS = 300;

const PREFILL_KEY = "sb.prefill";
const CHAIN_KEY = "sb.failChain";

// ADR-022's three presets. Keys mirror backend/app/config.py STYLE_PRESETS and the CHECK
// constraint in supabase/migrations/0002_jobs_style_preset_id.sql — `cel` is the default.
const STYLE_PRESETS = [
  { id: "cel", label: "Cartoon" },
  { id: "comic", label: "Comic" },
  { id: "gouache", label: "Painted" },
] as const;

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
  const { profileId } = useParams() as { profileId: string };

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

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (wordCount < MIN_STORY_WORDS) return;

    // ponytail: the radios are uncontrolled — FormData reads the choice, no useState needed.
    const stylePresetId = new FormData(e.currentTarget).get("style_preset_id");

    setSubmitting(true);
    setPostError(false);
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ text, style_preset_id: stylePresetId }),
      });
      if (!res.ok) {
        setPostError(true);
        return;
      }
      const data = await res.json();
      router.push(`/s/${profileId}/process/${data.job_id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="min-h-[calc(100dvh-76px)] sm:min-h-[calc(100dvh-85px)] flex flex-col py-4 sm:py-6 lg:py-8 px-4 sm:px-8 max-w-5xl mx-auto w-full relative">
      
      {/* The Magic Canvas Textarea */}
      <motion.textarea
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Once upon a time..."
        aria-label="story text"
        className="flex-1 w-full bg-transparent resize-none font-kid font-bold text-2xl sm:text-3xl lg:text-4xl leading-relaxed text-foreground placeholder-foreground/35 focus:outline-none caret-primary min-h-[200px] sm:min-h-[240px]"
        autoFocus
      />

      {/* Style Picker — ADR-022, three sample cards (PRD §8 step 4) */}
      <motion.fieldset
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.05, ease: "easeOut" }}
        className="mt-3 shrink-0 max-w-2xl"
      >
        <legend className="text-xs font-display font-extrabold tracking-wider uppercase text-foreground/60 mb-2">Pick a look</legend>
        <div className="flex gap-3">
          {STYLE_PRESETS.map(({ id, label }) => (
            <label key={id} className="flex-1 cursor-pointer">
              <input
                type="radio"
                name="style_preset_id"
                value={id}
                defaultChecked={id === "cel"}
                className="sr-only peer"
              />
              <div className="relative rounded-2xl overflow-hidden bg-surface border border-primary/20 transition-all hover:-translate-y-0.5 hover:shadow-sm peer-checked:border-primary peer-checked:ring-2 peer-checked:ring-primary peer-checked:shadow-sm peer-focus-visible:ring-[3px] peer-focus-visible:ring-secondary peer-focus-visible:ring-offset-[3px] peer-focus-visible:ring-offset-background">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`/style-presets/${id}.png`}
                  alt=""
                  className="w-full aspect-[4/3] object-cover"
                />
                <span className="block text-center text-xs sm:text-sm font-extrabold text-foreground py-1.5 sm:py-2">
                  {label}
                </span>
              </div>
            </label>
          ))}
        </div>
      </motion.fieldset>

      {/* Floating Action Bar */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1, ease: "easeOut" }}
        className="mt-3 flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4 bg-surface p-3 sm:p-4 rounded-3xl border border-primary/10 shadow-[0_22px_60px_rgba(49,85,217,0.16)] shrink-0"
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
            whileHover={{ y: (submitting || wordCount < MIN_STORY_WORDS || overCap) ? 0 : -2, boxShadow: (submitting || wordCount < MIN_STORY_WORDS || overCap) ? "" : "0 6px 0 var(--color-primary-deep)" }}
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
