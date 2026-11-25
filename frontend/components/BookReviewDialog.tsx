"use client";

import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { supabase } from "@/lib/supabaseClient";
import { Job, ReviewDecision, jobState } from "@/lib/types/jobs";
import { StateBadge } from "./BookCard";
import { Avatar } from "@/components/Avatar";
import { displayTitle } from "@/lib/displayTitle";
import { ClearanceWithdrawal } from "./NeedsHelpQueue";

type Props = {
  job: Job | null;
  pageUrls: string[];
  /** Signing the pages failed or left a page without a link. */
  pagesFailed?: boolean;
  /** Signs the pages again; the page's Try again buttons call it. */
  onRetryPages: () => void;
  notesEnabled?: boolean;
  /** Job whose note row opens on load: set when the teacher picks "Add a note" from the toast. */
  openNoteFor?: string | null;
  onDecide: (decision: ReviewDecision) => void;
  onClose: () => void;
  /** Rendered inside the modal so it stays clickable; the rest of the page is inert. */
  children?: ReactNode;
};

export default function BookReviewDialog({
  job,
  pageUrls,
  pagesFailed = false,
  onRetryPages,
  notesEnabled = false,
  openNoteFor = null,
  onDecide,
  onClose,
  children,
}: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const noteRow = useRef<HTMLDetailsElement>(null);
  const [pending, setPending] = useState(false);
  const [withdrawnJob, setWithdrawnJob] = useState<string | null>(null);
  const withdrawn = !!job && withdrawnJob === job.id;
  // Load state per page index, for this set of links only: a re-sign hands over a new array and starts fresh.
  const [pictures, setPictures] = useState<{ urls: string[]; state: Record<number, "loaded" | "failed"> }>({ urls: pageUrls, state: {} });
  const pictureState = pictures.urls === pageUrls ? pictures.state : {};
  const markPicture = (i: number, value: "loaded" | "failed") => setPictures((current) => ({
    urls: pageUrls, state: { ...(current.urls === pageUrls ? current.state : {}), [i]: value },
  }));
  const pageFailed = (i: number) => pictureState[i] === "failed" || (pagesFailed && !pageUrls[i]);
  const pageCount = job?.pages?.length ?? 0;
  const anyPageFailed = Array.from({ length: pageCount }, (_, i) => pageFailed(i)).some(Boolean);
  const allPagesLoaded = Array.from({ length: pageCount }, (_, i) => pictureState[i] === "loaded").every(Boolean);

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
      aria-labelledby="book-review-name book-review-title"
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
        <div className="bg-surface w-full max-w-3xl mx-4 sm:mx-auto rounded-2xl flex flex-col max-h-[95dvh] shadow-[0_22px_60px_rgb(49_85_217/16%)] overflow-hidden">
          {/* Header */}
          {/* min-w-0 lets the text block shrink so Close is never pushed out at 360px.
              Below sm the badge drops to a second row under the name (avatar 36px + gap 12px
              = ml-12); from sm it sits between the text and Close. */}
          <div className="px-6 py-4 border-b border-primary/10 grid grid-cols-[minmax(0,1fr)_auto] sm:grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-x-3 gap-y-1 shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <Avatar avatarId={job?.profiles?.avatar_id ?? null} displayNickname={name} size={36} />
              <div className="min-w-0">
                <p id="book-review-name" className="font-bold text-foreground truncate">{name}</p>
                <p id="book-review-title" className="text-sm text-foreground/70 truncate max-w-[24ch]">
                  {displayTitle(job.title, job.input_text)}
                </p>
                <p className="text-xs text-foreground/50">
                  {new Date(job.created_at).toLocaleDateString(undefined, {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                  })}
                </p>
              </div>
            </div>
            <StateBadge state={state} className="row-start-2 col-start-1 justify-self-start ml-12 sm:row-start-1 sm:col-start-2 sm:ml-0" />
            <button
              onClick={onClose}
              className="row-start-1 col-start-2 sm:col-start-3 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-xl hover:bg-muted transition-colors text-foreground/60 font-bold text-xl"
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          {/* Pages */}
          <div className="flex-1 overflow-y-auto px-4 sm:px-8 py-6 space-y-8 bg-background/30">
            {!withdrawn && pageUrls.length === 0 && !pagesFailed && (
              <div className="py-12 text-center text-foreground/40 text-sm">
                Loading pages…
              </div>
            )}
            {!withdrawn && job.pages?.map((page, i) => (
              <div
                key={page.scene_id}
                className="bg-surface rounded-2xl overflow-hidden border border-primary/10 shadow-[0_6px_18px_rgb(49_85_217/10%)]"
              >
                {pageFailed(i) ? (
                  <div className="w-full aspect-[4/3] bg-muted flex flex-col items-center justify-center gap-2 p-4 text-center text-sm text-foreground/70">
                    <p>This page&apos;s picture didn&apos;t load.</p>
                    <button
                      onClick={onRetryPages}
                      aria-label={`Try loading page ${i + 1} again`}
                      className="min-h-[44px] px-4 py-2 rounded-xl border border-primary/20 bg-surface font-bold text-foreground hover:bg-muted transition-colors"
                    >
                      Try again
                    </button>
                  </div>
                ) : pageUrls[i] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={pageUrls[i]}
                    alt={page.caption}
                    onLoad={() => markPicture(i, "loaded")}
                    onError={() => markPicture(i, "failed")}
                    // A 15-page book is ~20 MB of full-res PNG. This is a scroll
                    // container, so lazy means the teacher pays for the pages they
                    // actually scroll to, not the whole book on open.
                    loading={i === 0 ? "eager" : "lazy"}
                    decoding="async"
                    // Whole picture, never cropped: the teacher approves what the class
                    // will see. Generated pictures are 1024x768 (4:3).
                    className="w-full aspect-[4/3] object-contain bg-muted"
                  />
                ) : (
                  <div className="w-full aspect-[4/3] bg-muted animate-pulse" />
                )}
                <p className="font-kid text-lg leading-relaxed px-6 py-5 text-center text-foreground">
                  {page.caption}
                </p>
              </div>
            ))}
            {job.moderation_mode === "teacher_review_v1" && <ClearanceWithdrawal key={job.id}
              jobId={job.id} onPending={setPending} onWithdrawn={() => setWithdrawnJob(job.id)} />}
            {!withdrawn && notesEnabled && job.status === "complete" && (
              <TeacherNoteRow key={job.id} jobId={job.id} name={name} detailsRef={noteRow}
                openOnMount={openNoteFor === job.id} />
            )}
          </div>

          {/* Decision footer — fixed at bottom, thumb-reachable */}
          {!withdrawn && <fieldset disabled={pending} className="px-6 py-4 border-t border-primary/10 bg-surface shrink-0 space-y-3">
            <p id="book-sharing-note" className="text-sm leading-relaxed text-foreground/75">
              Classmates will be able to read and download this book. Copies already saved remain
              after approval is withdrawn or the book is deleted.
            </p>
            {state !== "approved" && anyPageFailed && (
              <div role="alert" className="flex flex-wrap items-center gap-3 text-sm font-bold text-destructive">
                <p>A page didn&apos;t load, so you can&apos;t share yet.</p>
                <button
                  onClick={onRetryPages}
                  className="min-h-[44px] px-4 py-2 rounded-xl border border-primary/20 text-foreground hover:bg-muted transition-colors"
                >
                  Try again
                </button>
              </div>
            )}
            {state !== "approved" && !anyPageFailed && !allPagesLoaded && (
              <p id="book-share-waiting" className="text-sm text-foreground/75">
                Pages are still loading. Scroll through the book to load every page.
              </p>
            )}
            <div className="flex flex-wrap gap-3 justify-end">
              {state !== "rejected" && state !== "pending" ? null : (
                <button
                  onClick={() => onDecide("rejected")}
                  className="min-h-[44px] px-6 py-2 rounded-xl border border-destructive text-destructive font-bold text-sm hover:bg-destructive/10 transition-colors"
                >
                  Not ready to share yet
                </button>
              )}
              {state !== "approved" ? (
                <button
                  onClick={() => onDecide("approved")}
                  disabled={anyPageFailed || !allPagesLoaded}
                  aria-describedby={!anyPageFailed && !allPagesLoaded ? "book-sharing-note book-share-waiting" : "book-sharing-note"}
                  className="min-h-[44px] px-8 py-2 rounded-xl bg-primary text-on-primary font-bold text-sm hover:bg-primary-deep transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary"
                >
                  Share with class
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
          </fieldset>}
        </div>
      )}
      {children}
    </dialog>
  );
}

