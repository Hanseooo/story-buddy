"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { ArrowLeft, Backpack } from "@phosphor-icons/react";

// S1-3 alphabet: a-z0-9 minus ambiguous chars 0, O, 1, I, l
const EXCLUDED = new Set(["0", "o", "1", "i", "l"]);
const BOX_COUNT = 6;

export default function JoinPage() {
  const router = useRouter();
  const shouldReduceMotion = useReducedMotion();
  const [boxes, setBoxes] = useState<string[]>(Array(BOX_COUNT).fill(""));
  const [hint, setHint] = useState(false);
  const refs = useRef<Array<HTMLInputElement | null>>(Array(BOX_COUNT).fill(null));

  const handleKeyDown = (idx: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    const key = e.key.toLowerCase();
    if (e.key === "Backspace" && !boxes[idx] && idx > 0) {
      refs.current[idx - 1]?.focus();
      return;
    }
    if (e.key === "ArrowLeft" && idx > 0) {
      refs.current[idx - 1]?.focus();
      return;
    }
    if (e.key === "ArrowRight" && idx < BOX_COUNT - 1) {
      refs.current[idx + 1]?.focus();
      return;
    }
    if (key.length === 1 && EXCLUDED.has(key)) {
      e.preventDefault();
      setHint(true);
    } else if (key.length === 1) {
      setHint(false);
    }
  };

  const handleChange = (idx: number, e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value.toLowerCase();
    if (!raw) {
      const next = [...boxes];
      next[idx] = "";
      setBoxes(next);
      return;
    }

    const cleanChars: string[] = [];
    let hasExcluded = false;

    for (const char of raw) {
      if (EXCLUDED.has(char)) {
        hasExcluded = true;
      } else {
        cleanChars.push(char);
      }
    }

    if (hasExcluded) {
      setHint(true);
    } else {
      setHint(false);
    }

    if (cleanChars.length === 0) {
      e.target.value = boxes[idx];
      return;
    }

    const next = [...boxes];
    let currentIdx = idx;
    for (const c of cleanChars) {
      if (currentIdx < BOX_COUNT) {
        next[currentIdx] = c;
        currentIdx++;
      }
    }

    setBoxes(next);

    const nextFocusIdx = Math.min(currentIdx, BOX_COUNT - 1);
    refs.current[nextFocusIdx]?.focus();
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const text = e.clipboardData
      .getData("text")
      .toLowerCase()
      .replace(/[01oil\s]/g, "");
    const chars = text.split("").slice(0, BOX_COUNT);
    const next = Array(BOX_COUNT).fill("") as string[];
    chars.forEach((c, i) => { next[i] = c; });
    setBoxes(next);
    setHint(false);
    refs.current[Math.min(chars.length, BOX_COUNT - 1)]?.focus();
  };

  const code = boxes.join("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length === BOX_COUNT) router.push("/join/" + code);
  };

  return (
    <main className="font-kid min-h-[100dvh] bg-background text-foreground flex items-center justify-center p-4 sm:p-6 overflow-hidden relative">
      {/* Back Button */}
      <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-50">
        <Link 
          href="/" 
          className="inline-flex min-h-11 items-center gap-2 text-foreground/70 hover:text-primary font-bold text-sm transition-colors group focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary rounded-xl px-3 py-1.5 -ml-2"
        >
          <ArrowLeft size={18} weight="bold" className="transition-transform group-hover:-translate-x-1" />
          Home
        </Link>
      </div>

      {/* Tactile Playroom Background Shapes (Crisp Geometric Cutouts - No Blur Slop) */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <div className="absolute -top-16 -right-16 size-64 rounded-full bg-secondary/20" />
        <div className="absolute -bottom-20 -left-20 size-80 rounded-[48px] bg-primary/5 rotate-12" />
        <div className="absolute top-1/4 left-10 size-12 rounded-full bg-coral/15" />
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: shouldReduceMotion ? 1 : 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-md bg-surface border border-primary/15 rounded-[24px] p-6 sm:p-10 shadow-[0_10px_28px_rgba(49,85,217,0.08)] relative z-10"
      >
        <div className="text-center mb-8">
          <div className="size-16 mx-auto bg-primary/10 text-primary rounded-2xl flex items-center justify-center mb-6 shadow-sm">
            <Backpack size={32} weight="duotone" />
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-primary mb-2 tracking-tight">
            Class code
          </h1>
          <p className="text-foreground/75 text-base">
            Ask your teacher for the six-letter code to join your classroom.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div
            className="flex gap-2 sm:gap-3 justify-center mb-6"
            role="group"
            aria-label="Class code"
            onPaste={handlePaste}
          >
            {boxes.map((val, idx) => (
              <motion.input
                key={idx}
                ref={(el) => { refs.current[idx] = el; }}
                type="text"
                inputMode="text"
                autoCapitalize="off"
                autoCorrect="off"
                spellCheck={false}
                autoComplete="one-time-code"
                maxLength={1}
                value={val}
                autoFocus={idx === 0}
                aria-label={`Code character ${idx + 1}`}
                whileFocus={{ scale: 1.04, boxShadow: "0 10px 28px rgba(49,85,217,0.12)" }}
                className="w-12 h-14 sm:w-14 sm:h-16 text-center text-2xl sm:text-3xl font-extrabold text-primary border-2 border-primary/20 rounded-[16px] bg-background focus:border-primary focus:outline-none transition-all uppercase caret-primary leading-none p-0 flex items-center justify-center"
                onKeyDown={(e) => handleKeyDown(idx, e)}
                onChange={(e) => handleChange(idx, e)}
              />
            ))}
          </div>

          <div className="h-6 mb-6 text-center">
            <AnimatePresence>
              {hint && (
                <motion.p 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0, x: shouldReduceMotion ? 0 : [-5, 5, -5, 5, 0] }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                  role="alert" 
                  className="text-sm font-bold text-warning"
                >
                  That letter isn&apos;t used in class codes.
                </motion.p>
              )}
            </AnimatePresence>
          </div>

          <motion.button
            type="submit"
            disabled={code.length < BOX_COUNT}
            whileTap={{ y: code.length === BOX_COUNT ? 2 : 0, boxShadow: code.length === BOX_COUNT ? "0 0px 0 var(--color-primary-deep)" : undefined }}
            className="w-full min-h-[52px] rounded-xl bg-primary text-on-primary text-lg font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed disabled:transform-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px]"
          >
            Join Class
          </motion.button>
        </form>

        <div className="mt-8 text-center text-sm font-bold text-foreground/70">
          Teacher or parent?{" "}
          <Link href="/welcome?action=login" className="text-primary hover:text-primary-deep underline decoration-primary/30 underline-offset-4 transition-colors">
            Log in here
          </Link>
        </div>
      </motion.div>
    </main>
  );
}
