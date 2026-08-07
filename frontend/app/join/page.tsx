"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";

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

  return (
    <main className="font-kid min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center">
        <h1 className="font-display text-3xl font-extrabold text-primary mb-2">
          Enter your class code
        </h1>
        <p className="text-foreground/70 mb-8">Ask your teacher for the six-letter code.</p>

        <form onSubmit={handleSubmit}>
          <div
            className="flex gap-2 justify-center mb-4"
            role="group"
            aria-label="Class code"
            onPaste={handlePaste}
          >
            {boxes.map((val, idx) => (
              <input
                key={idx}
                ref={(el) => { refs.current[idx] = el; }}
                type="text"
                inputMode="text"
                maxLength={1}
                value={val}
                autoFocus={idx === 0}
                aria-label={`Code character ${idx + 1}`}
                className="w-12 h-14 text-center text-2xl font-extrabold border-2 border-primary/30 rounded-xl bg-surface focus:border-primary focus:outline-none focus:ring-2 focus:ring-secondary uppercase"
                onKeyDown={(e) => handleKeyDown(idx, e)}
                onChange={(e) => handleChange(idx, e)}
              />
            ))}
          </div>

          {hint && (
            <p role="alert" className="text-sm text-amber-600 mb-4">
              That letter isn&apos;t used in class codes.
            </p>
          )}

          <button
            type="submit"
            disabled={code.length < BOX_COUNT}
            className="w-full min-h-11 rounded-xl bg-primary text-on-primary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </form>
      </div>
    </main>
  );
}
