"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowRight } from "@phosphor-icons/react";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// tabIndex: a table wider than the screen scrolls sideways, and a keyboard user needs to reach it.
// SH-05: a visible cue, only while the table is wider than its box: a label, and an edge fade until the right end is reached.
export default function ScrollTable({ label, children }: { label: string; children: React.ReactNode }) {
  const box = useRef<HTMLDivElement>(null);
  const [overflows, setOverflows] = useState(false);
  const [atEnd, setAtEnd] = useState(false);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const measure = () => {
      setOverflows(el.scrollWidth > el.clientWidth + 1);
      setAtEnd(el.scrollLeft + el.clientWidth >= el.scrollWidth - 1);
    };
    measure();
    el.addEventListener("scroll", measure, { passive: true });
    window.addEventListener("resize", measure);
    return () => {
      el.removeEventListener("scroll", measure);
      window.removeEventListener("resize", measure);
    };
  }, []);

  return (
    <div className="space-y-1">
      {overflows && (
        <p aria-hidden className="flex items-center justify-end gap-1 text-xs font-bold text-foreground/60">
          <span>Scrolls sideways</span>
          <ArrowRight weight="bold" className="size-3" />
        </p>
      )}
      <div className="relative">
        <div ref={box} role="region" aria-label={label} tabIndex={0} className={`overflow-x-auto rounded-2xl neo-border ${FOCUS}`}>
          <table className="w-full min-w-[36rem] border-collapse text-sm">
            <caption className="sr-only">{label}</caption>
            {children}
          </table>
        </div>
        {overflows && !atEnd && (
          <span
            aria-hidden
            className="pointer-events-none absolute inset-y-0 right-0 w-10 rounded-r-2xl bg-gradient-to-l from-foreground/20 to-transparent"
          />
        )}
      </div>
    </div>
  );
}
