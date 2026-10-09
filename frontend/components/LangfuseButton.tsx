"use client";

import { useState } from "react";
import { ArrowSquareOut } from "@phosphor-icons/react";
import ConfirmDialog from "@/components/ConfirmDialog";

// #103. A trace holds the story before redaction, so the link is off unless the deploy opts in,
// and it asks first. Read inside the component: Next inlines NEXT_PUBLIC_ values at build either way.
export default function LangfuseButton({
  url,
  label = "Open Langfuse trace",
}: {
  url: string | null | undefined;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  if (process.env.NEXT_PUBLIC_SHOW_LANGFUSE_LINKS !== "true" || !url) return null;

  return (
    <>
      <button
        type="button"
        aria-label={label}
        onClick={() => setOpen(true)}
        className="relative z-10 inline-flex min-h-11 items-center gap-1.5 rounded-xl px-3 text-sm font-bold text-primary hover:bg-primary/10 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
      >
        Langfuse
        <ArrowSquareOut weight="bold" className="size-4" aria-hidden />
      </button>
      <ConfirmDialog
        open={open}
        title="Open the full Langfuse trace?"
        description="This trace is the full raw record of the run, including the story text before redaction. Open it only when you need that detail."
        confirmLabel="Open in new tab"
        confirmClass="bg-primary text-on-primary"
        onCancel={() => setOpen(false)}
        onConfirm={() => {
          window.open(url, "_blank", "noopener,noreferrer");
          setOpen(false);
        }}
      />
    </>
  );
}
