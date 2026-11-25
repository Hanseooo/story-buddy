"use client";

/* eslint-disable @next/next/no-img-element */

import { use, useEffect, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence, useScroll, useReducedMotion } from "framer-motion";
import { useJob } from "@/lib/useJob";
import { displayTitle } from "@/lib/displayTitle";
import FailureScreen, { resetFailChain } from "@/components/FailureScreen";
import StoppedStory from "@/components/StoppedStory";
import { signPaths } from "@/lib/signedUrls";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import { useParams } from "next/navigation";
import { CaretLeft, CaretRight, BookOpen, Rows, ArrowLeft, DownloadSimple } from "@phosphor-icons/react";

// Generated pictures are 1024x768 (backend `providers.GENERATED_IMAGE_SIZE`), so a 4:3 box holds
// their place before they load.
function ScrollImage({ src, alt, label, broken, onClick, onError, onRetry }: {
  src: string; alt: string; label: string; broken: boolean;
  onClick: (opener: HTMLElement) => void; onError: () => void; onRetry: () => void;
}) {
  const [isLoaded, setIsLoaded] = useState(false);
  if (broken) {
    return (
      <div role="alert" className="flex w-full aspect-[4/3] max-h-[50vh] md:max-h-none flex-col items-center justify-center gap-2 rounded-xl bg-muted/30 p-4 text-center font-kid">
        <p>We couldn&apos;t load this picture right now.</p>
        <button type="button" onClick={() => { setIsLoaded(false); onRetry(); }} className={`${kidControl} bg-surface text-foreground`}>
          Try loading this picture again
        </button>
      </div>
    );
  }
  return (
    <button
      type="button"
      aria-label={label}
      onClick={(event) => onClick(event.currentTarget)}
      className="relative w-full aspect-[4/3] max-h-[50vh] md:max-h-none flex items-center justify-center rounded-xl cursor-zoom-in focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
    >
      {!isLoaded && <div className="absolute inset-0 bg-muted/30 animate-pulse rounded-xl" />}
      <motion.img
         src={src}
         alt={alt}
         initial={{ opacity: 0 }}
         animate={{ opacity: isLoaded ? 1 : 0 }}
         transition={{ duration: 0.6, ease: "easeOut" }}
         onLoad={() => setIsLoaded(true)}
         onError={onError}
         loading="lazy"
         decoding="async"
         className="absolute inset-0 h-full w-full object-contain rounded-xl z-10"
      />
    </button>
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

function ScrollView({ signedPages, broken, onImageClick, onImageError, onRetry }: {
  signedPages: SignedPage[]; broken: Record<string, boolean>;
  onImageClick: (url: string, page: number, opener: HTMLElement) => void;
  onImageError: (path: string) => void; onRetry: (path: string) => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ container: scrollRef });

  return (
    <div ref={scrollRef} className="flex-1 w-full h-full overflow-y-auto overflow-x-hidden pt-4 pb-20 px-4 md:px-8 relative z-20 custom-scrollbar">
      <motion.div 
        className="fixed top-0 left-0 right-0 h-[3px] bg-primary z-50 origin-left"
        style={{ scaleX: scrollYProgress }}
      />
      <div className="flex flex-col gap-8 md:gap-16 max-w-5xl mx-auto">
        {signedPages.map((page, index) => (
          <motion.div
            key={page.scene_id}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            className="flex flex-col md:flex-row bg-surface neo-shadow rounded-3xl overflow-hidden border border-muted"
          >
            <div className="w-full md:w-1/2 flex-shrink-0 bg-muted/20 p-4 md:p-8 border-b md:border-b-0 md:border-r border-muted flex items-center justify-center">
               <ScrollImage src={page.signedUrl} alt={page.caption} label={`Show the picture for page ${index + 1} bigger`}
                 broken={Boolean(broken[page.image_path])}
                 onClick={(opener) => onImageClick(page.signedUrl, index + 1, opener)}
                 onError={() => onImageError(page.image_path)} onRetry={() => onRetry(page.image_path)} />
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
        className="m-auto max-w-[min(28rem,calc(100%-2rem))] rounded-2xl bg-background p-6 font-kid text-foreground backdrop:bg-foreground/50">
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

type PencilUse = { use_id: string; scene_id: string; state: string; text: string; before_path: string; after_path: string | null };
type PencilStatus = { pencils_left: number; disabled_reason: string | null; uses: PencilUse[] };
const MAX_PENCIL_CHARS = 200;   // Mirrors backend `app.config.MAX_PENCIL_CHARS`.
const PENCIL_ACTIVE = ["drawing", "held", "choice", "error"];   // Mirrors backend `app.page_pencil.ACTIVE_STATES`.
const PENCIL_DISABLED: Record<string, string> = {
  no_pencils: "No pencils left for this book",
  image_budget: "This book can't have any more new pictures",
};
const kidControl = "min-h-11 rounded-xl px-4 py-2 font-kid text-sm font-bold focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:cursor-not-allowed disabled:opacity-50";

async function pencilPost(path: string, body: object) {
  const { data: { session } } = await supabase.auth.getSession();
  return fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    method: "POST", body: JSON.stringify(body),
    headers: { Authorization: `Bearer ${session?.access_token}`, "Content-Type": "application/json" },
  });
}

// ADR-082 / magic-pencil 10 (US-04): the child's words change this page's current picture once. The
// edit runs server-side, so a closed tab still completes, and the result waits for "Keep this" or
// "Use the old one". A request carries its id and source picture, so a retry spends once (SH-08).
function PagePencil({ jobId, pageNumber, page, status, reviewed, busy, onBusy, onChanged }: {
  jobId: string; pageNumber: number; page: SignedPage; status: PencilStatus; reviewed: boolean; busy: boolean;
  onBusy: (busy: boolean) => void; onChanged: () => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState("");
  const [afterUrl, setAfterUrl] = useState<string | null>(null);
  const [afterState, setAfterState] = useState<"loading" | "loaded" | "error">("loading");
  const [afterAttempt, setAfterAttempt] = useState(0);
  const openerRef = useRef<HTMLButtonElement | null>(null);
  const boxRef = useRef<HTMLTextAreaElement | null>(null);
  const confirmRef = useRef<HTMLDialogElement | null>(null);
  const confirmButtonRef = useRef<HTMLButtonElement | null>(null);
  const requestId = useRef<string | null>(null);
  const formId = `page-pencil-${page.scene_id}`;
  const latest = status.uses.at(-1);
  const active = status.uses.find((u) => PENCIL_ACTIVE.includes(u.state));
  const mine = active?.scene_id === page.scene_id ? active
    : !active && latest?.scene_id === page.scene_id && ["refused", "stopped", "stale"].includes(latest.state) ? latest : undefined;
  const reason = status.disabled_reason ? PENCIL_DISABLED[status.disabled_reason] ?? PENCIL_DISABLED.no_pencils : null;
  const choiceUse = mine?.state === "choice" ? mine.use_id : null;

  useEffect(() => { if (open) boxRef.current?.focus(); }, [open]);

  // The result is not a page yet, so the API serves it by its own asset id to the author only.
  useEffect(() => {
    if (!choiceUse) return;
    const controller = new AbortController();
    let created: string | null = null;
    void (async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/images/page-pencil-${choiceUse}`,
          { headers: { Authorization: `Bearer ${session?.access_token}` }, cache: "no-store", signal: controller.signal });
        if (!response.ok) throw new Error("image_unavailable");
        const blob = await response.blob();
        if (controller.signal.aborted) return;
        created = URL.createObjectURL(blob);
        setAfterUrl(created);
        setAfterState("loading");
      } catch {
        if (!controller.signal.aborted) setAfterState("error");
      }
    })();
    return () => { controller.abort(); if (created) URL.revokeObjectURL(created); };
  }, [choiceUse, jobId, afterAttempt]);

  function close() {
    setOpen(false);
    setMessage("");
    openerRef.current?.focus();
  }

  async function send(body: { request_id: string; text: string; source: string }) {
    setSending(true);
    onBusy(true);
    setMessage("");
    try {
      const response = await pencilPost(`/jobs/${jobId}/pages/${encodeURIComponent(page.scene_id)}/pencil`, body);
      if (response.status === 409) {
        const { detail } = await response.json().catch(() => ({ detail: "" }));
        requestId.current = null;
        await onChanged();
        setMessage(PENCIL_DISABLED[detail] ?? (detail === "pencil_in_progress"
          ? "Another change is still going on this book. Try again soon." : "This page changed. Have another look."));
        return;
      }
      if (!response.ok) throw new Error("pencil_unavailable");
      requestId.current = null;
      setText("");
      setOpen(false);
      await onChanged();
      openerRef.current?.focus();
    } catch {
      setMessage("We couldn't check your words right now. Try again.");   // a retry sends the same request id
    } finally {
      setSending(false);
      onBusy(false);
    }
  }

  function submit() {
    const words = text.trim();
    if (!words || sending) return;
    requestId.current ??= crypto.randomUUID();
    void send({ request_id: requestId.current, text: words, source: page.image_path });
  }

  async function decide(choice: "kept" | "old") {
    confirmRef.current?.close();
    if (!mine?.after_path) return;
    onBusy(true);
    setMessage("");
    try {
      const response = await pencilPost(`/jobs/${jobId}/pages/${encodeURIComponent(page.scene_id)}/pencil/choice`,
        { use_id: mine.use_id, choice, source: mine.after_path });
      if (response.status === 409) {
        await onChanged();
        setMessage("This page changed. Have another look.");
        return;
      }
      if (!response.ok) throw new Error("choice_unavailable");
      await onChanged();
      openerRef.current?.focus();
    } catch {
      setMessage("We couldn't change this picture right now. Try again.");
    } finally {
      onBusy(false);
    }
  }

  function keep() {
    if (!reviewed) { void decide("kept"); return; }
    confirmRef.current?.showModal();
    confirmButtonRef.current?.focus();
  }

  return (
    <div className="mt-4 w-full">
      <div className="flex flex-wrap items-center gap-3">
        <button
          ref={openerRef}
          type="button"
          aria-label={`Magic pencil for page ${pageNumber}`}
          aria-expanded={open}
          aria-controls={formId}
          aria-describedby={`${formId}-left`}
          disabled={!!reason || !!active || (busy && !open)}
          onClick={() => { setMessage(""); setOpen((value) => !value); }}
          className={`${kidControl} border border-primary/20 bg-background text-foreground hover:bg-primary/5`}
        >
          Magic pencil
        </button>
        <span id={`${formId}-left`} className="font-kid text-sm text-foreground/70">
          {reason ?? `${status.pencils_left} magic ${status.pencils_left === 1 ? "pencil" : "pencils"} left`}
        </span>
      </div>
      {open && (
        <form
          id={formId}
          aria-label={`Magic pencil for page ${pageNumber}`}
          className="mt-3 w-full rounded-2xl bg-primary/5 p-4 text-left"
          onSubmit={(event) => { event.preventDefault(); submit(); }}
          onKeyDown={(event) => {
            if (event.key !== "Escape" || sending) return;
            event.stopPropagation();
            close();
          }}
        >
          <label htmlFor={`${formId}-text`} className="block font-kid font-bold">What should change on page {pageNumber}?</label>
          <textarea
            id={`${formId}-text`}
            ref={boxRef}
            value={text}
            maxLength={MAX_PENCIL_CHARS}
            rows={3}
            disabled={sending}
            aria-describedby={`${formId}-count`}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key !== "Enter" || event.shiftKey) return;
              event.preventDefault();
              submit();
            }}
            className="mt-2 w-full rounded-xl border border-primary/20 bg-background p-3 font-kid text-foreground focus-visible:outline-secondary focus-visible:outline-3"
          />
          <p id={`${formId}-count`} className="font-kid text-xs text-foreground/70">{text.length}/{MAX_PENCIL_CHARS}</p>
          {sending && <p role="status" className="font-kid text-sm">Checking your words…</p>}
          {message && <p role="alert" className="mt-2 font-kid text-sm">{message}</p>}
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="submit" disabled={!text.trim() || sending} aria-label={`Change page ${pageNumber} with the magic pencil`}
              className={`${kidControl} bg-primary text-on-primary`}>
              Change my picture
            </button>
            <button type="button" disabled={sending} onClick={close} aria-label={`Close the magic pencil for page ${pageNumber}`}
              className={`${kidControl} text-foreground`}>
              Cancel
            </button>
          </div>
        </form>
      )}
      {!open && message && <p role="alert" className="mt-2 font-kid text-sm">{message}</p>}
      {mine?.state === "drawing" && <p role="status" className="mt-2 font-kid text-sm">Changing your picture…</p>}
      {mine?.state === "held" && <p role="status" className="mt-2 font-kid text-sm">Your teacher is taking a look</p>}
      {mine?.state === "refused" && <p role="status" className="mt-2 font-kid text-sm">We couldn&apos;t change this picture. Try different words.</p>}
      {mine?.state === "stopped" && <p role="status" className="mt-2 font-kid text-sm">This change can&apos;t be made. Your page stays as it is.</p>}
      {mine?.state === "stale" && <p role="status" className="mt-2 font-kid text-sm">This page changed. Have another look.</p>}
      {mine?.state === "error" && (
        <div role="alert" className="mt-2 flex flex-col items-start gap-2 font-kid text-sm">
          <p>We couldn&apos;t change this picture right now.</p>
          <button type="button" disabled={busy} className={`${kidControl} bg-surface`}
            onClick={() => void send({ request_id: mine.use_id, text: mine.text, source: mine.before_path })}>
            Try changing page {pageNumber} again
          </button>
        </div>
      )}
      {mine?.state === "choice" && (
        <div role="group" aria-label={`Your changed picture for page ${pageNumber}`} className="mt-3 w-full rounded-2xl bg-primary/5 p-4 text-left">
          {afterState === "error" ? (
            <div role="alert" className="flex flex-col items-start gap-2 font-kid text-sm">
              <p>We couldn&apos;t load this picture right now.</p>
              <button type="button" className={`${kidControl} bg-surface`}
                onClick={() => { setAfterState("loading"); setAfterAttempt((value) => value + 1); }}>
                Try loading the changed picture for page {pageNumber} again
              </button>
            </div>
          ) : afterUrl && (
            <img
              src={afterUrl}
              alt={`Your changed picture for page ${pageNumber}`}
              className="aspect-square w-full max-w-xs rounded-lg bg-muted object-contain"
              onLoad={() => setAfterState("loaded")}
              onError={() => setAfterState("error")}
            />
          )}
          {afterState === "loading" && <p role="status" className="font-kid text-sm">Loading your changed picture…</p>}
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" disabled={busy || afterState !== "loaded"} onClick={keep}
              aria-label={`Keep this picture for page ${pageNumber}`} className={`${kidControl} bg-primary text-on-primary`}>
              Keep this
            </button>
            <button type="button" disabled={busy} onClick={() => void decide("old")}
              aria-label={`Use the old picture for page ${pageNumber}`} className={`${kidControl} text-foreground`}>
              Use the old one
            </button>
          </div>
        </div>
      )}
      <dialog ref={confirmRef} aria-labelledby={`${formId}-confirm`} onCancel={(event) => { event.preventDefault(); confirmRef.current?.close(); }}
        className="m-auto max-w-[min(28rem,calc(100%-2rem))] rounded-2xl bg-background p-6 font-kid text-foreground backdrop:bg-foreground/50">
        <h2 id={`${formId}-confirm`} className="text-xl font-bold">Your teacher will look at your book again before classmates can see it.</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          <button type="button" ref={confirmButtonRef} onClick={() => void decide("kept")} className={`${kidControl} bg-primary text-on-primary`}>
            Change page {pageNumber}
          </button>
          <button type="button" onClick={() => confirmRef.current?.close()} className={`${kidControl} text-foreground`}>
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
  const [fullscreen, setFullscreen] = useState<{ url: string; page: number } | null>(null);
  const fullscreenRef = useRef<HTMLDialogElement | null>(null);
  const fullscreenOpener = useRef<HTMLElement | null>(null);
  const [brokenPictures, setBrokenPictures] = useState<Record<string, boolean>>({});   // by image_path
  const reduceMotion = useReducedMotion();
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState("");
  const [changingPage, setChangingPage] = useState(false); // SH-07: one page change per book at a time
  const downloadRequest = useRef<AbortController | null>(null);
  const imageRequest = useRef<AbortController | null>(null);
  // Page URLs collected for the current imageRequest. Blobs here die with that controller, so a new
  // controller starts empty (image-loading AC-13, AC-15).
  const collectedUrls = useRef<Record<string, string>>({});
  const ownsBook = Boolean(profileId && row?.profile_id === profileId);
  // RLS supplies readable classroom books; the PDF endpoint rechecks active membership/approval.
  const canDownload = Boolean(profileId && row?.approved_at) && !row?.rejected_at;
  const showDownload = ownsBook || canDownload;

  useEffect(() => () => downloadRequest.current?.abort(), [jobId, canDownload]);

  // Magic pencil 10: only the author of a finished feature book gets the page pencil. Any failure
  // hides it, so the book itself always stays readable.
  const [pencil, setPencil] = useState<PencilStatus | null>(null);
  const pencilBook = ownsBook && bucket === "terminal-success" && row?.moderation_mode === "teacher_review_v1";
  const [pencilTick, setPencilTick] = useState(0);
  useEffect(() => {
    if (!pencilBook) return;
    const controller = new AbortController();
    void (async () => {
      let status: PencilStatus | null = null;
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/pages/pencil`,
          { headers: { Authorization: `Bearer ${session?.access_token}` }, cache: "no-store", signal: controller.signal });
        if (response.ok) status = await response.json();
      } catch { /* hidden below */ }
      if (!controller.signal.aborted) setPencil(status);
    })();
    return () => controller.abort();
  }, [pencilBook, jobId, pencilTick]);
  // A closed tab still completes, so an open one only polls while the edit or the teacher is working.
  const pencilWait = pencil?.uses.some((u) => u.state === "drawing") ? 2500
    : pencil?.uses.some((u) => u.state === "held") ? 15000 : null;
  useEffect(() => {
    if (!pencilBook || !pencilWait) return;
    const timer = window.setTimeout(() => setPencilTick((tick) => tick + 1), pencilWait);
    return () => window.clearTimeout(timer);
  }, [pencilBook, pencilWait, pencil]);
  const pencilActive = Boolean(pencil?.uses.some((u) => PENCIL_ACTIVE.includes(u.state)));   // SH-07
  const pencilChanged = useCallback(async () => {
    await refetch();
    setPencilTick((tick) => tick + 1);
  }, [refetch]);

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
    const signed = collectedUrls.current;
    async function doSign(att: number): Promise<void> {
      // Only pages still missing are fetched again; the book still needs every page (SH-05).
      const missing = paths.filter(p => !signed[p]);
      const got = await signPaths(missing, [{id: jobId, moderation_mode: row?.moderation_mode, pages: pagesList}], controller?.signal);
      if (controller?.signal.aborted) return;
      Object.assign(signed, got);
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
    collectedUrls.current = {};
    signPages(1);
    return () => { controller.abort(); };
  }, [bucket, signPages]);

  // A picture whose link broke (an expired link, a dropped connection) goes back through the same
  // re-sign as the whole book: dropping its URL makes it the only missing path (SH-05).
  function markBroken(path: string) {
    setBrokenPictures(b => ({ ...b, [path]: true }));
  }

  function retryPicture(path: string) {
    delete collectedUrls.current[path];
    setBrokenPictures(b => ({ ...b, [path]: false }));
    void signPages(1);
  }

  function openFullscreen(url: string, page: number, opener: HTMLElement) {
    fullscreenOpener.current = opener;
    setFullscreen({ url, page });
    fullscreenRef.current?.showModal();
  }

  function closeFullscreen() {
    fullscreenRef.current?.close();
    setFullscreen(null);
    fullscreenOpener.current?.focus();
  }

  // Arrow key navigation. Up/Down stay with scrolling, and a key meant for a field, a dialog or
  // the big picture never turns the page (that would remount the pencil and lose typed words).
  useEffect(() => {
    if (!signedPages || viewMode !== "pages" || fullscreen) return;
    function onKey(e: KeyboardEvent) {
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      if (e.target instanceof Element && e.target.closest("input, textarea, select, [contenteditable], dialog")) return;
      if (e.key === "ArrowRight") {
        setHasInteracted(true);
        setDirection(1);
        setPageIndex(i => Math.min(i + 1, signedPages!.length - 1));
      }
      if (e.key === "ArrowLeft") {
        setHasInteracted(true);
        setDirection(-1);
        setPageIndex(i => Math.max(i - 1, 0));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [signedPages, viewMode, fullscreen]);

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

      {/* Big picture: a native modal dialog brings Escape, the focus trap and an inert page. */}
      <dialog
        ref={fullscreenRef}
        aria-label={fullscreen ? `Picture for page ${fullscreen.page}` : undefined}
        onCancel={(event) => { event.preventDefault(); closeFullscreen(); }}
        onClick={(event) => { if (!(event.target as Element).closest("img, button")) closeFullscreen(); }}
        className="m-0 h-dvh max-h-none w-screen max-w-none bg-transparent p-4 backdrop:bg-foreground/90 backdrop:backdrop-blur-sm md:p-8"
      >
        {fullscreen && (
          <div className="flex h-full w-full flex-col items-center justify-center gap-4">
            <button
              type="button"
              aria-label="Close the big picture"
              onClick={closeFullscreen}
              className={`${kidControl} self-end bg-surface text-foreground`}
            >
              Close
            </button>
            <motion.img
              src={fullscreen.url}
              alt={`Picture for page ${fullscreen.page}`}
              initial={reduceMotion ? { opacity: 0 } : { scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={reduceMotion ? { duration: 0.15 } : { type: "spring", bounce: 0, duration: 0.4 }}
              className="min-h-0 max-w-full flex-1 object-contain rounded-2xl neo-shadow-xl"
            />
          </div>
        )}
      </dialog>

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
            {/* Left tap zone: absolute on mobile/tablet, relative column on desktop. Below lg only the
                arrow takes taps, so the zone never covers the page's own controls; swipe covers the rest.
                The arrow stays on the first page (aria-disabled keeps it focusable) so focus never drops. */}
            {totalPages > 1 && (
              <div
                className={`absolute inset-y-0 left-0 w-[15%] lg:w-24 xl:w-32 z-30 pointer-events-none lg:relative lg:shrink-0 flex items-center justify-start px-2 sm:px-4 lg:justify-center lg:px-0 group ${pageIndex > 0 ? "lg:pointer-events-auto lg:cursor-pointer" : ""}`}
                onClick={() => {
                  setHasInteracted(true);
                  if (pageIndex > 0) {
                    setDirection(-1);
                    setPageIndex(pageIndex - 1);
                  }
                }}
              >
                <button
                  type="button"
                  data-testid="nav-prev"
                  aria-label="Previous page"
                  aria-disabled={pageIndex === 0}
                  className="pointer-events-auto flex h-11 w-11 lg:h-16 lg:w-16 items-center justify-center rounded-full bg-surface neo-shadow text-primary font-bold hover:scale-105 transition-all cursor-pointer focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 aria-disabled:opacity-40 aria-disabled:cursor-not-allowed aria-disabled:hover:scale-100"
                >
                  <CaretLeft className="w-5 h-5 lg:w-8 lg:h-8" weight="bold" aria-hidden="true" />
                </button>
              </div>
            )}

            {/* Page content with swipe */}
            <motion.div 
              className="flex-1 flex w-full h-full items-center justify-center z-20 mx-auto max-w-6xl"
              drag="x"
              dragConstraints={{ left: 0, right: 0 }}
              // Elastic 1 past zero-width constraints = the page follows the finger 1:1. The snap back
              // takes the release velocity into a critically damped spring (damping = 2·√stiffness).
              dragElastic={1}
              dragTransition={{ bounceStiffness: 300, bounceDamping: 35 }}
              onDragEnd={(e, { offset, velocity }) => {
                setHasInteracted(true);
                // A quick flick commits in its own direction; a slow drag commits past 50px.
                const turn = Math.abs(velocity.x) > 400 ? -Math.sign(velocity.x)
                  : Math.abs(offset.x) > 50 ? -Math.sign(offset.x) : 0;
                if (turn > 0 && pageIndex < totalPages - 1) {
                  setDirection(1);
                  setPageIndex(pageIndex + 1);
                }
                if (turn < 0 && pageIndex > 0) {
                  setDirection(-1);
                  setPageIndex(pageIndex - 1);
                }
              }}
            >
              {/* "wait" keeps one card in the flow, so the column never jumps between two card heights;
                  the exit is short so the next page answers quickly. */}
              <AnimatePresence mode="wait" custom={direction}>
                <motion.div
                  key={pageIndex}
                  custom={direction}
                  variants={reduceMotion ? {
                    enter: { opacity: 0 },
                    center: { opacity: 1 },
                    exit: { opacity: 0 },
                  } : {
                    enter: (dir: number) => ({ x: dir > 0 ? 40 : -40, opacity: 0, scale: 0.98 }),
                    center: { x: 0, opacity: 1, scale: 1 },
                    exit: (dir: number) => ({ x: dir < 0 ? 40 : -40, opacity: 0, scale: 0.98, transition: { duration: 0.15, ease: "easeIn" } })
                  }}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  transition={reduceMotion ? { duration: 0.15 } : { type: "spring", bounce: 0, duration: 0.4 }}
                  className="flex flex-col lg:flex-row w-full h-auto lg:max-h-[80vh] lg:min-h-[65vh] items-stretch justify-start lg:justify-center bg-surface neo-shadow rounded-3xl overflow-hidden mx-2 sm:mx-4 lg:mx-0 border border-muted"
                >
                  {/* Left side: Illustration (Massive on Desktop, contained on mobile) */}
                  <div className="relative flex items-center justify-center w-full lg:w-[60%] xl:w-[65%] bg-muted/20 p-4 lg:p-10 border-b lg:border-b-0 lg:border-r border-muted shrink-0 lg:shrink">
                    {/* A 4:3 box (generated pictures are 1024x768) holds the picture's place while it loads. */}
                    {brokenPictures[current.image_path] ? (
                      <div role="alert" className="flex w-full aspect-[4/3] max-h-[40vh] lg:max-h-[60vh] flex-col items-center justify-center gap-2 rounded-xl bg-muted/30 p-4 text-center font-kid">
                        <p>We couldn&apos;t load this picture right now.</p>
                        <button type="button" onClick={() => retryPicture(current.image_path)} className={`${kidControl} bg-surface text-foreground`}>
                          Try loading this picture again
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        aria-label={`Show the picture for page ${pageIndex + 1} bigger`}
                        onClick={(event) => openFullscreen(current.signedUrl, pageIndex + 1, event.currentTarget)}
                        className="relative block w-full aspect-[4/3] max-h-[40vh] lg:max-h-[60vh] rounded-xl cursor-zoom-in pointer-events-auto focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
                      >
                        <img
                          src={current.signedUrl}
                          alt={current.caption}
                          fetchPriority="high"
                          onLoad={() => setLoaded(l => (l[pageIndex] ? l : { ...l, [pageIndex]: true }))}
                          onError={() => markBroken(current.image_path)}
                          className="absolute inset-0 h-full w-full object-contain rounded-xl lg:neo-shadow"
                        />
                        {!loaded[pageIndex] && (
                          <span
                            aria-hidden="true"
                            className="absolute inset-0 rounded-xl bg-muted animate-pulse pointer-events-none"
                          />
                        )}
                      </button>
                    )}
                    
                    {/* Swipe Indicator (Mobile only, Page 0 only, disappears after interaction) */}
                    {pageIndex === 0 && !hasInteracted && (
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={reduceMotion ? { opacity: 1 } : { opacity: [0, 1, 1, 0], x: [0, -20, -20, -40] }}
                        transition={reduceMotion ? { duration: 0.15 } : { repeat: Infinity, duration: 2, ease: "easeInOut" }}
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
                          reviewed={Boolean(row?.approved_at || row?.rejected_at)} busy={changingPage || pencilActive}
                          onBusy={setChangingPage} onChanged={refetch} />
                      )}
                      {pencilBook && pencil && (
                        <PagePencil key={current.scene_id} jobId={jobId} pageNumber={pageIndex + 1} page={current} status={pencil}
                          reviewed={Boolean(row?.approved_at || row?.rejected_at)} busy={changingPage}
                          onBusy={setChangingPage} onChanged={pencilChanged} />
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

            {/* Right tap zone: same rules as the left one. */}
            {totalPages > 1 && (
              <div
                className={`absolute inset-y-0 right-0 w-[15%] lg:w-24 xl:w-32 z-30 pointer-events-none lg:relative lg:shrink-0 flex items-center justify-end px-2 sm:px-4 lg:justify-center lg:px-0 group ${pageIndex < totalPages - 1 ? "lg:pointer-events-auto lg:cursor-pointer" : ""}`}
                onClick={() => {
                  setHasInteracted(true);
                  if (pageIndex < totalPages - 1) {
                    setDirection(1);
                    setPageIndex(pageIndex + 1);
                  }
                }}
              >
                <button
                  type="button"
                  data-testid="nav-next"
                  aria-label="Next page"
                  aria-disabled={pageIndex === totalPages - 1}
                  className="pointer-events-auto flex h-11 w-11 lg:h-16 lg:w-16 items-center justify-center rounded-full bg-surface neo-shadow text-primary font-bold hover:scale-105 transition-all cursor-pointer focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 aria-disabled:opacity-40 aria-disabled:cursor-not-allowed aria-disabled:hover:scale-100"
                >
                  <CaretRight className="w-5 h-5 lg:w-8 lg:h-8" weight="bold" aria-hidden="true" />
                </button>
              </div>
            )}
            <p role="status" aria-live="polite" className="sr-only">{`Page ${pageIndex + 1} of ${totalPages}`}</p>
          </div>
        </>
      ) : (
        /* Scroll view mode */
        <ScrollView signedPages={signedPages} broken={brokenPictures} onImageClick={openFullscreen}
          onImageError={markBroken} onRetry={retryPicture} />
      )}
    </div>
  );
}
