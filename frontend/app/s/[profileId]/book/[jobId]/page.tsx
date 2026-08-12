"use client";

/* eslint-disable @next/next/no-img-element */

import { use, useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useJob } from "@/lib/useJob";
import FailureScreen, { resetFailChain } from "@/components/FailureScreen";
import { signPaths } from "@/lib/signedUrls";
import { CaretLeft, CaretRight } from "@phosphor-icons/react";

function LoadingSkeleton() {
  return (
    <div className="relative flex h-[100dvh] w-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
      <div className="flex flex-col md:flex-row w-full h-full items-center justify-center gap-8 md:gap-16 p-6 md:p-12">
        <div className="relative flex items-center justify-center w-full md:w-1/2">
          <div className="w-full max-w-md aspect-[4/3] rounded-2xl animate-shimmer neo-border" />
        </div>
        <div className="w-full md:w-1/2 flex flex-col items-center md:items-start gap-4">
          <div className="h-6 w-3/4 rounded-full animate-shimmer" />
          <div className="h-6 w-5/6 rounded-full animate-shimmer" />
          <div className="h-6 w-1/2 rounded-full animate-shimmer" />
        </div>
      </div>
    </div>
  );
}

const SWEPT_STATUS = "__swept__"; // placeholder — replace when data-deletion names it

type SignedPage = { scene_id: string; caption: string; signedUrl: string };

