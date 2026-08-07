"use client";

import { useEffect, useRef } from "react";
import { Job, ReviewDecision, jobState } from "@/lib/types/jobs";
import { StateBadge } from "./BookCard";

type Props = {
  job: Job | null;
  pageUrls: string[];
  onDecide: (decision: ReviewDecision) => void;
  onClose: () => void;
};

export default function BookReviewDialog({
  job,
  pageUrls,
  onDecide,
  onClose,
}: Props) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (job) el.showModal?.();
    else el.close?.();
  }, [job]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const handler = () => onClose();
    el.addEventListener("cancel", handler);
    return () => el.removeEventListener("cancel", handler);
  }, [onClose]);

  const state = job ? jobState(job) : "pending";
  const name = job?.profiles?.display_nickname ?? "";

  return (
    <dialog
      ref={ref}
      className="
        m-0 p-0 border-none bg-transparent
        w-full h-full max-w-none max-h-none
        open:flex items-center justify-center
        backdrop:bg-foreground/50 backdrop:backdrop-blur-sm
      "
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      {job && (
        <div className="bg-surface w-full max-w-3xl mx-4 sm:mx-auto rounded-2xl flex flex-col max-h-[95vh] shadow-[0_22px_60px_rgb(49_85_217/16%)] overflow-hidden">
          {/* Header */}
          <div className="px-6 py-4 border-b border-primary/10 flex items-center justify-between shrink-0">
            <div>
              <p className="font-bold text-foreground">{name}</p>
              <p className="text-xs text-foreground/50">
                {new Date(job.created_at).toLocaleDateString(undefined, {
                  weekday: "short",
                  month: "short",
                  day: "numeric",
                })}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <StateBadge state={state} />
              <button
                onClick={onClose}
                className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl hover:bg-muted transition-colors text-foreground/60 font-bold text-xl"
                aria-label="Close"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Pages */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-8 bg-background/30">
            {pageUrls.length === 0 && (
              <div className="py-12 text-center text-foreground/40 text-sm">
                Loading pages…
              </div>
            )}
            {job.pages?.map((page, i) => (
              <div
                key={page.scene_id}
                className="bg-surface rounded-2xl overflow-hidden border border-primary/10 shadow-[0_6px_18px_rgb(49_85_217/10%)]"
              >
                {pageUrls[i] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={pageUrls[i]}
                    alt={page.caption}
                    className="w-full aspect-[3/2] object-cover"
                  />
                ) : (
                  <div className="w-full aspect-[3/2] bg-muted animate-pulse" />
                )}
                <p className="font-kid text-lg leading-relaxed px-6 py-5 text-center text-foreground">
                  {page.caption}
                </p>
              </div>
            ))}
          </div>

          {/* Decision footer — fixed at bottom, thumb-reachable */}
          <div className="px-6 py-4 border-t border-primary/10 bg-surface shrink-0 flex gap-3 justify-end">
            {state !== "rejected" && state !== "pending" ? null : (
              <button
                onClick={() => onDecide("rejected")}
                className="min-h-[44px] px-6 py-2 rounded-xl border border-destructive text-destructive font-bold text-sm hover:bg-destructive/10 transition-colors"
              >
                Reject
              </button>
            )}
            {state !== "approved" ? (
              <button
                onClick={() => onDecide("approved")}
                className="min-h-[44px] px-8 py-2 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-deep transition-colors"
              >
                Approve
              </button>
            ) : (
              <button
                onClick={() => onDecide("pending")}
                className="min-h-[44px] px-6 py-2 rounded-xl border border-primary/20 font-bold text-sm hover:bg-muted transition-colors"
              >
                Move back to queue
              </button>
            )}
          </div>
        </div>
      )}
    </dialog>
  );
}
