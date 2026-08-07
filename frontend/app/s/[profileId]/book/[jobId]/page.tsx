"use client";

/* eslint-disable @next/next/no-img-element */

import { use, useEffect, useState, useCallback } from "react";
import { useJob } from "@/lib/useJob";
import FailureScreen, { resetFailChain } from "@/components/FailureScreen";
import { supabase } from "@/lib/supabaseClient";

const BUCKET = "storybook-images";
const SWEPT_STATUS = "__swept__"; // placeholder — replace when data-deletion names it

type SignedPage = { scene_id: string; caption: string; signedUrl: string };

export default function BookPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const { bucket, row } = useJob(jobId);
  const [pageIndex, setPageIndex] = useState(0);
  const [signedPages, setSignedPages] = useState<SignedPage[] | null>(null);
  const [signFailed, setSignFailed] = useState(false);

  const signPages = useCallback(async (attempt: number) => {
    if (!row?.pages.length) return;
    const pagesList = row.pages;
    const paths = pagesList.map(p => p.image_path);
    async function doSign(att: number): Promise<void> {
      const { data, error } = await supabase.storage.from(BUCKET).createSignedUrls(paths, 3600);
      const anyBad = !data || error || data.some(s => s.error || !s.signedUrl);
      if (anyBad) {
        if (att < 2) {
          console.log("sb:action", { action: "re-sign" });
          await doSign(att + 1);
          return;
        }
        setSignFailed(true);
        return;
      }
      const pages: SignedPage[] = pagesList.map((p, i) => ({
        scene_id: p.scene_id,
        caption: p.caption,
        signedUrl: data![i].signedUrl as string,
      }));
      setSignedPages(pages);
      resetFailChain(); // actual book is on screen — chain is over
    }
    await doSign(attempt);
  }, [row?.pages]);

  useEffect(() => {
    if (bucket !== "terminal-success") return;
    signPages(1);
  }, [bucket, signPages]);

  // Arrow key navigation
  useEffect(() => {
    if (!signedPages) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        setPageIndex(i => Math.min(i + 1, signedPages!.length - 1));
      }
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        setPageIndex(i => Math.max(i - 1, 0));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [signedPages]);

  // ── Bucket routing ──────────────────────────────────────────────────────────

  if (bucket === "not-found") {
    return <FailureScreen kind="not-found" />;
  }

  if (bucket === "terminal-failure") {
    // Signing failure while book was complete: machine screen, counter NOT bumped
    if (signFailed) {
      return <FailureScreen kind="retry" inputText={row?.input_text} countable={false} />;
    }
    const kind =
      row?.failure_reason === "child_text"
        ? "revise"
        : row?.status === SWEPT_STATUS
        ? "asleep"
        : "retry";
    return <FailureScreen kind={kind} inputText={row?.input_text} />;
  }

  if (bucket === "in-flight" || bucket === "paused") {
    return (
      <div className="flex flex-col items-center gap-4 p-6">
        <p className="font-kid text-lg">Loading your book…</p>
      </div>
    );
  }

  // terminal-success — wait for signing
  if (signFailed) {
    return <FailureScreen kind="retry" inputText={row?.input_text} countable={false} />;
  }

  if (!signedPages) {
    return (
      <div className="flex flex-col items-center gap-4 p-6">
        <p className="font-kid text-lg">Loading your book…</p>
      </div>
    );
  }

  const totalPages = signedPages.length;
  const current = signedPages[pageIndex];

  return (
    // Orientation layout: portrait = column, landscape = row (CSS only, no JS lock)
    <div className="relative flex h-screen w-screen overflow-hidden">
      {/* Left tap zone — 30% of viewport width; hidden on first page */}
      {pageIndex > 0 && (
        <button
          data-testid="nav-prev"
          aria-label="Previous page"
          className="absolute left-0 top-0 h-full w-[30%] z-10 cursor-pointer"
          onClick={() => setPageIndex(i => i - 1)}
        />
      )}

      {/* Page content — portrait stacks, landscape rows */}
      <div className="flex flex-col landscape:flex-row w-full h-full items-center justify-center gap-4 p-4">
        <img
          src={current.signedUrl}
          alt={current.caption}
          className="max-h-[60vh] landscape:max-h-full object-contain rounded-2xl neo-border"
        />
        <p aria-hidden="true" className="font-kid text-base text-center max-w-prose">
          {current.caption}
        </p>
      </div>

      {/* Page indicator */}
      <div
        aria-label={`Page ${pageIndex + 1} of ${totalPages}`}
        className="absolute bottom-4 left-1/2 -translate-x-1/2 font-kid text-sm neo-border rounded-2xl px-3 py-1 bg-[var(--color-surface)]"
      >
        {pageIndex + 1} / {totalPages}
      </div>

      {/* Right tap zone — hidden on last page */}
      {pageIndex < totalPages - 1 && (
        <button
          data-testid="nav-next"
          aria-label="Next page"
          className="absolute right-0 top-0 h-full w-[30%] z-10 cursor-pointer"
          onClick={() => setPageIndex(i => i + 1)}
        />
      )}
    </div>
  );
}