export default function BookPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const { bucket, row } = useJob(jobId);
  const [pageIndex, setPageIndex] = useState(0);
  const [signedPages, setSignedPages] = useState<SignedPage[] | null>(null);
  const [signFailed, setSignFailed] = useState(false);
  const [loaded, setLoaded] = useState<Record<number, boolean>>({});
  const [direction, setDirection] = useState(0);
  const [hasInteracted, setHasInteracted] = useState(false);

  const signPages = useCallback(async (attempt: number) => {
    if (!row?.pages.length) return;
    const pagesList = row.pages;
    const paths = pagesList.map(p => p.image_path);
    async function doSign(att: number): Promise<void> {
      const signed = await signPaths(paths);
      if (paths.some(p => !signed[p])) {
        if (att < 2) {
          console.log("sb:action", { action: "re-sign" });
          await doSign(att + 1);
          return;
        }
        setSignFailed(true);
        return;
      }
      const pages: SignedPage[] = pagesList.map(p => ({
        scene_id: p.scene_id,
        caption: p.caption,
        signedUrl: signed[p.image_path],
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
        setHasInteracted(true);
        setDirection(1);
        setPageIndex(i => Math.min(i + 1, signedPages!.length - 1));
      }
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        setHasInteracted(true);
        setDirection(-1);
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
    return <LoadingSkeleton />;
  }

  // terminal-success — wait for signing
  if (signFailed) {
    return <FailureScreen kind="retry" inputText={row?.input_text} countable={false} />;
  }

  if (!signedPages) {
    return <LoadingSkeleton />;
  }

  const totalPages = signedPages.length;
  const current = signedPages[pageIndex];

  return (
    // Layout: Mobile-first stacking, desktop splits symmetrically
    <div className="relative flex h-[100dvh] w-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
      
      {/* Ambient magical background blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-[var(--color-primary)] opacity-[0.03] md:opacity-[0.06] blur-[80px] md:blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[60vw] h-[60vw] rounded-full bg-[var(--color-secondary)] opacity-[0.06] md:opacity-[0.08] blur-[80px] md:blur-[140px] pointer-events-none" />
      <div className="absolute top-[40%] left-[60%] w-[40vw] h-[40vw] rounded-full bg-[var(--color-coral)] opacity-[0.04] blur-[80px] md:blur-[120px] pointer-events-none" />

      {/* Left tap zone: absolute on mobile, relative column on desktop */}
      <div 
        className={`absolute inset-y-0 left-0 w-[15%] md:w-24 lg:w-32 z-10 cursor-pointer md:relative md:shrink-0 flex items-center justify-start px-4 md:justify-center md:px-0 group ${pageIndex > 0 ? "" : "pointer-events-none"}`} 
        onClick={() => {
          setHasInteracted(true);
          if (pageIndex > 0) {
            setDirection(-1);
            setPageIndex(pageIndex - 1);
          }
        }}
      >
        {pageIndex > 0 && (
          <button
            data-testid="nav-prev"
            aria-label="Previous page"
            className="hidden md:flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-surface)] neo-shadow text-[var(--color-primary)] opacity-40 hover:opacity-100 transition-opacity duration-normal"
          >
            <CaretLeft size={32} weight="bold" />
          </button>
        )}
      </div>

      {/* Page content with swipe */}
      <motion.div 
        className="flex-1 flex w-full h-full items-center justify-center py-6 md:py-12 z-20"
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.2}
        onDragEnd={(e, { offset }) => {
          setHasInteracted(true);
          if (offset.x < -50 && pageIndex < totalPages - 1) {
            setDirection(1);
            setPageIndex(pageIndex + 1);
          }
          if (offset.x > 50 && pageIndex > 0) {
            setDirection(-1);
            setPageIndex(pageIndex - 1);
          }
        }}
      >
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={pageIndex}
            custom={direction}
            variants={{
              enter: (dir: number) => ({ x: dir > 0 ? 40 : -40, opacity: 0, scale: 0.98 }),
              center: { x: 0, opacity: 1, scale: 1 },
              exit: (dir: number) => ({ x: dir < 0 ? 40 : -40, opacity: 0, scale: 0.98 })
            }}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col md:flex-row w-full max-w-6xl lg:max-w-7xl h-auto max-h-[85vh] md:min-h-[70vh] items-stretch justify-start md:justify-center bg-[var(--color-surface)] neo-shadow rounded-3xl overflow-hidden mx-4 md:mx-0"
          >
            {/* Left side: Illustration (Massive on Desktop, contained on mobile) */}
            <div className="relative flex items-center justify-center w-full md:w-[60%] lg:w-[65%] bg-[var(--color-muted)]/20 p-4 md:p-10 border-b md:border-b-0 md:border-r border-[var(--color-muted)] shrink-0 md:shrink">
              <img
                src={current.signedUrl}
                alt={current.caption}
                fetchPriority="high"
                className="w-full h-auto max-h-[40vh] md:max-h-[65vh] object-contain rounded-xl md:neo-shadow pointer-events-none"
              />
              {!loaded[pageIndex] && (
                <div
                  aria-hidden="true"
                  className="absolute inset-4 md:inset-10 rounded-xl bg-[var(--color-muted)] animate-pulse"
                />
              )}
              
              {/* Swipe Indicator (Mobile only, Page 0 only, disappears after interaction) */}
              {pageIndex === 0 && !hasInteracted && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0, 1, 1, 0], x: [0, -20, -20, -40] }}
                  transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                  className="absolute bottom-6 right-6 flex items-center gap-2 bg-[var(--color-surface)]/90 backdrop-blur-md rounded-full px-4 py-2 neo-shadow text-[var(--color-primary)] md:hidden pointer-events-none z-30"
                >
                  <span className="font-kid text-sm font-bold">Swipe</span>
                  <CaretLeft size={16} weight="bold" />
                </motion.div>
              )}
            </div>
            
            {/* Right side: Story Text */}
            <div className="w-full flex-1 md:w-[40%] lg:w-[35%] flex flex-col justify-between p-6 md:p-12 bg-[var(--color-surface)] relative overflow-y-auto">
              <div className="flex-1 flex flex-col justify-center pt-2 md:pt-0">
                <p aria-hidden="true" className="font-kid text-lg md:text-2xl lg:text-3xl leading-relaxed text-[var(--foreground)] text-left max-w-[60ch]">
                  {current.caption}
                </p>
              </div>
              
              {/* Progress dots at the bottom */}
              <div className="mt-6 md:mt-8 flex justify-start items-center gap-2 shrink-0" aria-label={`Page ${pageIndex + 1} of ${totalPages}`}>
                {signedPages.map((_, i) => (
                  <button
                    key={i}
                    aria-label={`Go to page ${i + 1}`}
                    className={`h-2 rounded-full transition-all duration-300 ${
                      i === pageIndex
                        ? "w-8 bg-[var(--color-primary)]"
                        : "w-2 bg-[var(--color-muted)] hover:bg-[var(--color-primary-deep)]/50"
                    }`}
                    onClick={(e) => {
                       e.stopPropagation();
                       setHasInteracted(true);
                       if (i !== pageIndex) {
                         setDirection(i > pageIndex ? 1 : -1);
                         setPageIndex(i);
                       }
                    }}
                  />
                ))}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </motion.div>

      {/* Preload the neighbours only. Preloading all 15 pages pulled tens of MB of
          full-res PNG that competed with the page the child is actually looking at. */}
      <div className="hidden">
        {signedPages.map((p, i) => (
          Math.abs(i - pageIndex) <= 1 ? (
            <img
              key={p.scene_id}
              src={p.signedUrl}
              alt=""
              onLoad={() => setLoaded(l => (l[i] ? l : { ...l, [i]: true }))}
            />
          ) : null
        ))}
      </div>

      {/* Right tap zone: absolute on mobile, relative column on desktop */}
      <div 
        className={`absolute inset-y-0 right-0 w-[15%] md:w-24 lg:w-32 z-10 cursor-pointer md:relative md:shrink-0 flex items-center justify-end px-4 md:justify-center md:px-0 group ${pageIndex < totalPages - 1 ? "" : "pointer-events-none"}`} 
        onClick={() => {
          setHasInteracted(true);
          if (pageIndex < totalPages - 1) {
            setDirection(1);
            setPageIndex(pageIndex + 1);
          }
        }}
      >
        {pageIndex < totalPages - 1 && (
          <button
            data-testid="nav-next"
            aria-label="Next page"
            className="hidden md:flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-surface)] neo-shadow text-[var(--color-primary)] opacity-40 hover:opacity-100 transition-opacity duration-normal"
          >
            <CaretRight size={32} weight="bold" />
          </button>
        )}
      </div>
    </div>
  );
}