// Mirrors MAX_REVIEW_NOTE_CHARS in backend/app/config.py; the endpoint still enforces it.
const MAX_NOTE_CHARS = 500;

function TeacherNoteRow({ jobId, name, detailsRef, openOnMount }: {
  jobId: string;
  name: string;
  detailsRef: RefObject<HTMLDetailsElement | null>;
  openOnMount: boolean;
}) {
  const [body, setBody] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [loadFailed, setLoadFailed] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const box = useRef<HTMLTextAreaElement>(null);
  const endpoint = `${process.env.NEXT_PUBLIC_API_BASE_URL}/teacher/jobs/${jobId}/note`;

  useEffect(() => {
    if (openOnMount && detailsRef.current) detailsRef.current.open = true;
  }, [openOnMount, detailsRef]);

  useEffect(() => {
    if (!loading && detailsRef.current?.open && (editing || sent === null)) box.current?.focus();
  }, [loading, editing, sent, detailsRef]);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      setLoading(true);
      setLoadFailed(false);
      try {
        const { data: { session } } = await supabase.auth.getSession();
        const response = await fetch(endpoint, {
          headers: { Authorization: `Bearer ${session?.access_token}` },
          cache: "no-store", signal: controller.signal,
        });
        if (response.status !== 404) {
          if (!response.ok) throw new Error("load failed");
          const note: { body: string } = await response.json();
          if (!controller.signal.aborted) { setSent(note.body); setBody(note.body); }
        }
      } catch {
        if (!controller.signal.aborted) setLoadFailed(true);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [endpoint, loadAttempt]);

  async function save(method: "PUT" | "DELETE") {
    if (loading || saving || loadFailed) return;
    setSaving(true);
    setError(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const response = await fetch(endpoint, {
        method, headers: { Authorization: `Bearer ${session?.access_token}`, "Content-Type": "application/json" },
        ...(method === "PUT" ? { body: JSON.stringify({ body }) } : {}),
      });
      if (!response.ok) {
        if (response.status === 409 && (await response.json()).detail === "notes_disabled") {
          setError("Notes are turned off for this class. Your text is kept.");
        } else if (response.status === 422) {
          setError(`Write a note with 1–${MAX_NOTE_CHARS} characters, including something other than spaces.`);
        } else {
          setError(method === "DELETE" ? "Could not delete the note. Try again." : "Could not save the note. Your text is kept. Try again.");
        }
        return;
      }
      const note: { body: string } | null = method === "PUT" ? await response.json() : null;
      setSent(note?.body ?? null);
      setBody(note?.body ?? "");
      setEditing(false);
    } catch {
      setError(method === "DELETE" ? "Could not delete the note. Try again." : "Could not save the note. Your text is kept. Try again.");
    } finally {
      setSaving(false);
    }
  }

  const actionClass = "min-h-[44px] px-4 py-2 rounded-xl border border-primary/20 font-bold text-sm hover:bg-muted disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-primary";
  return (
    <details ref={detailsRef} className="rounded-xl border border-primary/15 bg-surface px-4">
      <summary className="min-h-[44px] py-3 cursor-pointer font-bold text-sm focus-visible:outline-2 focus-visible:outline-primary">
        Add a note for {name}
      </summary>
      <div className="pb-4 space-y-3">
        <p aria-live="polite" className="text-sm text-destructive">{error}</p>
        {loading && <p role="status" className="text-sm text-foreground/70">Loading note…</p>}
        {loadFailed && <p aria-live="polite" className="text-sm text-destructive">
          Could not load the note. <button className={actionClass} onClick={() => setLoadAttempt(n => n + 1)}>Try loading note again</button>
        </p>}
        {sent !== null && !editing ? <>
          <p role="status" className="text-sm text-success">Note sent</p>
          <p className="whitespace-pre-wrap break-words text-sm">{sent}</p>
          <div className="flex flex-wrap gap-2">
            <button className={actionClass} disabled={saving} aria-label={`Edit note for ${name}`} onClick={() => {
              setEditing(true);
            }}>Edit</button>
            <button className={actionClass} disabled={saving} aria-label={`Delete note for ${name}`} onClick={() => void save("DELETE")}>{saving ? "Deleting…" : "Delete"}</button>
          </div>
        </> : <form onSubmit={e => { e.preventDefault(); if (body.trim()) void save("PUT"); }} className="space-y-3">
          <label className="block text-sm font-bold">
            Note for {name}
            <textarea ref={box} value={body} onChange={e => setBody(e.target.value)} disabled={loading || saving || loadFailed}
              placeholder="Something kind and specific…" rows={3} maxLength={MAX_NOTE_CHARS}
              className="mt-2 block w-full rounded-xl border border-primary/20 bg-background p-3 font-normal focus-visible:outline-2 focus-visible:outline-primary disabled:opacity-50" />
          </label>
          <p className="text-sm text-foreground/70">{name} will be able to read this note.</p>
          <div className="flex flex-wrap gap-2">
            <button type="submit" className={actionClass} disabled={loading || saving || loadFailed || !body.trim()} aria-label={`Send note for ${name}`}>{saving ? "Sending…" : "Send"}</button>
            {editing && <button type="button" className={actionClass} disabled={saving} onClick={() => { setBody(sent ?? ""); setEditing(false); }}>Cancel edit</button>}
          </div>
        </form>}
      </div>
    </details>
  );
}
