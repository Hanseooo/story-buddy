"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";

// S1-3 alphabet: a-z0-9 minus ambiguous chars 0, O, 1, I, l
const EXCLUDED = new Set(["0", "o", "1", "i", "l"]);
const BOX_COUNT = 6;

export default function JoinPage() {
  const router = useRouter();
  const [boxes, setBoxes] = useState<string[]>(Array(BOX_COUNT).fill(""));
  const [hint, setHint] = useState(false);
  const refs = useRef<Array<HTMLInputElement | null>>(Array(BOX_COUNT).fill(null));

  const handleKeyDown = (idx: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    const key = e.key.toLowerCase();
    if (e.key === "Backspace" && !boxes[idx] && idx > 0) {
      refs.current[idx - 1]?.focus();
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
    const char = raw[raw.length - 1] ?? "";
    if (!char) {
      const next = [...boxes];
      next[idx] = "";
      setBoxes(next);
      return;
    }
    if (EXCLUDED.has(char)) {
      setHint(true);
      e.target.value = boxes[idx];
      return;
    }
    const next = [...boxes];
    next[idx] = char;
    setBoxes(next);
    setHint(false);
    if (idx < BOX_COUNT - 1) refs.current[idx + 1]?.focus();
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

  // Decorative background shapes animation
  const floatingAnimation = {
    animate: {
      y: [0, -15, 0],
      rotate: [0, 5, -5, 0],
      transition: { duration: 6, repeat: Infinity, ease: "easeInOut" }
    }
  };

  return (
    <main className="font-kid min-h-[100dvh] bg-background text-foreground flex items-center justify-center p-4 sm:p-6 overflow-hidden relative">
      {/* Back Button */}
      <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-50">
        <Link href="/" className="inline-flex items-center gap-2 text-foreground/50 hover:text-primary font-bold text-base transition-colors group focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary rounded-lg px-2 py-1 -ml-2">
          <svg className="w-5 h-5 transition-transform group-hover:-translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3"><path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          Back
        </Link>
      </div>

      {/* Playroom Desk Background Decor */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <motion.div {...floatingAnimation} className="absolute top-20 left-10 lg:left-32 w-16 h-16 rounded-full bg-secondary/30 blur-sm" />
        <motion.div {...floatingAnimation} transition={{ duration: 7, delay: 1, repeat: Infinity, ease: "easeInOut" }} className="absolute bottom-32 right-10 lg:right-32 w-24 h-24 rounded-2xl bg-primary/10 rotate-12 blur-sm" />
        <motion.div {...floatingAnimation} transition={{ duration: 5, delay: 2, repeat: Infinity, ease: "easeInOut" }} className="absolute top-1/3 right-1/4 w-12 h-12 rounded-full bg-coral/20 blur-sm" />
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="w-full max-w-md bg-surface border border-primary/10 rounded-[24px] p-6 sm:p-10 shadow-[0_22px_60px_rgba(49,85,217,0.16)] relative z-10"
      >
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto bg-primary/10 text-primary rounded-full flex items-center justify-center mb-6">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
            </svg>
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-primary mb-3">
            Class code
          </h1>
          <p className="text-foreground/70 text-lg">
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
                maxLength={1}
                value={val}
                autoFocus={idx === 0}
                aria-label={`Code character ${idx + 1}`}
                whileFocus={{ y: -4, boxShadow: "0 10px 28px rgba(49,85,217,0.12)" }}
                className="w-12 h-14 sm:w-14 sm:h-16 text-center text-2xl sm:text-3xl font-extrabold text-primary border-2 border-primary/20 rounded-[16px] bg-background focus:border-primary focus:outline-none transition-colors uppercase caret-primary"
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
                  animate={{ opacity: 1, y: 0, x: [-5, 5, -5, 5, 0] }}
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
            className="w-full min-h-[56px] rounded-xl bg-primary text-on-primary text-lg font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-colors disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px]"
          >
            Join Class
          </motion.button>
        </form>
      </motion.div>
    </main>
  );
}
