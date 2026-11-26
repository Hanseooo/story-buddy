"use client";

/* eslint-disable @next/next/no-img-element */

import { use, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useJob, type JobRow } from "@/lib/useJob";
import { displayTitle } from "@/lib/displayTitle";
import FailureScreen from "@/components/FailureScreen";
import StopStory from "@/components/StopStory";
import StoppedStory from "@/components/StoppedStory";
import PictureBox from "@/components/PictureBox";
import OldNewPictures from "@/components/OldNewPictures";
import { supabase } from "@/lib/supabaseClient";
import { forgetSignedUrls, signPaths } from "@/lib/signedUrls";
import { motion, AnimatePresence, useReducedMotion } from "framer-motion";
import { BookOpen, Users, PaintBrush, MagicWand, Check, MagnifyingGlass } from "@phosphor-icons/react";

// ponytail: 90s is chosen so the line arrives before a child gives up; will fire on slow image calls
const STALL_MS = 90_000;

// Swept-pause synthetic status — replace with real value when data-deletion names it (spec §4.4.4)
const SWEPT_STATUS = "__swept__";

type StepperStep = 1 | 2 | 3 | 4;
type SelectedTrait = { charId: string; attribute: string } | null;
type SubmissionState = "idle" | "sending" | "reconciling" | "unknown";
type CharacterImageState = "signing" | "loading" | "loaded" | "error";

function getStep(stage: string | null): StepperStep | null {
  if (!stage) return null;
  if (["queued", "input_gate", "analyze", "segment"].some(p => stage.startsWith(p))) return 1;
  if (["char_bible", "char_ref_mod", "reveal"].some(p => stage.startsWith(p))) return 2;
  if (["generate_scene", "consistency_check", "regenerate", "output_mod"].some(p => stage.startsWith(p))) return 3;
  if (stage.startsWith("compose")) return 4;
  return null;
}

// The worker writes "<node>:{done + 1}/{n}" during the scene nodes (run_job._stage_string).
function getPictureCount(stage: string | null): { m: number; n: number } | null {
  const m = (stage ?? "").match(/:(\d+)\/(\d+)$/);
  return m ? { m: Number(m[1]), n: Number(m[2]) } : null;
}

function getStepLabel(step: StepperStep, stage: string | null): string {
  if (step === 3) {
    const count = getPictureCount(stage);
    if (count) return `Drawing picture ${count.m} of ${count.n}`;
    return "Drawing your pictures";
  }
  return [
    "Reading your story",
    "Meeting your characters",
    "Drawing your pictures",
    "Putting your book together",
  ][step - 1];
}

function KineticText({ text, className }: { text: string; className?: string }) {
  const words = text.split(" ");
  return (
    <div className={className + " flex flex-wrap justify-center gap-[0.25em]"}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true" className="flex flex-wrap justify-center gap-[0.25em]">
        {words.map((word, i) => (
          <span key={i} className="flex">
            {Array.from(word).map((letter, j) => (
              <motion.span
                key={j}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  type: "spring",
                  bounce: 0,
                  delay: (i * 5 + j) * 0.04,
                }}
                className="inline-block"
              >
                {letter}
              </motion.span>
            ))}
          </span>
        ))}
      </span>
    </div>
  );
}

const ReadingVignette = () => {
  const reduce = useReducedMotion();
  return (
  <div className="relative flex flex-col justify-center items-center h-32 w-48 my-4">
    <div className="w-full p-5 bg-[var(--color-surface)] border border-[var(--color-primary)]/20 rounded-[20px] shadow-[0_10px_28px_rgba(49,85,217,0.12)] flex flex-col gap-3 relative overflow-hidden">
      <div className="w-full h-3 bg-[var(--color-muted)] rounded-full opacity-60" />
      <div className="w-5/6 h-3 bg-[var(--color-muted)] rounded-full opacity-60" />
      <div className="w-4/6 h-3 bg-[var(--color-muted)] rounded-full opacity-60" />
    </div>
    <motion.div
      className="absolute z-10 text-[var(--color-primary)] drop-shadow-md"
      animate={reduce ? undefined : { x: [-40, 40, -40], y: [-10, 10, -10] }}
      transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
    >
      <MagnifyingGlass size={48} weight="duotone" />
    </motion.div>
  </div>
  );
};

const CharactersVignette = () => {
  const reduce = useReducedMotion();
  return (
  <div className="relative w-48 h-32 my-4 flex items-center justify-center">
    {[
      { rotate: -15, x: -30, delay: 0 },
      { rotate: 0, x: 0, delay: 0.15 },
      { rotate: 15, x: 30, delay: 0.3 }
    ].map((card, i) => (
      <motion.div
        key={i}
        className="absolute w-12 h-16"
        initial={{ y: 20, opacity: 0, rotate: 0, x: 0 }}
        animate={{ y: 0, opacity: 1, rotate: card.rotate, x: card.x }}
        transition={{ 
          y: { type: "spring", bounce: 0, delay: card.delay },
          opacity: { duration: 0.4, delay: card.delay },
          rotate: { type: "spring", bounce: 0, delay: card.delay },
          x: { type: "spring", bounce: 0, delay: card.delay }
        }}
        style={{ zIndex: i }}
      >
        <motion.div
          className="w-full h-full bg-[var(--color-surface)] border border-[var(--color-primary)]/20 rounded-[12px] shadow-[0_10px_28px_rgba(49,85,217,0.12)] flex items-center justify-center"
          animate={reduce ? undefined : { y: [-4, 4, -4], rotate: [-2, 2, -2] }}
          transition={{ repeat: Infinity, duration: 3, delay: i * 0.5, ease: "easeInOut" }}
        >
          <motion.div 
            className="w-6 h-6 rounded-full bg-[var(--color-primary)]/10"
            animate={reduce ? undefined : { scale: [0.85, 1.15, 0.85], opacity: [0.4, 1, 0.4] }}
            transition={{ repeat: Infinity, duration: 2, delay: card.delay, ease: "easeInOut" }}
          />
        </motion.div>
      </motion.div>
    ))}
  </div>
  );
};

// `count` is the stage's picture m of n; null when the stage carries none (a redraw, or a scene
// node before scenes exist), and the bar then claims no amount at all.
const DrawingVignette = ({ count }: { count: { m: number; n: number } | null }) => {
  const reduce = useReducedMotion();
  const finished = count ? Math.min(count.m - 1, count.n) : null;
  return (
  <div className="relative w-48 h-32 flex flex-col items-center justify-center my-4">
    <motion.div
      className="absolute top-0 z-10 text-[var(--color-primary)] origin-bottom drop-shadow-md"
      animate={reduce ? undefined : { x: [-40, 40, -40], rotate: [-15, 15, -15] }}
      transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
    >
      <PaintBrush size={48} weight="duotone" />
    </motion.div>
    <div
      role="progressbar"
      aria-label="Pictures finished"
      aria-valuemin={0}
      aria-valuemax={count?.n}
      aria-valuenow={finished ?? undefined}
      className="w-36 h-24 mt-8 border border-[var(--color-primary)]/20 rounded-[16px] overflow-hidden bg-[var(--color-surface)] shadow-[0_10px_28px_rgba(49,85,217,0.12)] relative"
    >
      {count && finished !== null ? (
        <div
          className="absolute inset-y-0 left-0 bg-[var(--color-secondary)]/30 transition-[width] duration-[var(--duration-slow)] ease-[var(--ease-out)]"
          style={{ width: `${(finished / count.n) * 100}%` }}
        />
      ) : (
        <div className="absolute inset-0 bg-[var(--color-secondary)]/15 animate-pulse" />
      )}
    </div>
  </div>
  );
};

