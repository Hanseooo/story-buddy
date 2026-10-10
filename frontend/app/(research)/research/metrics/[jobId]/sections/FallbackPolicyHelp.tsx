"use client";

import { useEffect, useId, useState } from "react";

export default function FallbackPolicyHelp() {
  const [open, setOpen] = useState(false);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    function dismiss(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      setOpen(false);
    }
    document.addEventListener("keydown", dismiss, true);
    return () => document.removeEventListener("keydown", dismiss, true);
  }, [open]);

  return (
    <div
      className="relative flex items-center justify-between gap-2"
      onMouseLeave={(event) => {
        if (!event.currentTarget.contains(document.activeElement)) setOpen(false);
      }}
      onBlur={() => setOpen(false)}
    >
      <p className="text-sm font-bold">Why it was used</p>
      <button
        type="button"
        aria-label="About the fallback policy"
        aria-describedby={open ? id : undefined}
        onMouseEnter={() => setOpen(true)}
        onFocus={() => setOpen(true)}
        onClick={() => setOpen(true)}
        className="inline-flex size-11 shrink-0 items-center justify-center rounded-xl text-primary hover:bg-primary/10 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
      >
        <span aria-hidden="true" className="inline-flex size-5 items-center justify-center rounded-full border border-current text-xs font-bold">?</span>
      </button>
      {open && (
        <div id={id} role="tooltip" className="absolute right-0 top-full z-20 w-72 max-w-full rounded-xl bg-surface p-3 text-sm leading-relaxed neo-border neo-shadow-sm">
          If redraws still fail, the pipeline can keep its best available drawing.
          {" "}Drawings are compared in this order: available check results, no page-content contradictions (then fewer contradictions), character match, intact anatomy, no text, correct character colour and body features, no duplicate characters, and matching style.
          {" "}The first difference decides the winner. If everything ties, the newest drawing wins.
          {" "}A selected drawing can still have failed consistency checks. Safety is checked separately.
          {" "}This policy is not a recorded explanation for this selection.
        </div>
      )}
    </div>
  );
}
