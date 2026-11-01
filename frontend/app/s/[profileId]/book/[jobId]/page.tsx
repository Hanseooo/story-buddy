"use client";

/* eslint-disable @next/next/no-img-element */

import { use, useEffect, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence, useScroll } from "framer-motion";
import { useJob } from "@/lib/useJob";
import { displayTitle } from "@/lib/displayTitle";
import FailureScreen, { resetFailChain } from "@/components/FailureScreen";
import StoppedStory from "@/components/StoppedStory";
import { signPaths } from "@/lib/signedUrls";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import { useParams } from "next/navigation";
import { CaretLeft, CaretRight, BookOpen, Rows, ArrowLeft, DownloadSimple } from "@phosphor-icons/react";

function ScrollImage({ src, alt, onClick }: { src: string; alt: string; onClick?: () => void }) {
  const [isLoaded, setIsLoaded] = useState(false);
  return (
    <div className="relative w-full h-full flex items-center justify-center">
      {!isLoaded && <div className="absolute inset-0 bg-muted/30 animate-pulse rounded-xl" />}
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
    <div className="relative flex min-h-[calc(100dvh-5rem)] flex-1 w-full overflow-hidden bg-background text-foreground">
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

function ScrollView({ signedPages, onImageClick }: { signedPages: SignedPage[]; onImageClick: (url: string) => void }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ container: scrollRef });

  return (
    <div ref={scrollRef} className="flex-1 w-full h-full overflow-y-auto overflow-x-hidden pt-4 pb-20 px-4 md:px-8 relative z-20 custom-scrollbar">
      <motion.div 
        className="fixed top-0 left-0 right-0 h-[3px] bg-primary z-50 origin-left"
        style={{ scaleX: scrollYProgress }}
      />
      <div className="flex flex-col gap-8 md:gap-16 max-w-5xl mx-auto">
        {signedPages.map((page) => (
          <motion.div
            key={page.scene_id}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="flex flex-col md:flex-row bg-surface neo-shadow rounded-3xl overflow-hidden border border-muted"
          >
            <div className="w-full md:w-1/2 flex-shrink-0 bg-muted/20 p-4 md:p-8 border-b md:border-b-0 md:border-r border-muted flex items-center justify-center">
               <ScrollImage src={page.signedUrl} alt={page.caption} onClick={() => onImageClick(page.signedUrl)} />
            </div>
            <div className="w-full md:w-1/2 p-6 md:p-12 flex flex-col justify-center">
               <p className="font-kid text-lg md:text-2xl leading-relaxed text-foreground">
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

type SignedPage = { scene_id: string; caption: string; signedUrl: string; image_path: string; other_versions?: boolean };

type PageVersion = { version_id: string; image_path: string };

// ADR-082 / magic-pencil 09: a finished page's other attempts cost no image. Opening asks the API to
// moderate the ones nobody checked (SH-02). A choice carries the picture it was made from, so a stale
// one is rejected (SH-08), and a reviewed book goes back to the teacher, so the child confirms first (AC-21).
function PageVersions({ jobId, pageNumber, page, reviewed, busy, onBusy, onChanged }: {
  jobId: string; pageNumber: number; page: SignedPage; reviewed: boolean; busy: boolean;
  onBusy: (busy: boolean) => void; onChanged: () => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [versions, setVersions] = useState<PageVersion[]>([]);
  const [unavailable, setUnavailable] = useState(0);
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [loaded, setLoaded] = useState<Record<string, boolean>>({});
  const [attempt, setAttempt] = useState(0);
  const [changeError, setChangeError] = useState("");
  const [pending, setPending] = useState<{ version: PageVersion; button: HTMLButtonElement } | null>(null);
  const openerRef = useRef<HTMLButtonElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const confirmRef = useRef<HTMLDialogElement | null>(null);
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  const listId = `page-versions-${page.scene_id}`;

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void (async () => {
      let list: PageVersion[] = [];
      let missing = 0;
      let signed: Record<string, string> = {};
      let failed = false;
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/pages/${encodeURIComponent(page.scene_id)}/versions/open`,
          { method: "POST", headers: { Authorization: `Bearer ${session?.access_token}` }, signal: controller.signal },
        );
        if (!response.ok) throw new Error("versions_unavailable");
        ({ versions: list, unavailable: missing } = await response.json());
        signed = await signPaths(list.map((v) => v.image_path),
          [{ id: jobId, moderation_mode: "teacher_review_v1", page_versions: list }], controller.signal);
      } catch { failed = true; /* shown as the error state below */ }
      if (controller.signal.aborted) return;
      setVersions(list);
      setUnavailable(missing);
      setUrls(signed);
      setState(!failed && list.every((v) => signed[v.image_path]) ? "ready" : "error");
    })();
    return () => controller.abort();
  }, [open, attempt, jobId, page.scene_id, page.image_path]);

  useEffect(() => { if (open) listRef.current?.focus(); }, [open]);

  function close() {
    setOpen(false);
    setChangeError("");
    openerRef.current?.focus();
  }

  function cancelConfirm() {
    confirmRef.current?.close();
    pending?.button.focus();
    setPending(null);
  }

  async function change(version: PageVersion) {
    confirmRef.current?.close();
    setPending(null);
    onBusy(true);
    setChangeError("");
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/pages/${encodeURIComponent(page.scene_id)}/version`,
        { method: "POST", headers: { Authorization: `Bearer ${session?.access_token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ version_id: version.version_id, source: page.image_path }) },
      );
      if (response.status === 409) {
        await onChanged();
        setChangeError("This page changed. Have another look.");
        setState("loading");
        setAttempt((value) => value + 1);
        return;
      }
      if (!response.ok) throw new Error("change_unavailable");
      await onChanged();
      close();
    } catch {
      setChangeError("We couldn't change this picture right now. Try again.");
    } finally {
      onBusy(false);
    }
  }

  function choose(version: PageVersion, button: HTMLButtonElement) {
    if (!reviewed) { void change(version); return; }
    setPending({ version, button });
    confirmRef.current?.showModal();
    confirmButtonRef.current?.focus();
  }

  return (
    <div className="mt-4 w-full">
      <button
        ref={openerRef}
        type="button"
        aria-label={`Other versions of page ${pageNumber}`}
        aria-expanded={open}
        aria-controls={listId}
        disabled={busy && !open}
        onClick={() => {
          setState("loading");
          setLoaded({});
          setChangeError("");
          setOpen((value) => !value);
        }}
        className="min-h-11 rounded-xl border border-primary/20 bg-background px-4 py-2 font-kid text-sm font-bold text-foreground hover:bg-primary/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Other versions
      </button>
      {open && (
        <div
          ref={listRef}
          id={listId}
          role="group"
          aria-label={`Other versions of page ${pageNumber}`}
          tabIndex={-1}
          onKeyDown={(event) => {
            if (event.key !== "Escape" || busy || pending) return;
            event.stopPropagation();
            close();
          }}
          className="mt-3 w-full rounded-2xl bg-primary/5 p-4 text-left focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
        >
          <p role="status" className="font-kid text-sm text-foreground/70">
            {busy ? "Changing your picture…" : state === "loading" ? `Loading other pictures for page ${pageNumber}…` : ""}
          </p>
          {changeError && <p role="alert" className="mt-2 font-kid text-sm">{changeError}</p>}
          {(state === "error" || (state === "ready" && unavailable > 0)) && (
            <div role="alert" className="mt-2 flex flex-col items-start gap-2 font-kid text-sm">
              <p>We couldn&apos;t load this picture right now.</p>
              <button
                type="button"
                onClick={() => { setState("loading"); setAttempt((value) => value + 1); }}
                className="min-h-11 rounded-xl bg-surface px-4 py-2 font-bold focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
              >
                Try loading the pictures for page {pageNumber} again
              </button>
            </div>
          )}
          {state === "ready" && versions.length === 0 && unavailable === 0 && (
            <p className="mt-2 font-kid text-sm">There are no other pictures for page {pageNumber} right now.</p>
          )}
          {state === "ready" && versions.length > 0 && (
            <ul className="mt-2 grid grid-cols-2 gap-2">
              {versions.map((version, index) => (
                <li key={version.version_id}>
                  <button
                    type="button"
                    aria-label={`Use other picture ${index + 1} for page ${pageNumber}`}
                    disabled={busy || !loaded[version.version_id]}
                    onClick={(event) => choose(version, event.currentTarget)}
                    className="w-full rounded-xl border border-primary/20 bg-background p-1 hover:bg-primary/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <img
                      src={urls[version.image_path]}
                      alt={`Other picture ${index + 1} for page ${pageNumber}`}
                      className="aspect-square w-full rounded-lg bg-muted object-contain"
                      onLoad={() => setLoaded((current) => ({ ...current, [version.version_id]: true }))}
                      onError={() => setState("error")}
                    />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button
            type="button"
            aria-label={`Close other versions of page ${pageNumber}`}
            disabled={busy}
            onClick={close}
            className="mt-3 min-h-11 rounded-xl px-4 py-2 font-kid font-bold text-foreground focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      )}
      <dialog ref={confirmRef} aria-labelledby={`${listId}-confirm`} onCancel={(event) => { event.preventDefault(); cancelConfirm(); }}
        className="m-auto max-w-md rounded-2xl bg-background p-6 font-kid text-foreground backdrop:bg-foreground/50">
        <h2 id={`${listId}-confirm`} className="text-xl font-bold">Your teacher will look at your book again before classmates can see it.</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" ref={confirmButtonRef} onClick={() => pending && void change(pending.version)}
            className="min-h-11 rounded-xl bg-primary px-4 font-bold text-on-primary focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">
            Change page {pageNumber}
          </button>
          <button type="button" onClick={cancelConfirm}
            className="min-h-11 rounded-xl px-4 font-bold focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">
            Keep page {pageNumber} as it is
          </button>
        </div>
      </dialog>
    </div>
  );
}

type ChildNote = { job_id: string; body: string; seen: boolean; updated_at: string };

function TeacherNote({ jobId }: { jobId: string }) {
  const [note, setNote] = useState<ChildNote | null>(null);
  const [open, setOpen] = useState(true);
  const [saveError, setSaveError] = useState(false);
  const [retry, setRetry] = useState(0);
  const summary = useRef<HTMLElement>(null);
  const version = useRef<string | null>(null);

  useEffect(() => {
    let active: AbortController | undefined;
    async function load() {
      active?.abort();
      const controller = new AbortController();
      active = controller;
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (controller.signal.aborted) return;
        if (!session) { setNote(null); version.current = null; return; }
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/me/notes`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
          cache: "no-store", signal: controller.signal,
        });
        if (!response.ok) throw new Error("notes unavailable");
        const notes: ChildNote[] = await response.json();
        if (controller.signal.aborted) return;
        const current = notes.find(item => item.job_id === jobId) ?? null;
        if (current?.updated_at !== version.current) setOpen(true);
        version.current = current?.updated_at ?? null;
        setNote(current);
      } catch {
        if (!controller.signal.aborted) setNote(null);
      }
    }
    void load();
    window.addEventListener("focus", load);
    return () => { active?.abort(); window.removeEventListener("focus", load); };
  }, [jobId]);

  useEffect(() => {
    if (!note || !open || note.seen) return;
    const controller = new AbortController();
    async function markSeen() {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (controller.signal.aborted) return;
        if (!session) throw new Error("session unavailable");
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/note/seen`, {
          method: "POST", headers: { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ updated_at: note!.updated_at }), signal: controller.signal,
        });
        if (response.status === 404) {
          if (!controller.signal.aborted) setNote(null);
          return;
        }
        if (!response.ok) throw new Error("note unavailable");
        if (!controller.signal.aborted) {
          setSaveError(false);
          setNote(previous => previous?.updated_at === note!.updated_at ? { ...previous, seen: true } : previous);
        }
      } catch {
        if (!controller.signal.aborted) setSaveError(true);
      }
    }
    void markSeen();
    return () => controller.abort();
  }, [jobId, note, open, retry]);

  useEffect(() => {
    if (!note || !open) return;
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") { setOpen(false); summary.current?.focus(); }
    }
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [note, open]);

  if (!note) return null;
  return (
    <details open={open} onToggle={event => setOpen(event.currentTarget.open)}
      className="relative z-30 mx-auto my-4 w-[calc(100%-2.5rem)] max-w-3xl rounded-2xl border border-primary/15 bg-surface px-5 font-kid text-foreground">
      <summary ref={summary} className="min-h-11 cursor-pointer py-3 font-extrabold focus-visible:outline-secondary focus-visible:outline-3">
        A note from your teacher
      </summary>
      <div className="pb-4">
        <p className="max-w-prose whitespace-pre-wrap break-words text-lg leading-relaxed">{note.body}</p>
        <div aria-live="polite">
          {saveError && <p className="mt-3 text-sm">We couldn&apos;t save your place. <button type="button" onClick={() => setRetry(value => value + 1)} className="min-h-11 underline focus-visible:outline-secondary">Try again</button></p>}
        </div>
        <button type="button" onClick={() => { setOpen(false); summary.current?.focus(); }}
          className="mt-3 min-h-11 rounded-xl px-4 font-bold text-primary hover:bg-muted/30 focus-visible:outline-secondary focus-visible:outline-3">Close</button>
      </div>
    </details>
  );
}

export default function BookPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
  const routeParams = useParams<{ profileId: string }>();
  const profileId = routeParams?.profileId;
  const { bucket, row, refetch } = useJob(jobId);
  const [pageIndex, setPageIndex] = useState(0);
  const [signedPages, setSignedPages] = useState<SignedPage[] | null>(null);
  const [signFailed, setSignFailed] = useState(false);
  const [loaded, setLoaded] = useState<Record<number, boolean>>({});
  const [direction, setDirection] = useState(0);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [viewMode, setViewMode] = useState<"pages" | "scroll">("pages");
  const [fullscreenImage, setFullscreenImage] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [changingPage, setChangingPage] = useState(false); // SH-07: one page change per book at a time
  const downloadRequest = useRef<AbortController | null>(null);
  const imageRequest = useRef<AbortController | null>(null);
  const ownsBook = Boolean(profileId && row?.profile_id === profileId);
  // RLS supplies readable classroom books; the PDF endpoint rechecks active membership/approval.
  const canDownload = Boolean(profileId && row?.approved_at) && !row?.rejected_at;
  const showDownload = ownsBook || canDownload;

  useEffect(() => () => downloadRequest.current?.abort(), [jobId, canDownload]);

  async function downloadPdf() {
    if (!canDownload || downloadRequest.current) return;
    const controller = new AbortController();
    downloadRequest.current = controller;
    setExporting(true);
    setExportError("");
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (controller.signal.aborted) return;
      if (!session) throw new Error("session unavailable");
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/pdf`, {
        headers: { Authorization: `Bearer ${session.access_token}` },
        signal: controller.signal,
      });
      // A withdrawn peer approval can hide the row before Realtime delivers its update.
      if (response.status === 404 || response.status === 409) {
        if (controller.signal.aborted) return;
        await refetch();
      }
      if (!response.ok || !response.headers.get("content-type")?.includes("application/pdf")) {
        throw new Error("download unavailable");
      }
      const blob = await response.blob();
      if (controller.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = response.headers.get("content-disposition")?.match(/filename="([^"]+)"/)?.[1] ?? "storybook.pdf";
      document.body.appendChild(link);
      link.click();
      link.remove();
      // Give mobile browsers time to begin consuming the blob before releasing it.
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      if (!controller.signal.aborted) setExportError("We couldn't download your book. Try again.");
    } finally {
      downloadRequest.current = null;
      setExporting(false);
    }
  }

  const signPages = useCallback(async (attempt: number) => {
    if (!row?.pages.length) return;
    const pagesList = row.pages;
    const paths = pagesList.map(p => p.image_path);
    const controller = imageRequest.current;
    async function doSign(att: number): Promise<void> {
      const signed = await signPaths(paths, [{id: jobId, moderation_mode: row?.moderation_mode, pages: pagesList}], controller?.signal);
      if (controller?.signal.aborted) return;
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
        image_path: p.image_path,
        other_versions: p.other_versions,
      }));
      setSignedPages(pages);
      resetFailChain(); // actual book is on screen — chain is over
    }
    await doSign(attempt);
  }, [jobId, row?.moderation_mode, row?.pages]);

  useEffect(() => {
    if (bucket !== "terminal-success") return;
    const controller = new AbortController();
    imageRequest.current = controller;
    signPages(1);
    return () => { controller.abort(); };
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
      return <FailureScreen kind="retry" reason={row?.failure_reason} jobId={jobId} inputText={row?.input_text} title={row?.title} stylePresetId={row?.style_preset_id} countable={false} />;
    }
    const kind =
      row?.failure_reason === "child_text"
        ? "revise"
        : row?.status === SWEPT_STATUS
        ? "asleep"
        : "retry";
    return <FailureScreen kind={kind} reason={row?.failure_reason} jobId={jobId} inputText={row?.input_text} title={row?.title} stylePresetId={row?.style_preset_id} />;
  }

  if (bucket === "stopped") return <StoppedStory jobId={jobId} profileId={profileId} />;
  if (bucket === "teacher-held") {
    return <main className="flex flex-1 flex-col items-center justify-center gap-6 p-6 text-center">
      <h1 className="font-display text-3xl font-extrabold">Waiting for your teacher</h1>
      <p>Your story is saved. Your teacher will help it continue.</p>
      <Link href={`/s/${profileId}`} className="min-h-11 rounded-2xl bg-primary px-6 py-3 font-bold text-on-primary">Back to my books</Link>
    </main>;
  }
  if (bucket === "in-flight" || bucket === "paused") {
    return <LoadingSkeleton />;
  }

  // terminal-success — wait for signing
  if (signFailed) {
    // The job succeeded: the row is `complete`, the pages are real, and `failure_reason` is null.
    // Signing is a browser-side read failure, so the honest fix is re-signing the same paths —
    // not a new paid generation (spec §4, kid-flow-failure-semantics §4.7). Passing no `reason`
    // keeps this off the safe taxonomy, which would claim a finished book failed to be made.
    return (
      <FailureScreen
        kind="read-failed"
        jobId={jobId}
        inputText={row?.input_text}
        title={row?.title}
        countable={false}
        onReload={() => {
          setSignFailed(false);
          signPages(1);
        }}
      />
    );
  }

  if (!signedPages) {
    return <LoadingSkeleton />;
  }

  const totalPages = signedPages.length;
  const current = signedPages[pageIndex];

  return (
    // Layout: Mobile-first stacking, desktop splits symmetrically
    <div className="relative flex min-h-[calc(100dvh-5rem)] flex-1 w-full flex-col justify-between overflow-hidden bg-background text-foreground">
      
      {row?.profile_id === profileId && <TeacherNote key={jobId} jobId={jobId} />}

      {/* Ambient magical background blobs */}
      <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-primary opacity-[0.03] md:opacity-[0.06] blur-[80px] md:blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-5%] w-[60vw] h-[60vw] rounded-full bg-secondary opacity-[0.06] md:opacity-[0.08] blur-[80px] md:blur-[140px] pointer-events-none" />
      <div className="absolute top-[40%] left-[60%] w-[40vw] h-[40vw] rounded-full bg-coral opacity-[0.04] blur-[80px] md:blur-[120px] pointer-events-none" />

      {/* Lightbox Overlay */}
      <AnimatePresence>
        {fullscreenImage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-[100] bg-[#18204A]/90 backdrop-blur-sm flex items-center justify-center p-4 md:p-8 cursor-zoom-out"
            onClick={() => setFullscreenImage(null)}
          >
            <motion.img
              src={fullscreenImage}
              alt="Fullscreen view"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              transition={{ type: "spring", bounce: 0, duration: 0.4 }}
              className="max-w-full max-h-full object-contain pointer-events-none rounded-2xl neo-shadow-xl"
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Navigation and export share a row; the mobile title always has its own width. */}
      <div className="relative z-30 mx-auto grid w-full max-w-6xl grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-3 px-5 pt-5 pb-2 sm:px-8 lg:max-w-7xl lg:grid-cols-[auto_minmax(0,1fr)_auto] lg:px-12">
        <Link
          href={profileId ? `/s/${profileId}` : "/"}
          aria-label="Back to bookshelf"
          className="order-1 inline-flex min-h-11 items-center justify-self-start gap-1.5 rounded-xl px-2 font-kid text-sm font-bold text-foreground/75 transition-colors hover:bg-muted/30 hover:text-primary focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 sm:px-3"
        >
          <ArrowLeft size={20} weight="bold" aria-hidden="true" />
          <span>Bookshelf</span>
        </Link>

        <h1 className="order-3 col-span-2 min-w-0 text-center font-display text-xl leading-snug font-extrabold break-words text-foreground sm:text-2xl lg:order-2 lg:col-span-1 lg:px-6">
          {/* `profileId` is an authenticated identity here, not a typed-in segment: `guardRequest`
              redirects any /s/:id whose id is not the session user (middleware.ts), so this
              equals the `profile_id = auth.uid()` the RLS policy uses. Comparing it to the row
              is what keeps a classmate's raw story out of the heading of their untitled book. */}
          {displayTitle(row?.title, row?.profile_id === profileId ? row?.input_text : null)}
        </h1>

        {showDownload && (
          <button
            type="button"
            onClick={downloadPdf}
            disabled={!canDownload || exporting}
            aria-busy={exporting}
            aria-describedby={!canDownload ? "pdf-approval-hint" : undefined}
            className="order-2 col-start-2 row-start-1 inline-flex min-h-11 items-center justify-center justify-self-end gap-1.5 rounded-xl border border-primary/20 bg-surface px-3 py-2 font-kid text-sm font-bold whitespace-nowrap text-primary transition-colors hover:bg-muted/30 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:cursor-not-allowed disabled:opacity-50 lg:order-3 lg:col-start-3"
          >
            <DownloadSimple size={18} weight="bold" aria-hidden="true" />
            {exporting ? "Preparing PDF…" : "Download PDF"}
          </button>
        )}

        {showDownload && (!canDownload || exportError) && (
          <div className="order-2 col-span-2 text-right font-kid text-sm lg:order-4 lg:col-span-3">
            {!canDownload && (
              <p id="pdf-approval-hint" className="text-foreground/75">
                Ask your teacher about downloading this book
              </p>
            )}
            {canDownload && exportError && <p role="alert" className="text-destructive">{exportError}</p>}
          </div>
        )}
        <p role="status" aria-live="polite" className="sr-only">
          {exporting ? "Preparing your PDF. You can keep reading." : ""}
        </p>

        <div
          role="group"
          aria-label="Reading view mode"
          className="order-4 col-span-2 flex items-center justify-self-center gap-1 rounded-2xl border border-primary/15 bg-surface p-1 lg:order-5 lg:col-span-3"
        >
          <button
            type="button"
            onClick={() => setViewMode("pages")}
            aria-label="Pages View"
            aria-pressed={viewMode === "pages"}
            className={`flex min-h-11 items-center gap-1.5 rounded-xl px-4 py-1.5 font-kid text-sm font-bold transition-colors focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 cursor-pointer ${
              viewMode === "pages"
                ? "bg-primary text-on-primary"
                : "text-foreground/75 hover:text-primary hover:bg-muted/30"
            }`}
          >
            <BookOpen size={18} weight={viewMode === "pages" ? "bold" : "regular"} aria-hidden="true" />
            <span>Pages</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode("scroll")}
            aria-label="Scroll View"
            aria-pressed={viewMode === "scroll"}
            className={`flex min-h-11 items-center gap-1.5 rounded-xl px-4 py-1.5 font-kid text-sm font-bold transition-colors focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 cursor-pointer ${
              viewMode === "scroll"
                ? "bg-primary text-on-primary"
                : "text-foreground/75 hover:text-primary hover:bg-muted/30"
            }`}
          >
            <Rows size={18} weight={viewMode === "scroll" ? "bold" : "regular"} aria-hidden="true" />
            <span>Scroll</span>
          </button>
        </div>
      </div>

      {viewMode === "pages" ? (
        <>
          <div className="flex-1 flex w-full items-center justify-between relative px-2 sm:px-4 lg:px-8 py-4 sm:py-6">
            {/* Left tap zone: absolute on mobile/tablet, relative column on desktop */}
            {totalPages > 1 && (
              <div 
                className={`absolute inset-y-0 left-0 w-[15%] lg:w-24 xl:w-32 z-30 cursor-pointer lg:relative lg:shrink-0 flex items-center justify-start px-2 sm:px-4 lg:justify-center lg:px-0 group ${pageIndex > 0 ? "" : "pointer-events-none"}`} 
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
                    className="flex h-11 w-11 lg:h-16 lg:w-16 items-center justify-center rounded-full bg-surface neo-shadow text-primary font-bold hover:scale-105 transition-all cursor-pointer"
                  >
                    <CaretLeft className="w-5 h-5 lg:w-8 lg:h-8" weight="bold" />
                  </button>
                )}
              </div>
            )}

            {/* Page content with swipe */}
            <motion.div 
              className="flex-1 flex w-full h-full items-center justify-center z-20 mx-auto max-w-6xl"
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
                  className="flex flex-col lg:flex-row w-full h-auto lg:max-h-[80vh] lg:min-h-[65vh] items-stretch justify-start lg:justify-center bg-surface neo-shadow rounded-3xl overflow-hidden mx-2 sm:mx-4 lg:mx-0 border border-muted"
                >
                  {/* Left side: Illustration (Massive on Desktop, contained on mobile) */}
                  <div className="relative flex items-center justify-center w-full lg:w-[60%] xl:w-[65%] bg-muted/20 p-4 lg:p-10 border-b lg:border-b-0 lg:border-r border-muted shrink-0 lg:shrink">
                    <img
                      src={current.signedUrl}
                      alt={current.caption}
                      fetchPriority="high"
                      className="w-full h-auto max-h-[40vh] lg:max-h-[60vh] object-contain rounded-xl lg:neo-shadow cursor-zoom-in pointer-events-auto"
                      onClick={() => setFullscreenImage(current.signedUrl)}
                    />
                    {!loaded[pageIndex] && (
                      <div
                        aria-hidden="true"
                        className="absolute inset-4 lg:inset-10 rounded-xl bg-muted animate-pulse pointer-events-none"
                      />
                    )}
                    
                    {/* Swipe Indicator (Mobile only, Page 0 only, disappears after interaction) */}
                    {pageIndex === 0 && !hasInteracted && (
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: [0, 1, 1, 0], x: [0, -20, -20, -40] }}
                        transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
                        className="absolute bottom-6 right-6 hidden [@media(pointer:coarse)]:flex items-center gap-2 bg-surface/90 backdrop-blur-md rounded-full px-4 py-2 neo-shadow text-primary pointer-events-none z-30"
                      >
                        <span className="font-kid text-sm font-bold">Swipe</span>
                        <CaretLeft size={16} weight="bold" />
                      </motion.div>
                    )}
                  </div>
                  
                  {/* Right side: Story Text */}
                  <div className="w-full flex-1 lg:w-[40%] xl:w-[35%] flex flex-col justify-between p-6 lg:p-12 bg-surface relative overflow-y-auto">
                    <div className="flex-1 flex flex-col justify-center pt-2 lg:pt-0">
                      <p aria-hidden="true" className="font-kid text-lg md:text-2xl lg:text-3xl leading-relaxed text-foreground text-left max-w-[60ch]">
                        {current.caption}
                      </p>
                      {ownsBook && current.other_versions && (
                        <PageVersions key={current.scene_id} jobId={jobId} pageNumber={pageIndex + 1} page={current}
                          reviewed={Boolean(row?.approved_at || row?.rejected_at)} busy={changingPage}
                          onBusy={setChangingPage} onChanged={refetch} />
                      )}
                    </div>
                    
                    {/* Progress dots at the bottom */}
                    <div className="mt-4 flex flex-wrap items-center justify-start gap-1 shrink-0 md:mt-6" aria-label={`Page ${pageIndex + 1} of ${totalPages}`}>
                      {signedPages.map((_, i) => (
                        <button
                          key={i}
                          type="button"
                          aria-label={`Go to page ${i + 1}`}
                          aria-current={i === pageIndex ? "page" : undefined}
                          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-colors hover:bg-muted/30 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 cursor-pointer"
                          onClick={(e) => {
                             e.stopPropagation();
                             setHasInteracted(true);
                             if (i !== pageIndex) {
                               setDirection(i > pageIndex ? 1 : -1);
                               setPageIndex(i);
                             }
                          }}
                        >
                          <span aria-hidden="true" className={`h-2 rounded-full transition-all duration-150 ${i === pageIndex ? "w-6 bg-primary" : "w-2 bg-muted"}`} />
                        </button>
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
            {totalPages > 1 && (
              <div 
                className={`absolute inset-y-0 right-0 w-[15%] lg:w-24 xl:w-32 z-30 cursor-pointer lg:relative lg:shrink-0 flex items-center justify-end px-2 sm:px-4 lg:justify-center lg:px-0 group ${pageIndex < totalPages - 1 ? "" : "pointer-events-none"}`} 
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
                    className="flex h-11 w-11 lg:h-16 lg:w-16 items-center justify-center rounded-full bg-surface neo-shadow text-primary font-bold hover:scale-105 transition-all cursor-pointer"
                  >
                    <CaretRight className="w-5 h-5 lg:w-8 lg:h-8" weight="bold" />
                  </button>
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        /* Scroll view mode */
        <ScrollView signedPages={signedPages} onImageClick={(url) => setFullscreenImage(url)} />
      )}
    </div>
  );
}