const StackingVignette = () => {
  const reduce = useReducedMotion();
  return (
  <div className="relative w-32 h-32 my-4 flex justify-center">
    {[0, 1, 2, 3].map((i) => {
      const isCover = i === 3;
      const tilt = isCover ? 0 : (i % 2 === 0 ? -4 : 4);
      return (
        <motion.div
          key={i}
          className={`absolute h-24 w-20 border border-[var(--color-primary)]/20 rounded-[8px] shadow-[0_6px_18px_rgba(49,85,217,0.10)] overflow-hidden ${isCover ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-surface)]'}`}
          // Reduced motion: the finished stack as a still frame.
          initial={reduce ? false : undefined}
          animate={reduce ? { y: i * 4, opacity: 1, rotate: tilt } : {
            y: [-40, i * 4, i * 4],
            opacity: [0, 1, 0],
            rotate: [0, tilt, tilt]
          }}
          transition={{
            repeat: Infinity,
            duration: 3,
            times: [0, 0.4, 1],
            delay: i * 0.3,
            ease: "easeInOut"
          }}
          style={{ zIndex: i, top: 20 }}
        >
          {isCover && (
             <div className="absolute left-1.5 top-0 bottom-0 w-1.5 bg-black/20" />
          )}
        </motion.div>
      );
    })}
  </div>
  );
};

function HoldRecovery({jobId, profileId, refetch, held = false}: {jobId: string; profileId: string; refetch: () => Promise<boolean>; held?: boolean}) {
  const [stopState, setStopState] = useState<{review_id: string; generation_epoch: number; worker_finished: boolean} | null>(null);
  const [pencilHold, setPencilHold] = useState(false);
  const [canRepair, setCanRepair] = useState<boolean | null>(null);
  const [error, setError] = useState(false);
  const [sending, setSending] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [readVersion, setReadVersion] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const {data: {session}} = await supabase.auth.getSession();
        if (!session) throw new Error();
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/state`, {
          headers: {Authorization: `Bearer ${session.access_token}`}, cache: "no-store", signal: controller.signal,
        });
        if (!response.ok) throw new Error();
        const state = await response.json();
        if (!controller.signal.aborted) {
          setCanRepair(state.can_reconcile_hold === true); setError(false);
          setStopState(state.status === "awaiting_teacher" && state.review_id ? state : null);
          setPencilHold(state.pencil_hold === true);
          if (state.status && state.status !== "awaiting_teacher" && held) await refetch();
        }
      } catch { if (!controller.signal.aborted) setError(true); }
    })();
    return () => { controller.abort(); };
    // refetch is an unstable useJob callback. Only reread on an explicit retry or route change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId, readVersion, held]);
  async function repair() {
    if (sending) return;
    setSending(true); setError(false);
    try {
      const {data: {session}} = await supabase.auth.getSession();
      if (!session) throw new Error();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/reconcile-hold`, {
        method: "POST", headers: {Authorization: `Bearer ${session.access_token}`}, cache: "no-store",
      });
      if (!response.ok) throw new Error();
      setSubmitted(true);
      await refetch();
    } catch { setError(true); } finally { setSending(false); }
  }
  return <main className="flex flex-1 flex-col items-center justify-center gap-6 p-6 text-center">
    {held && <Users weight="duotone" className="size-16 text-primary" aria-hidden="true" />}
    <h1 className="font-display text-3xl font-extrabold text-primary">{held && pencilHold ? "Your teacher is taking a look" : held ? "Waiting for your teacher" : "Your writing is saved"}</h1>
    <p role="status">{held && pencilHold ? "Your story is saved. Your teacher will look at your picture change." : held ? "Your story is saved. Your teacher will help it continue." : submitted ? "We’re checking the saved step. You can return to your books." : "We couldn’t finish the last step. Your writing is still here."}</p>
    {error && <p role="alert">We couldn’t check your saved story. Try again.</p>}
    {canRepair === null && !error && <p role="status">Checking your saved story…</p>}
    {canRepair && !submitted && <button type="button" disabled={sending} onClick={() => void repair()} className="min-h-11 rounded-2xl bg-primary px-6 font-bold text-on-primary disabled:opacity-50 active:scale-[0.98]">{sending ? "Checking…" : "Try saving this step again"}</button>}
    {error && <button type="button" disabled={sending} className="min-h-11 underline active:scale-[0.98]" onClick={() => {setError(false); setReadVersion(value => value + 1);}}>Try checking again</button>}
    {canRepair === false && !held && <Link href={`/s/${profileId}/write`} className="min-h-11 underline active:scale-[0.98]">Write a new story</Link>}
    <Link href={`/s/${profileId}`} className="inline-flex min-h-11 items-center rounded-2xl bg-primary px-6 font-bold text-on-primary active:scale-[0.98]">Back to my books</Link>
    {held && stopState && !pencilHold && !error && <StopStory key={`${stopState.review_id}-${stopState.generation_epoch}`} jobId={jobId} reviewId={stopState.review_id}
      epoch={stopState.generation_epoch} ready={stopState.worker_finished}
      onStopped={() => void refetch()} onRefresh={() => { void refetch(); setReadVersion(value => value + 1); }} />}
  </main>;
}

type RevealCharacter = NonNullable<JobRow["reveal"]>["characters"][number];

