"use client";

/* eslint-disable @next/next/no-img-element */

import { use, useEffect, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence, useScroll, useMotionValueEvent } from "framer-motion";
import { useJob } from "@/lib/useJob";
import FailureScreen, { resetFailChain } from "@/components/FailureScreen";
import { signPaths } from "@/lib/signedUrls";
import Link from "next/link";
import { useParams } from "next/navigation";
import { CaretLeft, CaretRight, BookOpen, Rows, ArrowLeft } from "@phosphor-icons/react";

function ScrollImage({ src, alt, onClick }: { src: string; alt: string; onClick?: () => void }) {
  const [isLoaded, setIsLoaded] = useState(false);
  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {!isLoaded && <div className="absolute inset-0 bg-[var(--color-muted)]/30 animate-pulse rounded-xl" />}
      <motion.img 
         src={src} 
         alt={alt}
         initial={{ opacity: 0 }}
         animate={{ opacity: isLoaded ? 1 : 0 }}
         transition={{ duration: 0.6, ease: "easeOut" }}
         onLoad={() => setIsLoaded(true)}
         loading="lazy"
         decoding="async"
         className={`w-full h-auto object-contain rounded-xl max-h-[50vh] md:max-h-none relative z-10 ${onClick ? 'cursor-zoom-in' : ''}`}
         onClick={onClick}
      />
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="relative flex h-[100dvh] w-full overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
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

function ScrollView({ signedPages, onNavHide, onImageClick }: { signedPages: SignedPage[]; onNavHide: (hidden: boolean) => void; onImageClick: (url: string) => void }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress, scrollY } = useScroll({ container: scrollRef });

  useMotionValueEvent(scrollY, "change", (latest) => {
    const previous = scrollY.getPrevious() ?? 0;
    if (latest > previous && latest > 150) {
      onNavHide(true);
    } else {
      onNavHide(false);
    }
  });

  useEffect(() => {
    return () => onNavHide(false);
  }, [onNavHide]);

  return (
    <div ref={scrollRef} className="flex-1 w-full h-full overflow-y-auto overflow-x-hidden pt-28 pb-24 px-4 md:px-8 relative z-20 custom-scrollbar">
      <motion.div 
        className="fixed top-0 left-0 right-0 h-1.5 bg-[var(--color-primary)] z-50 origin-left"
        style={{ scaleX: scrollYProgress }}
      />
      <div className="flex flex-col gap-12 md:gap-24 max-w-5xl mx-auto">
        {signedPages.map((page) => (
          <motion.div
            key={page.scene_id}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="flex flex-col md:flex-row bg-[var(--color-surface)] neo-shadow rounded-3xl overflow-hidden"
          >
            <div className="w-full md:w-1/2 flex-shrink-0 bg-[var(--color-muted)]/20 p-4 md:p-8 border-b md:border-b-0 md:border-r border-[var(--color-muted)] flex items-center justify-center">
               <ScrollImage src={page.signedUrl} alt={page.caption} onClick={() => onImageClick(page.signedUrl)} />
            </div>
            <div className="w-full md:w-1/2 p-6 md:p-12 flex flex-col justify-center">
               <p className="font-kid text-lg md:text-2xl leading-relaxed text-[var(--foreground)]">
                 {page.caption}
               </p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}

const SWEPT_STATUS = "__swept__"; // placeholder — replace when data-deletion names it

type SignedPage = { scene_id: string; caption: string; signedUrl: string };

export default function BookPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const routeParams = useParams<{ profileId: string }>();
  const profileId = routeParams?.profileId;
  const { bucket, row } = useJob(jobId);
  const [pageIndex, setPageIndex] = useState(0);
  const [signedPages, setSignedPages] = useState<SignedPage[] | null>(null);
  const [signFailed, setSignFailed] = useState(false);
  const [loaded, setLoaded] = useState<Record<number, boolean>>({});
  const [direction, setDirection] = useState(0);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [viewMode, setViewMode] = useState<"pages" | "scroll">("pages");
  const [navHidden, setNavHidden] = useState(false);
  const [fullscreenImage, setFullscreenImage] = useState<string | null>(null);

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
    if (!signedPages || viewMode !== "pages") return;
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
  }, [signedPages, viewMode]);

  // ── Bucket routing ──────────────────────────────────────────────────────────

  if (bucket === "not-found") {
    return <FailureScreen kind="not-found" jobId={jobId} />;
  }

  if (bucket === "terminal-failure") {
    // Signing failure while book was complete: machine screen, counter NOT bumped
    if (signFailed) {
      return <FailureScreen kind="retry" reason={row?.failure_reason} jobId={jobId} inputText={row?.input_text} stylePresetId={row?.style_preset_id} countable={false} />;
    }
    const kind =
      row?.failure_reason === "child_text"
        ? "revise"
        : row?.status === SWEPT_STATUS
        ? "asleep"
        : "retry";
    return <FailureScreen kind={kind} reason={row?.failure_reason} jobId={jobId} inputText={row?.input_text} stylePresetId={row?.style_preset_id} />;
  }

  if (bucket === "in-flight" || bucket === "paused") {
    return <LoadingSkeleton />;
  }

  // terminal-success — wait for signing
  if (signFailed) {
    // No `reason`: the job succeeded and the row's `failure_reason` is null. Signing is a browser-side
    // failure with no safe reason behind it, so it keeps the legacy machine copy (spec §3 maps a null
    // reason to `system_error`, which would be a lie about a book that generated fine).
    return <FailureScreen kind="retry" jobId={jobId} inputText={row?.input_text} stylePresetId={row?.style_preset_id} countable={false} />;
  }

  if (!signedPages) {
    return <LoadingSkeleton />;
  }

  const totalPages = signedPages.length;
  const current = signedPages[pageIndex];

  return (
    // Layout: Mobile-first stacking, desktop splits symmetrically
    <div className="relative flex h-[100dvh] w-full overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
      
      {/* Ambient magical background blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-[var(--color-primary)] opacity-[0.03] md:opacity-[0.06] blur-[80px] md:blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[60vw] h-[60vw] rounded-full bg-[var(--color-secondary)] opacity-[0.06] md:opacity-[0.08] blur-[80px] md:blur-[140px] pointer-events-none" />
      <div className="absolute top-[40%] left-[60%] w-[40vw] h-[40vw] rounded-full bg-[var(--color-coral)] opacity-[0.04] blur-[80px] md:blur-[120px] pointer-events-none" />

      {/* Lightbox Overlay */}
      <AnimatePresence>
        {fullscreenImage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-sm flex items-center justify-center p-4 cursor-zoom-out"
            onClick={() => setFullscreenImage(null)}
          >
            <motion.img
              src={fullscreenImage}
              alt="Fullscreen view"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ type: "spring", bounce: 0, duration: 0.4 }}
              className="w-full h-full object-contain pointer-events-none rounded-xl"
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Unified Reader Toolbar (Back Button + View Toggle) */}
      <AnimatePresence>
        {!navHidden && (
          <motion.div
            initial={{ y: -100, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -100, opacity: 0 }}
            transition={{ type: "spring", bounce: 0, duration: 0.4 }}
            className="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-1.5 bg-[var(--color-surface)]/90 backdrop-blur-md p-1.5 rounded-full neo-shadow border border-[var(--color-muted)]"
          >
            <Link
              href={profileId ? `/s/${profileId}` : "/"}
              aria-label="Back to bookshelf"
              className="flex h-10 md:h-11 items-center gap-1.5 px-3 md:px-4 rounded-full text-[var(--foreground)] hover:text-[var(--color-primary)] hover:bg-[var(--color-muted)]/20 transition-all font-kid font-bold text-sm shrink-0"
            >
              <ArrowLeft size={20} weight="bold" />
              <span className="hidden sm:inline">Bookshelf</span>
            </Link>

            <div className="w-[1px] h-5 bg-[var(--color-muted)] mx-0.5" />

            <div className="flex items-center gap-1">
              <button
                onClick={() => setViewMode("pages")}
                className={`relative flex items-center justify-center p-2.5 rounded-full transition-colors ${
                  viewMode === "pages" ? "text-white" : "text-[var(--foreground)] hover:bg-[var(--color-muted)]/20"
                }`}
                aria-label="Pages View"
              >
                {viewMode === "pages" && (
                  <motion.div
                    layoutId="view-toggle"
                    className="absolute inset-0 bg-[var(--color-primary)] rounded-full -z-10"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
                <BookOpen size={20} weight={viewMode === "pages" ? "bold" : "regular"} />
              </button>
              <button
                onClick={() => setViewMode("scroll")}
                className={`relative flex items-center justify-center p-2.5 rounded-full transition-colors ${
                  viewMode === "scroll" ? "text-white" : "text-[var(--foreground)] hover:bg-[var(--color-muted)]/20"
                }`}
                aria-label="Scroll View"
              >
                {viewMode === "scroll" && (
                  <motion.div
                    layoutId="view-toggle"
                    className="absolute inset-0 bg-[var(--color-primary)] rounded-full -z-10"
                    transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                  />
                )}
                <Rows size={20} weight={viewMode === "scroll" ? "bold" : "regular"} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Presidio pseudonymizes every detected person name, so a child who wrote "Mia" reads a
          book about "Ana" and has no way to know why. Nothing persists WHETHER a swap happened —
          `redact_pii` only logs entity counts — hence "may", which is true either way and costs
          no contract, schema or migration change. Rendered once outside the viewMode branch so
          both reading modes get it. See docs/capstone/ethics_and_safety.md §1. */}
      <AnimatePresence>
        {!navHidden && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="absolute bottom-3 left-1/2 -translate-x-1/2 z-40 px-3 text-center font-kid text-xs text-[var(--foreground)]/50 pointer-events-none"
          >
            We may change some names to keep you safe.
          </motion.p>
        )}
      </AnimatePresence>

      {viewMode === "pages" ? (
        <>
          {/* Left tap zone: absolute on mobile/tablet, relative column on desktop */}
          <div 
            className={`absolute inset-y-0 left-0 w-[15%] lg:w-24 xl:w-32 z-30 cursor-pointer lg:relative lg:shrink-0 flex items-center justify-start px-4 lg:justify-center lg:px-0 group ${pageIndex > 0 ? "" : "pointer-events-none"}`} 
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
            className="flex h-10 w-10 lg:h-16 lg:w-16 items-center justify-center rounded-full bg-[var(--color-surface)]/90 lg:bg-[var(--color-surface)] neo-shadow text-[var(--color-primary)] opacity-70 lg:opacity-40 hover:opacity-100 transition-opacity duration-normal"
          >
            <CaretLeft className="w-5 h-5 lg:w-8 lg:h-8" weight="bold" />
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
            className="flex flex-col lg:flex-row w-full max-w-6xl lg:max-w-7xl h-auto lg:max-h-[85vh] lg:min-h-[70vh] items-stretch justify-start lg:justify-center bg-[var(--color-surface)] neo-shadow rounded-3xl overflow-hidden mx-4 lg:mx-0"
          >
            {/* Left side: Illustration (Massive on Desktop, contained on mobile) */}
            <div className="relative flex items-center justify-center w-full lg:w-[60%] xl:w-[65%] bg-[var(--color-muted)]/20 p-4 lg:p-10 border-b lg:border-b-0 lg:border-r border-[var(--color-muted)] shrink-0 lg:shrink">
              <img
                src={current.signedUrl}
                alt={current.caption}
                fetchPriority="high"
                className="w-full h-auto max-h-[40vh] lg:max-h-[65vh] object-contain rounded-xl lg:neo-shadow cursor-zoom-in pointer-events-auto"
                onClick={() => setFullscreenImage(current.signedUrl)}
              />
              {!loaded[pageIndex] && (
                <div
                  aria-hidden="true"
                  className="absolute inset-4 lg:inset-10 rounded-xl bg-[var(--color-muted)] animate-pulse pointer-events-none"
                />
              )}
              
              {/* Swipe Indicator (Mobile only, Page 0 only, disappears after interaction) */}
              {pageIndex === 0 && !hasInteracted && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0, 1, 1, 0], x: [0, -20, -20, -40] }}
                  transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                  className="absolute bottom-6 right-6 hidden [@media(pointer:coarse)]:flex items-center gap-2 bg-[var(--color-surface)]/90 backdrop-blur-md rounded-full px-4 py-2 neo-shadow text-[var(--color-primary)] pointer-events-none z-30"
                >
                  <span className="font-kid text-sm font-bold">Swipe</span>
                  <CaretLeft size={16} weight="bold" />
                </motion.div>
              )}
            </div>
            
            {/* Right side: Story Text */}
            <div className="w-full flex-1 lg:w-[40%] xl:w-[35%] flex flex-col justify-between p-6 lg:p-12 bg-[var(--color-surface)] relative overflow-y-auto">
              <div className="flex-1 flex flex-col justify-center pt-2 lg:pt-0">
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

      {/* Right tap zone: absolute on mobile/tablet, relative column on desktop */}
      <div 
        className={`absolute inset-y-0 right-0 w-[15%] lg:w-24 xl:w-32 z-30 cursor-pointer lg:relative lg:shrink-0 flex items-center justify-end px-4 lg:justify-center lg:px-0 group ${pageIndex < totalPages - 1 ? "" : "pointer-events-none"}`} 
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
            className="flex h-10 w-10 lg:h-16 lg:w-16 items-center justify-center rounded-full bg-[var(--color-surface)]/90 lg:bg-[var(--color-surface)] neo-shadow text-[var(--color-primary)] opacity-70 lg:opacity-40 hover:opacity-100 transition-opacity duration-normal"
          >
            <CaretRight className="w-5 h-5 lg:w-8 lg:h-8" weight="bold" />
          </button>
        )}
      </div>
        </>
      ) : (
        /* Scroll view mode */
        <ScrollView signedPages={signedPages} onNavHide={setNavHidden} onImageClick={(url) => setFullscreenImage(url)} />
      )}
    </div>
  );
}