// ADR-082 Decision 1: earlier pictures cost no image and no go. Choosing one resumes the pause
// with the picture it was chosen from, so a stale choice is rejected server-side (SH-08).
// Unchosen first-round draws arrive by id only; opening asks the API to moderate them first (SH-02).
function OtherVersions({ jobId, moderationMode, character, disabled, onChoose }: {
  jobId: string; moderationMode?: string; character: RevealCharacter; disabled: boolean;
  onChoose: (versionId: string) => void;
}) {
  const versions = character.versions ?? [];
  const unreviewed = character.unreviewed ?? [];
  const [open, setOpen] = useState(false);
  const [shown, setShown] = useState(versions);
  const [unavailable, setUnavailable] = useState(0);
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [loaded, setLoaded] = useState<Record<string, boolean>>({});
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);
  const openerRef = useRef<HTMLButtonElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const listId = `other-versions-${character.char_id}`;

  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    void (async () => {
      let signed: Record<string, string> = {};
      let list = versions;
      let missing = 0;
      let failed = false;
      try {
        if (unreviewed.length > 0) {
          const { data: { session } } = await supabase.auth.getSession();
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/characters/${encodeURIComponent(character.char_id)}/versions/open`,
            { method: "POST", headers: { Authorization: `Bearer ${session?.access_token}` }, signal: controller.signal },
          );
          if (!response.ok) throw new Error("versions_unavailable");
          ({ versions: list, unavailable: missing } = await response.json());
        }
        signed = await signPaths(list.map((v) => v.image_path),
          [{ id: jobId, moderation_mode: moderationMode, reveal: { characters: [{ ...character, versions: list }] } }],
          controller.signal);
      } catch { failed = true; /* shown as the error state below */ }
      if (controller.signal.aborted) return;
      setShown(list);
      setUnavailable(missing);
      setUrls(signed);
      setState(!failed && list.every((v) => signed[v.image_path]) ? "ready" : "error");
    })();
    return () => controller.abort();
    // The list re-reads on open and on an explicit retry only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, attempt]);

  useEffect(() => { if (open) listRef.current?.focus(); }, [open]);

  if (versions.length === 0 && unreviewed.length === 0) return null;

  function close() {
    setOpen(false);
    openerRef.current?.focus();
  }

  return (
    <div className="w-full">
      <button
        ref={openerRef}
        type="button"
        aria-label={`Other versions of ${character.name}`}
        aria-expanded={open}
        aria-controls={listId}
        disabled={disabled && !open}
        onClick={() => {
          setState("loading");
          setLoaded({});
          setOpen((value) => !value);
        }}
        className="min-h-[44px] w-full rounded-xl border border-[var(--color-primary)]/20 bg-background px-4 py-2 font-kid text-sm font-bold text-foreground hover:bg-[var(--color-primary)]/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
      >
        Other versions
      </button>
      {open && (
        <div
          ref={listRef}
          id={listId}
          role="group"
          aria-label={`Other versions of ${character.name}`}
          tabIndex={-1}
          onKeyDown={(event) => {
            if (event.key !== "Escape" || disabled) return;
            event.stopPropagation();
            close();
          }}
          className="mt-3 w-full rounded-[16px] bg-[var(--color-primary)]/5 p-4 text-left focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
        >
          <p role="status" className="font-kid text-sm text-foreground/70">
            {disabled ? "Changing your picture…" : state === "loading" ? `Loading ${character.name}'s other pictures…` : ""}
          </p>
          {(state === "error" || (state === "ready" && unavailable > 0)) && (
            <div role="alert" className="mt-2 flex flex-col items-start gap-2 font-kid text-sm">
              <p>We couldn&apos;t load this picture right now.</p>
              <button
                type="button"
                onClick={() => { setState("loading"); setAttempt((value) => value + 1); }}
                className="min-h-[44px] rounded-xl bg-[var(--color-surface)] px-4 py-2 font-bold focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 active:scale-[0.98]"
              >
                Try loading {character.name}&apos;s other pictures again
              </button>
            </div>
          )}
          {state === "ready" && shown.length === 0 && unavailable === 0 && (
            <p className="mt-2 font-kid text-sm">There are no other pictures of {character.name} right now.</p>
          )}
          {state === "ready" && shown.length > 0 && (
            <ul className="mt-2 grid grid-cols-2 gap-2">
              {shown.map((version, index) => (
                <li key={version.version_id}>
                  <button
                    type="button"
                    aria-label={`Use earlier picture ${index + 1} of ${character.name}`}
                    disabled={disabled || !loaded[version.version_id]}
                    onClick={() => onChoose(version.version_id)}
                    className="w-full rounded-[12px] border border-[var(--color-primary)]/20 bg-background p-1 hover:bg-[var(--color-primary)]/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                  >
                    <img
                      src={urls[version.image_path]}
                      alt={`Earlier picture ${index + 1} of ${character.name}`}
                      className="w-full aspect-square object-contain rounded-[8px] bg-[var(--color-muted)]"
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
            aria-label={`Cancel other versions of ${character.name}`}
            disabled={disabled}
            onClick={close}
            className="mt-3 min-h-[44px] rounded-xl px-4 py-2 font-kid font-bold text-foreground focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
          >
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}

// Mirrors backend `app.config.MAX_PENCIL_CHARS`; the API rejects anything longer.
const MAX_PENCIL_CHARS = 200;

// ADR-082 Decision 2: the child's words edit the picture on screen once, sent as written (SH-10).
// The API redacts and moderates the text before anything is stored or drawn (SH-03).
function MagicPencil({ character, tapsLeft, disabled, onSubmit }: {
  character: RevealCharacter; tapsLeft: number; disabled: boolean; onSubmit: (text: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const openerRef = useRef<HTMLButtonElement | null>(null);
  const fieldRef = useRef<HTMLTextAreaElement | null>(null);
  const panelId = `magic-pencil-${character.char_id}`;
  const fieldId = `${panelId}-text`;
  const empty = text.trim() === "";

  useEffect(() => { if (open) fieldRef.current?.focus(); }, [open]);

  function close() {
    setOpen(false);
    openerRef.current?.focus();
  }

  function submit() {
    if (empty || disabled) return;
    onSubmit(text.trim());
  }

  return (
    <div className="w-full">
      <button
        ref={openerRef}
        type="button"
        aria-label={`Magic pencil for ${character.name}`}
        aria-expanded={open}
        aria-controls={panelId}
        disabled={tapsLeft === 0 || (disabled && !open)}
        onClick={() => setOpen((value) => !value)}
        className="min-h-[44px] w-full rounded-xl border border-[var(--color-primary)]/20 bg-background px-4 py-2 font-kid text-sm font-bold text-foreground hover:bg-[var(--color-primary)]/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
      >
        Magic pencil
      </button>
      {tapsLeft === 0 && <p className="mt-1 text-center font-kid text-sm text-foreground/70">No pencils left for this book</p>}
      {open && tapsLeft > 0 && (
        <div
          id={panelId}
          role="group"
          aria-label={`Magic pencil for ${character.name}`}
          onKeyDown={(event) => {
            if (event.key !== "Escape" || disabled) return;
            event.stopPropagation();
            close();
          }}
          className="mt-3 w-full rounded-[16px] bg-[var(--color-primary)]/5 p-4 text-left"
        >
          <label htmlFor={fieldId} className="font-kid text-sm font-bold text-foreground">
            What should change about {character.name}?
          </label>
          <textarea
            ref={fieldRef}
            id={fieldId}
            value={text}
            maxLength={MAX_PENCIL_CHARS}
            rows={3}
            disabled={disabled}
            aria-describedby={`${fieldId}-count ${fieldId}-goes`}
            placeholder="Like: give them a red hat"
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key !== "Enter" || event.shiftKey) return;
              event.preventDefault();
              submit();
            }}
            className="mt-2 w-full rounded-xl border border-[var(--color-primary)]/30 bg-background p-3 font-kid text-base text-foreground focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50"
          />
          <div className="mt-1 flex justify-between gap-2 font-kid text-sm text-foreground/70">
            <p id={`${fieldId}-goes`}>This uses 1 of your {tapsLeft} {tapsLeft === 1 ? "go" : "goes"} left.</p>
            <p id={`${fieldId}-count`}>{text.length}/{MAX_PENCIL_CHARS}</p>
          </div>
          <p role="status" className="font-kid text-sm text-foreground/70">{disabled ? "Changing your picture…" : ""}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              aria-label={`Change ${character.name}'s picture`}
              disabled={empty || disabled}
              onClick={submit}
              className="min-h-[44px] rounded-xl border border-[var(--color-primary)]/40 bg-[var(--color-surface)] px-4 py-2 font-kid font-bold text-[var(--color-primary)] hover:bg-[var(--color-primary)]/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              Change picture
            </button>
            <button
              type="button"
              aria-label={`Cancel magic pencil for ${character.name}`}
              disabled={disabled}
              onClick={close}
              className="min-h-[44px] rounded-xl px-4 py-2 font-kid font-bold text-foreground focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// AC-11: the old and new pictures are shown side by side with the choice. The go is spent either
// way, and the book cannot go on until the child chooses (the API rejects confirm meanwhile).
function PencilChoice({ jobId, moderationMode, character, newUrl, disabled, onChoose, onRetryNew }: {
  jobId: string; moderationMode?: string; character: RevealCharacter; newUrl: string | null | undefined; disabled: boolean;
  onChoose: (choice: "kept" | "old") => void; onRetryNew: () => void;
}) {
  const old = character.pencil_choice!;
  const [url, setUrl] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      let signed: Record<string, string> = {};
      try {
        signed = await signPaths([old.image_path],
          [{ id: jobId, moderation_mode: moderationMode, reveal: { characters: [character] } }], controller.signal);
      } catch { /* shown as the error state below */ }
      if (controller.signal.aborted) return;
      setUrl(signed[old.image_path] ?? null);
      setState(signed[old.image_path] ? "ready" : "error");
    })();
    return () => controller.abort();
    // The old picture re-reads on an explicit retry only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt]);

  return (
    <div role="group" aria-label={`Keep the new picture of ${character.name}?`} className="w-full rounded-[16px] bg-[var(--color-primary)]/5 p-4 text-left">
      <p className="font-kid text-sm leading-relaxed text-foreground">
        Here is your changed picture of {character.name}. Keep it, or go back to the old one.
      </p>
      {/* The card widens while this choice is open, so Old and New fit side by side (audit B3). */}
      <div className="mt-2">
        <OldNewPictures
          old={state === "error" ? (
            <div role="alert" className="flex aspect-[4/3] w-full flex-col items-center justify-center gap-2 rounded-[8px] bg-[var(--color-muted)] p-3 text-center font-kid text-sm">
              <p>We couldn&apos;t load the old picture right now.</p>
              <button
                type="button"
                onClick={() => { setState("loading"); setAttempt((value) => value + 1); }}
                className="min-h-[44px] rounded-xl bg-[var(--color-surface)] px-4 py-2 font-bold focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 active:scale-[0.98]"
              >
                Try loading {character.name}&apos;s old picture again
              </button>
            </div>
          ) : (
            <PictureBox src={url ?? undefined} alt={`Old picture of ${character.name}`} className="aspect-[4/3] w-full rounded-[8px]"
              onRetry={() => { forgetSignedUrls([old.image_path]); setUrl(null); setState("loading"); setAttempt((value) => value + 1); }} />
          )}
          fresh={<PictureBox src={newUrl} alt={`New picture of ${character.name}`} onRetry={onRetryNew} className="aspect-[4/3] w-full rounded-[8px]" />}
        />
      </div>
      <p role="status" className="font-kid text-sm text-foreground/70">{disabled ? "Changing your picture…" : ""}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          aria-label={`Keep this new picture of ${character.name}`}
          disabled={disabled}
          onClick={() => onChoose("kept")}
          className="min-h-[44px] rounded-xl bg-[var(--color-primary)] px-4 py-2 font-kid font-bold text-[var(--color-surface)] focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
        >
          Keep this
        </button>
        <button
          type="button"
          aria-label={`Use the old picture of ${character.name}`}
          disabled={disabled}
          onClick={() => onChoose("old")}
          className="min-h-[44px] rounded-xl border border-[var(--color-primary)]/40 bg-[var(--color-surface)] px-4 py-2 font-kid font-bold text-[var(--color-primary)] hover:bg-[var(--color-primary)]/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
        >
          Use the old one
        </button>
      </div>
    </div>
  );
}

export default function ProcessingPage({ params }: { params: Promise<{ profileId: string; jobId: string }> }) {
  const { profileId, jobId } = use(params);
  const { bucket, row, refetch } = useJob(jobId);
  const router = useRouter();

  // Prevent the stepper from flashing during a redraw (spec §4.2). Holds the stage the job was
  // paused on when we confirmed; the bridge lifts the moment the backend reports a different one.
  // It must be state, not a ref: a ref cannot re-render the thing that reads it, so the bridge
  // would only ever lift on some *other* render.
  const [bridgeStage, setBridgeStage] = useState<string | null>(null);
  const [submissionState, setSubmissionState] = useState<SubmissionState>("idle");
  // Which card sent the request that failed; null is "Use these characters".
  const [confirmError, setConfirmError] = useState<{ charId: string | null } | null>(null);
  const [selectedTrait, setSelectedTrait] = useState<SelectedTrait>(null);
  const [pendingRedrawName, setPendingRedrawName] = useState<string | null>(null);
  const [changingPicture, setChangingPicture] = useState(false);
  // Which cards have "Change this picture" open, by char_id. Here, not in the card, because a redraw
  // leaves the reveal and comes back.
  const [changeOpen, setChangeOpen] = useState<Record<string, boolean>>({});
  const submissionInFlight = useRef(false);
  const characterHeadingRefs = useRef<Record<string, HTMLHeadingElement | null>>({});
  const characterCardRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const selectedControlWasFocused = useRef(false);
  const lastSelectedCharId = useRef<string | null>(null);
  const submissionsDisabled = submissionState !== "idle";
  const imageRequest = useRef<AbortController | null>(null);
  const isRetryingCharacterChoices = submissionState === "reconciling";

  function toggleTrait(charId: string, attribute: string) {
    setChoiceUpdated(false);
    setSelectedTrait((current) => {
      if (current?.charId === charId && current.attribute === attribute) {
        selectedControlWasFocused.current = false;
        return null;
      }
      lastSelectedCharId.current = charId;
      selectedControlWasFocused.current = characterCardRefs.current[charId]?.contains(document.activeElement) ?? false;
      return { charId, attribute };
    });
  }

  const revealFingerprint = bucket === "paused" && row?.reveal
    ? JSON.stringify({
        tapsLeft: row.reveal.taps_left,
        characters: row.reveal.characters.map(({ char_id, image_path, chips }) => ({
          charId: char_id,
          imagePath: image_path,
          chips,
        })),
      })
    : null;
  const previousRevealFingerprint = useRef<string | null>(null);
  const [choiceUpdated, setChoiceUpdated] = useState(false);

  useEffect(() => {
    // Deliberately keeps the last paused fingerprint across the in-flight leg: a redraw always
    // leaves the pause and comes back, and forgetting it here let a replacement that still
    // suggested the same trait return with the spent selection intact.
    if (bucket !== "paused" || !row?.reveal || !revealFingerprint) return;

    const previous = previousRevealFingerprint.current;
    const selectionStillOffered = selectedTrait === null || row.reveal.characters.some(
      (character) => character.char_id === selectedTrait.charId && character.chips.includes(selectedTrait.attribute)
    );
    const revealChanged = previous !== null && previous !== revealFingerprint;

    if (changingPicture && revealChanged) {
      // The chosen picture is back; the focus effect below returns the child to its heading.
      setChangingPicture(false);
      setChoiceUpdated(true);
    }

    if (selectedTrait && (!selectionStillOffered || revealChanged)) {
      lastSelectedCharId.current = selectedTrait.charId;
      // Two questions, not one. The latch answers "was the child working in this card when they
      // chose?" — it has to be captured at selection time, because by now the chosen control is
      // unmounted and focus has already fallen to <body>. This narrows it with "and is focus still
      // here, or nowhere?": a child who tabbed to Continue is navigating, and dragging them back
      // to the heading is the theft spec §5 forbids.
      const active = document.activeElement;
      const focusIsStillHereOrLost =
        active === null
        || active === document.body
        || (characterCardRefs.current[selectedTrait.charId]?.contains(active) ?? false);
      selectedControlWasFocused.current = selectedControlWasFocused.current && focusIsStillHereOrLost;
      setSelectedTrait(null);
      setPendingRedrawName(null);
      setChoiceUpdated(true);
    }

    previousRevealFingerprint.current = revealFingerprint;
  }, [bucket, revealFingerprint, row?.reveal, selectedTrait, changingPicture]);

  useEffect(() => {
    if (!selectedTrait || submissionsDisabled) return;
    function clearSelection(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      selectedControlWasFocused.current = false;
      setSelectedTrait(null);
    }
    window.addEventListener("keydown", clearSelection);
    return () => window.removeEventListener("keydown", clearSelection);
  }, [selectedTrait, submissionsDisabled]);

  useEffect(() => {
    if (!choiceUpdated || !selectedControlWasFocused.current || !lastSelectedCharId.current) return;
    characterHeadingRefs.current[lastSelectedCharId.current]?.focus();
    selectedControlWasFocused.current = false;
  }, [choiceUpdated, revealFingerprint]);

  // Stall line: show after STALL_MS of no stage change
  const [stalling, setStalling] = useState(false);
  useEffect(() => {
    if (bucket !== "in-flight") return;
    const timer = setTimeout(() => setStalling(true), STALL_MS);
    return () => {
      clearTimeout(timer);
      setStalling(false);
    };
  }, [bucket, row?.current_stage]);

  // Reveal character image signing and browser-read state
  const [signedCharUrls, setSignedCharUrls] = useState<Record<string, string>>({});
  const [characterImageState, setCharacterImageState] = useState<Record<string, CharacterImageState>>({});

  // A redraw re-enters this function with the replacement's paths while the previous signing
  // round may still be awaiting. Without a token the loser's resolution lands last and writes its
  // stale URL and a fresh "loading" over the picture the child is actually looking at — which also
  // re-disables "Use these characters" on an image that already loaded.
  const characterImageLoadId = useRef(0);
  const moderationMode = row?.moderation_mode;

  const loadCharacterImages = useCallback(async (characters: Array<{ char_id: string; image_path: string }>) => {
    imageRequest.current?.abort();
    const controller = new AbortController();
    imageRequest.current = controller;
    const loadId = characterImageLoadId.current + 1;
    characterImageLoadId.current = loadId;
    setSignedCharUrls((current) => {
      const next = { ...current };
      characters.forEach((character) => delete next[character.char_id]);
      return next;
    });
    setCharacterImageState((current) => ({
      ...current,
      ...Object.fromEntries(characters.map((character) => [character.char_id, "signing"])),
    }));

    const paths = characters.map((character) => character.image_path);
    let signed: Record<string, string> = {};
    for (let attempt = 0; attempt < 2 && Object.keys(signed).length === 0; attempt += 1) {
      try {
        signed = await signPaths(paths, [{id: jobId, moderation_mode: moderationMode, reveal: {characters}}], controller.signal);
      } catch {
        signed = {};
      }
    }

    const urls: Record<string, string> = {};
    const states: Record<string, CharacterImageState> = {};
    for (const character of characters) {
      const url = signed[character.image_path];
      if (url) urls[character.char_id] = url;
      states[character.char_id] = url ? "loading" : "error";
    }
    if (controller.signal.aborted || loadId !== characterImageLoadId.current) return;
    setSignedCharUrls((current) => {
      const next = { ...current };
      characters.forEach((character) => {
        if (urls[character.char_id]) next[character.char_id] = urls[character.char_id];
        else delete next[character.char_id];
      });
      return next;
    });
    setCharacterImageState((current) => ({ ...current, ...states }));
  }, [jobId, moderationMode]);

  // Keyed on the pictures, not the reveal object: a tab-return refetch or realtime UPDATE hands
  // back an identical reveal as a new object, and reloading on that blanked every picture and
  // disabled every control until it downloaded again. A new draw always has a new path.
  const revealImagesKey = bucket === "paused" && row?.reveal?.characters.length
    ? JSON.stringify(row.reveal.characters.map(({ char_id, image_path }) => [char_id, image_path]))
    : null;

  useEffect(() => {
    if (!revealImagesKey) return;
    const characters = (JSON.parse(revealImagesKey) as Array<[string, string]>)
      .map(([char_id, image_path]) => ({ char_id, image_path }));
    // Initialize the per-image read state when the paused reveal becomes authoritative.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadCharacterImages(characters);
    return () => { imageRequest.current?.abort(); };
  }, [revealImagesKey, loadCharacterImages]);

  // Push to /book on terminal-success. The bridge needs no teardown here: `isRedrawing` is read
  // only on the in-flight branch and only while the stage still matches, so a stale value cannot
  // show through. Clearing it from this effect would in fact break it — `useRouter()` hands back
  // a new object every render, so this effect re-runs on every render and would wipe the bridge
  // one render after the tap.
  useEffect(() => {
    if (bucket === "terminal-success") {
      router.replace(`/s/${profileId}/book/${jobId}`);
    }
  }, [bucket, profileId, jobId, router]);

  async function handleConfirm(
    action: "confirm" | "try_again" | "choose_version" | "pencil" | "pencil_choice",
    char_id?: string,
    attribute?: string,
    extra?: Record<string, string>
  ) {
    if (submissionInFlight.current || submissionsDisabled) return;
    submissionInFlight.current = true;
    // Only a redraw, a version choice or a pencil request returns to this stage; a plain confirm advances, and
    // bridging it made the continue path claim a redraw was under way.
    setBridgeStage(action !== "confirm" ? row?.current_stage ?? null : null);
    setSubmissionState("sending");
    setConfirmError(null);
    let requestFailed = false;
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ action, char_id: char_id ?? null, attribute: attribute ?? null, ...extra }),
      });
      requestFailed = !res.ok;
    } catch {
      requestFailed = true;
    }

    setSubmissionState("reconciling");
    let refreshed = false;
    try {
      refreshed = await refetch();
    } catch {
      refreshed = false;
    }
    if (!refreshed) {
      setBridgeStage(null);
      setSubmissionState("unknown");
      return;
    }

    if (requestFailed) {
      setConfirmError({ charId: char_id ?? null });
      setChangingPicture(false);
    }
    setSubmissionState("idle");
    submissionInFlight.current = false;
  }

  async function retryCharacterChoices() {
    if (submissionState !== "unknown") return;
    setSubmissionState("reconciling");
    let refreshed = false;
    try {
      refreshed = await refetch();
    } catch {
      refreshed = false;
    }
    if (refreshed) {
      submissionInFlight.current = false;
      setSubmissionState("idle");
      return;
    }
    setSubmissionState("unknown");
  }

  // Derive FailureScreen kind from row state
  if (bucket === "stopped") return <StoppedStory jobId={jobId} profileId={profileId} />;
  if (bucket === "teacher-held") {
    return <HoldRecovery jobId={jobId} profileId={profileId} refetch={refetch} held />;
  }
  if (bucket === "not-found") {
    return <FailureScreen kind="not-found" />;
  }

  if (bucket === "terminal-failure") {
    if (row?.moderation_mode === "teacher_review_v1") return <HoldRecovery jobId={jobId} profileId={profileId} refetch={refetch} />;
    const kind =
      row?.failure_reason === "child_text"
        ? "revise"
        : row?.status === SWEPT_STATUS
        ? "asleep"
        : "retry";
    return (
      <FailureScreen
        kind={kind}
        reason={row?.failure_reason}
        jobId={jobId}
        inputText={row?.input_text}
        title={row?.title}
        stylePresetId={row?.style_preset_id}
      />
    );
  }

  if (bucket === "paused" && row?.reveal) {
    const { characters, taps_left } = row.reveal;
    // Magic pencil jobs (ADR-082) share the goes between Redraw and the pencil (AC-06).
    const pencil = characters.some((character) => character.versions !== undefined);
    const goes = pencil ? ["go", "goes"] : ["redraw", "redraws"];
    const waiting = characters.find((character) => character.pencil_choice);
    const allRequiredImagesLoaded = characters.every(
      (character) => characterImageState[character.char_id] === "loaded"
    );
    // A live region only announces a change to text it already holds, so this node is always
    // rendered and only its content switches.
    const liveMessage =
      pendingRedrawName && submissionsDisabled
        ? `Redrawing ${pendingRedrawName}…`
        : choiceUpdated
        ? "The character choices were updated."
        : "";
    return (
      <div className="w-full flex-1 min-h-[calc(100dvh-5rem)] flex flex-col justify-center items-center p-6 max-w-5xl mx-auto">
        <div className="w-full flex justify-start mb-4 z-20">
          <Link
            href={`/s/${profileId}`}
            className="inline-flex min-h-11 items-center gap-1.5 font-kid text-sm font-bold text-foreground/60 hover:text-primary transition-colors focus-visible:outline-secondary focus-visible:outline-2 rounded-lg py-1 px-2.5 active:scale-[0.98]"
          >
            ← Bookshelf
          </Link>
        </div>
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center gap-4 text-center mb-12"
        >
          {row && (
            <p className="text-sm font-bold text-foreground/50 tracking-wide">
              {displayTitle(row.title, row.input_text)}
            </p>
          )}
          <h1 className="font-display text-4xl md:text-5xl text-foreground tracking-tight text-center">
            <KineticText text="Meet your cast!" />
          </h1>
          <p className="font-kid text-lg text-foreground/70 max-w-md">
            Choose a detail you want the new picture to show.
          </p>
          {/* Always rendered, so a live region exists before its text changes. The pending line
              is announced only — the in-flight screen states it visually — while the changed-reveal
              explanation is also shown, because a sighted child otherwise watches the chips change
              with no explanation at all (spec §4). */}
          <p
            aria-live="polite"
            className={choiceUpdated ? "font-kid text-sm text-foreground/70 max-w-md" : "sr-only"}
          >
            {liveMessage}
          </p>
        </motion.div>

        <div className="mb-6 text-center font-kid text-foreground">
          {taps_left > 0 ? (
            <>
              <p className="font-bold">
                {taps_left} {taps_left === 1 ? goes[0] : goes[1]} left for this book
              </p>
              <p className="text-sm text-foreground/70">
                {pencil ? "Redraw and Magic pencil share them, for all your characters." : "Shared by all your characters."}
              </p>
            </>
          ) : (
            <p className="max-w-lg">
              No {goes[1]} left for this book. You can use these characters or go back to your bookshelf.
            </p>
          )}
        </div>

        <motion.div 
          className="flex flex-wrap justify-center gap-8 w-full"
          initial="hidden"
          animate="show"
          variants={{
            hidden: { opacity: 0 },
            show: {
              opacity: 1,
              transition: { staggerChildren: 0.15 }
            }
          }}
        >
          {characters.map(c => (
            <motion.div 
              key={c.char_id} 
              ref={(node) => { characterCardRefs.current[c.char_id] = node; }}
              variants={{
                hidden: { opacity: 0, y: 40, scale: 0.8 },
                show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", bounce: 0 } }
              }}
              className={`flex flex-col items-center gap-4 neo-border bg-[var(--color-surface)] rounded-[24px] p-5 shadow-[0_10px_28px_rgba(49,85,217,0.12)] ${c.pencil_choice ? "max-w-2xl" : "max-w-xs"} w-full`}
            >
              {/* While choosing, the New box in the choice is the only copy of the new picture (audit Q3). */}
              {c.pencil_choice ? null : characterImageState[c.char_id] === "error" ? (
                <div role="alert" className="flex aspect-square w-full max-w-[17.5rem] flex-col items-center justify-center gap-3 rounded-[16px] bg-[var(--color-muted)] p-4 text-center font-kid">
                  <p>We couldn&apos;t load {c.name}&apos;s picture.</p>
                  <button
                    type="button"
                    className="min-h-[44px] rounded-xl bg-[var(--color-surface)] px-4 py-2 font-bold focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 active:scale-[0.98]"
                    onClick={() => { forgetSignedUrls([c.image_path]); void loadCharacterImages([c]); }}
                  >
                    Try loading {c.name}&apos;s picture again
                  </button>
                </div>
              ) : signedCharUrls[c.char_id] ? (
                <img
                  src={signedCharUrls[c.char_id]}
                  alt={c.name}
                  className="w-full max-w-[17.5rem] aspect-square object-contain rounded-[16px] bg-[var(--color-muted)]"
                  onLoad={() => setCharacterImageState((current) => ({ ...current, [c.char_id]: "loaded" }))}
                  onError={() => setCharacterImageState((current) => ({ ...current, [c.char_id]: "error" }))}
                />
              ) : (
                <div className="w-full max-w-[17.5rem] aspect-square rounded-[16px] bg-[var(--color-muted)] animate-pulse" />
              )}
              <h2
                ref={(node) => { characterHeadingRefs.current[c.char_id] = node; }}
                tabIndex={-1}
                className="font-display text-2xl text-foreground mt-2 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
              >
                {c.name}
              </h2>

              {c.pencil_choice ? (
                <PencilChoice
                  key={c.image_path}
                  jobId={jobId}
                  moderationMode={moderationMode}
                  character={c}
                  newUrl={characterImageState[c.char_id] === "error" ? null : signedCharUrls[c.char_id]}
                  disabled={submissionsDisabled}
                  onRetryNew={() => { forgetSignedUrls([c.image_path]); void loadCharacterImages([c]); }}
                  onChoose={(choice) => {
                    setSelectedTrait(null);
                    setPendingRedrawName(null);
                    setChangingPicture(true);
                    lastSelectedCharId.current = c.char_id;
                    selectedControlWasFocused.current = true;
                    void handleConfirm("pencil_choice", c.char_id, undefined, { choice, source: c.image_path });
                  }}
                />
              ) : (<>
              <OtherVersions
                key={c.image_path}
                jobId={jobId}
                moderationMode={moderationMode}
                character={c}
                disabled={submissionsDisabled || characterImageState[c.char_id] !== "loaded"}
                onChoose={(versionId) => {
                  setSelectedTrait(null);
                  setPendingRedrawName(null);
                  setChangingPicture(true);
                  lastSelectedCharId.current = c.char_id;
                  selectedControlWasFocused.current = true;
                  void handleConfirm("choose_version", c.char_id, undefined, { version_id: versionId, source: c.image_path });
                }}
              />

              {/* Outside the tools below, so a closed "Change this picture" never hides it. */}
              {c.versions !== undefined && c.pencil_ready && c.pencil_refused && (
                <p role="alert" className="w-full text-center font-kid text-sm text-[var(--color-destructive)]">
                  We couldn&apos;t change this picture. Try different words.
                </p>
              )}

              {/* Audit B9: Other versions stays one tap away; the pencil and the redraw chips wait behind
                  one disclosure, whose open state lives on this page so it survives a redraw. */}
              {c.versions !== undefined && (
                <button
                  type="button"
                  aria-label={`Change this picture of ${c.name}`}
                  aria-expanded={Boolean(changeOpen[c.char_id])}
                  aria-controls={`change-tools-${c.char_id}`}
                  disabled={submissionsDisabled}
                  onClick={() => {
                    if (changeOpen[c.char_id] && selectedTrait?.charId === c.char_id) setSelectedTrait(null);
                    setChangeOpen((open) => ({ ...open, [c.char_id]: !open[c.char_id] }));
                  }}
                  className="min-h-[44px] w-full rounded-xl border border-[var(--color-primary)]/20 bg-background px-4 py-2 font-kid text-sm font-bold text-foreground hover:bg-[var(--color-primary)]/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                >
                  Change this picture
                </button>
              )}

              {/* Hidden, not unmounted, when closed, so the pencil keeps what the child typed. */}
              <div id={`change-tools-${c.char_id}`} hidden={c.versions !== undefined && !changeOpen[c.char_id]}
                className="flex w-full flex-col items-center gap-4">
              {c.versions !== undefined && c.pencil_ready && (
                <MagicPencil
                  key={`pencil-${c.image_path}`}
                  character={c}
                  tapsLeft={taps_left}
                  disabled={submissionsDisabled || characterImageState[c.char_id] !== "loaded"}
                  onSubmit={(text) => {
                    setSelectedTrait(null);
                    setPendingRedrawName(null);
                    setChangingPicture(true);
                    lastSelectedCharId.current = c.char_id;
                    selectedControlWasFocused.current = true;
                    void handleConfirm("pencil", c.char_id, undefined, { text, source: c.image_path });
                  }}
                />
              )}

              {taps_left > 0 && c.chips.length === 0 && (
                <p className="w-full text-center font-kid text-sm text-foreground/70">
                  No suggested changes are available for this character.
                </p>
              )}
              
              <div className="flex flex-wrap justify-center gap-2 mt-2 w-full">
                {taps_left > 0 && c.chips.map(chip => {
                  const selected = selectedTrait?.charId === c.char_id && selectedTrait.attribute === chip;
                  return (
                    <button
                      key={chip}
                      type="button"
                      aria-pressed={selected}
                      disabled={submissionsDisabled || characterImageState[c.char_id] !== "loaded"}
                      onClick={() => toggleTrait(c.char_id, chip)}
                      className={`min-h-[44px] max-w-full rounded-full border px-4 py-2 font-kid text-sm text-foreground transition-colors focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed ${
                        selected
                          ? "border-[var(--color-primary)] bg-[var(--color-primary)]/10 font-bold"
                          : "border-[var(--color-primary)]/20 bg-background hover:bg-[var(--color-primary)]/5"
                      } active:scale-[0.98]`}
                    >
                      {chip}
                      {selected && <span className="sr-only"> selected</span>}
                    </button>
                  );
                })}
              </div>

              {selectedTrait?.charId === c.char_id && (
                <div className="w-full rounded-[16px] bg-[var(--color-primary)]/5 p-4 text-left">
                  <p className="font-kid text-sm leading-relaxed text-foreground">
                    {selectedTrait.attribute === "overall physical appearance"
                      ? `We'll try a new picture of ${c.name}. It will replace this picture. Other details may change.`
                      : `We'll make a new picture and try to show ${selectedTrait.attribute}. It will replace this picture. Other details may change.`}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={submissionsDisabled || characterImageState[c.char_id] !== "loaded"}
                      onClick={() => {
                        setPendingRedrawName(c.name);
                        setChangingPicture(false);
                        void handleConfirm("try_again", c.char_id, selectedTrait.attribute);
                      }}
                      className="min-h-[44px] rounded-xl border border-[var(--color-primary)]/40 bg-[var(--color-surface)] px-4 py-2 font-kid font-bold text-[var(--color-primary)] hover:bg-[var(--color-primary)]/5 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                    >
                      Redraw {c.name}
                    </button>
                    <button
                      type="button"
                      disabled={submissionsDisabled}
                      onClick={() => setSelectedTrait(null)}
                      className="min-h-[44px] rounded-xl px-4 py-2 font-kid font-bold text-foreground focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
              </div>
              </>)}
              {confirmError?.charId === c.char_id && (
                <p role="alert" className="w-full font-kid text-base text-[var(--color-destructive)] bg-[var(--color-destructive)]/10 px-4 py-3 rounded-xl">
                  We couldn&apos;t send that choice. Please try again.
                </p>
              )}
            </motion.div>
          ))}
        </motion.div>

        <div className="mt-12 w-full flex flex-col items-center justify-center gap-3">
          <p className="font-kid text-sm text-foreground/70">
            {waiting ? `Choose Keep this or Use the old one for ${waiting.name} first.` : "Continue with the pictures shown."}
          </p>
          <button
            type="button"
            disabled={submissionsDisabled || !allRequiredImagesLoaded || waiting !== undefined}
            onClick={() => {
              setSelectedTrait(null);
              setPendingRedrawName(null);
              void handleConfirm("confirm");
            }}
            className="rounded-[16px] bg-[var(--color-primary)] text-[var(--color-surface)] min-h-[56px] px-12 font-kid text-xl disabled:opacity-50 disabled:cursor-not-allowed hover:brightness-105 active:scale-[0.98] transition-all font-bold shadow-[0_10px_28px_rgba(49,85,217,0.12)] focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            Use these characters
          </button>
        </div>
        
        <div className="min-h-16 mt-8 flex items-center justify-center">
          <AnimatePresence>
            {submissionState === "unknown" ? (
              <motion.div
                initial={{ opacity: 0, height: 0, scale: 0.9 }}
                animate={{ opacity: 1, height: "auto", scale: 1 }}
                exit={{ opacity: 0, height: 0, scale: 0.9 }}
                role="alert"
                className="flex flex-wrap items-center justify-center gap-3 rounded-xl bg-[var(--color-destructive)]/10 px-6 py-3 font-kid text-base text-[var(--color-destructive)]"
              >
                <p>We couldn&apos;t refresh your character choices. Try loading them again.</p>
                <button
                  type="button"
                  onClick={() => void retryCharacterChoices()}
                  disabled={isRetryingCharacterChoices}
                  className="min-h-[44px] rounded-xl bg-[var(--color-surface)] px-4 py-2 font-bold text-foreground focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3 disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.98]"
                >
                  Load character choices again
                </button>
              </motion.div>
            ) : confirmError?.charId === null && (
              <motion.p 
                initial={{ opacity: 0, height: 0, scale: 0.9 }}
                animate={{ opacity: 1, height: "auto", scale: 1 }}
                exit={{ opacity: 0, height: 0, scale: 0.9 }}
                role="alert" 
                className="font-kid text-base text-[var(--color-destructive)] bg-[var(--color-destructive)]/10 px-6 py-3 rounded-xl"
              >
                We couldn&apos;t send that choice. Please try again.
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </div>
    );
  }

  // in-flight bucket (or justConfirmed redraw state)
  const currentStepRaw = getStep(row?.current_stage ?? null);
  const currentStep = currentStepRaw ?? 1;
  const STEPS: StepperStep[] = [1, 2, 3, 4];
  const isRedrawing = bridgeStage !== null && (row?.current_stage ?? null) === bridgeStage;

  const ICONS = {
    1: BookOpen,
    2: Users,
    3: PaintBrush,
    4: MagicWand,
  };
  const STEP_NAMES = { 1: "Story", 2: "Characters", 3: "Pictures", 4: "Book" };

  const headline = isRedrawing
    ? changingPicture ? "Changing your picture…" : pendingRedrawName ? `Redrawing ${pendingRedrawName}…` : "Redrawing your character…"
    : currentStepRaw !== null
    ? getStepLabel(currentStep, row?.current_stage ?? null)
    : "Warming up...";

  return (
    <div className="w-full flex-1 min-h-[calc(100dvh-5rem)] flex flex-col justify-center items-center p-5 sm:p-6 max-w-4xl mx-auto relative">
      
      {/* Top Navigation Exit */}
      <div className="w-full flex justify-start mb-4 z-20">
        <Link
          href={`/s/${profileId}`}
          className="inline-flex min-h-11 items-center gap-1.5 font-kid text-sm font-bold text-foreground/60 hover:text-primary transition-colors focus-visible:outline-secondary focus-visible:outline-2 rounded-lg py-1 px-2.5 active:scale-[0.98]"
        >
          ← Bookshelf
        </Link>
      </div>

      <div className="z-10 w-full min-w-0 text-center mb-8 sm:mb-12">
        <h1 className="font-display font-extrabold text-4xl md:text-5xl leading-tight text-foreground tracking-tight [overflow-wrap:anywhere]">
          {displayTitle(row?.title, row?.input_text)}
        </h1>
        <p className="mt-3 font-kid text-lg sm:text-xl font-bold text-foreground/75">
          Making your book…
        </p>
      </div>

      {/* The Journey Tracker */}
      <div className="w-full max-w-2xl z-10 mb-8 sm:mb-16 relative">
         {/* Connecting line behind. Its ends sit on the first and last circle centres (half of
             w-14 / md:w-16), so (step - 1) / 3 of it reaches the current circle's centre. */}
         <div className="absolute top-1/2 left-7 right-7 md:left-8 md:right-8 h-1 bg-[var(--color-muted)] -translate-y-1/2 z-0 hidden sm:block" />
         <motion.div
           className="absolute top-1/2 left-7 right-7 md:left-8 md:right-8 h-1 bg-[var(--color-primary)] -translate-y-1/2 z-0 hidden sm:block origin-left"
           initial={{ scaleX: 0 }}
           animate={{ scaleX: (currentStep - 1) / 3 }}
           transition={{ duration: 0.8, ease: "easeInOut" }}
         />

         <ol aria-label="Book steps" className="relative flex items-center justify-between gap-4 md:gap-8">
         {STEPS.map(step => {
           const isDone = currentStepRaw !== null && step < currentStepRaw;
           const isActive = step === currentStep && !isRedrawing && currentStepRaw !== null;
           const Icon = ICONS[step];

           return (
             <li key={step} aria-current={isActive ? "step" : undefined} className="relative z-10 flex flex-col items-center gap-2">
                <motion.div
                  aria-hidden="true"
                  animate={{
                    scale: isActive ? 1.15 : 1
                  }}
                  style={{
                    backgroundColor: isDone || isActive ? "var(--color-primary)" : "var(--color-surface)",
                    borderColor: isDone || isActive ? "var(--color-primary)" : "var(--color-muted)",
                    color: isDone || isActive ? "#FFFDF7" : "var(--foreground)",
                  }}
                  className="w-14 h-14 md:w-16 md:h-16 rounded-full border-2 flex items-center justify-center shadow-sm relative transition-colors duration-300"
                >
                  {isDone ? <Check size={28} weight="bold" /> : <Icon size={28} weight={isActive ? "fill" : "regular"} />}
                </motion.div>
                <span className="sr-only">{`Step ${step}: ${STEP_NAMES[step]}${isDone ? ", done" : ""}`}</span>
             </li>
           );
         })}
         </ol>
      </div>

      {/* Spotlight Theater Vignettes & Text */}
      <div className="z-10 text-center min-h-[220px] flex flex-col items-center justify-center gap-4 w-full">
        <AnimatePresence mode="wait">
          {isRedrawing ? (
            <motion.div
              key="redrawing"
              initial={{ opacity: 0, scale: 0.8, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.8, y: -10 }}
              className="flex flex-col items-center gap-6"
            >
               <DrawingVignette count={null} />
            </motion.div>
          ) : (
            <motion.div
              key={`step-${currentStep}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4, type: "spring", bounce: 0 }}
              className="flex flex-col items-center gap-4 w-full px-4"
            >
               <div className="h-[140px] flex items-center justify-center">
                 {currentStep === 1 && <ReadingVignette />}
                 {currentStep === 2 && <CharactersVignette />}
                 {currentStep === 3 && <DrawingVignette count={getPictureCount(row?.current_stage ?? null)} />}
                 {currentStep === 4 && <StackingVignette />}
               </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Stays mounted so screen readers hear each step change; the heading inside re-enters once
            per change instead of pulsing. */}
        <div role="status" className="w-full px-4">
          <motion.h2
            key={headline}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="font-display text-3xl md:text-4xl text-foreground text-center tracking-tight"
          >
            {headline}
          </motion.h2>
        </div>
      </div>

      {/* Stalling Text */}
      <div className="z-10 mt-12 min-h-[60px] flex justify-center w-full" aria-live="polite">
          {stalling && !isRedrawing && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="flex flex-col sm:flex-row items-center gap-3 bg-[var(--color-surface)] neo-border px-6 py-4 rounded-2xl sm:rounded-full shadow-sm max-w-sm sm:max-w-xl w-full mx-auto justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-[var(--color-secondary)] animate-pulse shrink-0" />
                <p className="font-kid text-sm md:text-base text-foreground/80 leading-snug">
                  This step is taking longer than usual. Your progress is saved, so you can leave and come back.
                </p>
              </div>
              <Link
                href={"/s/" + profileId}
                className="inline-flex min-h-11 items-center gap-2 px-4 py-2 rounded-xl bg-surface border border-primary/20 text-foreground font-bold hover:bg-muted/40 transition shrink-0 whitespace-nowrap focus-visible:outline-secondary focus-visible:outline-2 text-sm active:scale-[0.98]"
              >
                Return to Bookshelf
              </Link>
            </motion.div>
          )}
      </div>
    </div>
  );
}

