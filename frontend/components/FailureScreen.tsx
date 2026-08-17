"use client";

import { useState, ReactNode } from "react";
import { useRouter, useParams } from "next/navigation";
import { Wrench, Gear, MagnifyingGlass, PencilSimple, BookOpen, Copy, Check } from "@phosphor-icons/react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";
import { FailureReason } from "@/lib/types/jobs";

export type FailureKind = "revise" | "retry" | "not-found" | "asleep";

const CHAIN_KEY = "sb.failChain";
const PREFILL_KEY = "sb.prefill";

function getChainCount(): number {
  try { return Number(sessionStorage.getItem(CHAIN_KEY) ?? 0); } catch { return 0; }
}

function bumpChain(): number {
  const next = getChainCount() + 1;
  try { sessionStorage.setItem(CHAIN_KEY, String(next)); } catch { /* storage unavailable */ }
  return next;
}

export function resetFailChain() {
  try {
    sessionStorage.removeItem("sb.failChain");
    sessionStorage.removeItem("sb_fail_count");
  } catch { /* storage unavailable */ }
}

type Props = {
  kind?: FailureKind;
  reason?: FailureReason | string | null;
  jobId?: string;
  inputText?: string;
  stylePresetId?: string | null;
  countable?: boolean;
};

function StoryReference({ jobId }: { jobId: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(jobId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="mt-6 flex flex-col items-center gap-2">
      <div className="inline-flex items-center gap-2 font-mono text-sm text-[var(--foreground)]/70 bg-[var(--color-muted)]/30 px-3.5 py-2 rounded-xl">
        <span className="font-semibold text-xs tracking-wide uppercase text-[var(--foreground)]/50">Ref:</span>
        <span className="font-bold text-[var(--foreground)]">{jobId.slice(0, 8)}</span>
        <button
          type="button"
          aria-label="Copy story reference ID"
          onClick={handleCopy}
          className="ml-2 inline-flex items-center gap-1 min-h-[44px] min-w-[44px] px-2.5 py-1 text-xs font-kid font-bold text-[var(--color-primary)] hover:bg-[var(--color-primary)]/10 rounded-lg transition-colors focus-visible:outline-[var(--color-secondary)] focus-visible:outline-2"
        >
          {copied ? (
            <>
              <Check size={16} weight="bold" className="text-emerald-600" />
              <span className="text-emerald-700">Copied!</span>
            </>
          ) : (
            <>
              <Copy size={16} weight="bold" />
              <span>Copy full ID</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}

function FailureCard({
  icon,
  title,
  subtext,
  buttonLabel,
  onAction,
  submitting,
  secondaryAction,
  error,
  jobId,
  profileId,
}: {
  icon: ReactNode;
  title: string;
  subtext?: string;
  buttonLabel?: string | null;
  onAction?: () => void;
  submitting: boolean;
  secondaryAction?: ReactNode;
  error?: boolean;
  jobId?: string;
  profileId?: string;
}) {
  return (
    <div
      role="alert"
      className="w-full flex-1 min-h-[calc(100dvh-5rem)] bg-[var(--background)] flex flex-col items-center justify-center px-6 py-8 text-center overflow-x-hidden selection:bg-[var(--color-primary)] selection:text-[var(--color-surface)]"
    >
      <motion.div 
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-2xl mx-auto flex flex-col items-center"
      >
        {/* Visual Stage */}
        <div className="relative mb-8 md:mb-12 flex items-center justify-center w-full max-w-[280px]">
          <div className="absolute inset-0 bg-[var(--color-primary)]/10 rounded-full blur-2xl md:blur-3xl" aria-hidden="true" />
          <div className="absolute inset-4 bg-[var(--color-secondary)]/15 rounded-full blur-xl md:blur-2xl" aria-hidden="true" />
          
          <div className="relative z-10 scale-110 md:scale-125">
            {icon}
          </div>
        </div>

        {/* Copy */}
        <div className="flex flex-col gap-4">
          <h2 className="font-display text-4xl md:text-5xl font-extrabold text-[var(--foreground)] tracking-tight leading-tight">
            {title}
          </h2>
          {subtext && (
            <p className="font-kid text-xl md:text-2xl text-[var(--foreground)]/80 max-w-[40ch] mx-auto leading-relaxed">
              {subtext}
            </p>
          )}
        </div>

        {/* Story Ref */}
        {jobId && <StoryReference jobId={jobId} />}

        {/* Actions */}
        <div className="flex flex-col items-center w-full max-w-sm gap-5 mt-8 md:mt-10">
          {buttonLabel && onAction && (
            <button
              className="w-full bg-[var(--color-primary)] text-[var(--color-surface)] rounded-2xl min-h-[56px] px-8 py-4 font-kid font-extrabold text-lg shadow-sm hover:bg-[var(--color-primary-deep)] active:scale-[0.98] transition-all duration-150 disabled:opacity-50 disabled:hover:scale-100 disabled:cursor-not-allowed focus-visible:outline-[var(--color-secondary)] focus-visible:outline-3 focus-visible:outline-offset-3"
              onClick={onAction}
              disabled={submitting}
            >
              {buttonLabel}
            </button>
          )}
          {secondaryAction}
          {profileId && (
            <Link
              href={`/s/${profileId}`}
              className="inline-flex items-center gap-1.5 font-kid text-base font-bold text-[var(--foreground)]/60 hover:text-[var(--color-primary)] transition-colors focus-visible:outline-[var(--color-secondary)] focus-visible:outline-2 rounded-lg py-1 px-3 mt-1"
            >
              ← Back to Bookshelf
            </Link>
          )}
        </div>

        <div className="mt-6 min-h-[56px] flex items-start justify-center w-full max-w-sm">
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                role="alert"
                className="font-kid text-base text-[var(--color-destructive)] bg-[var(--color-destructive)]/10 px-5 py-3 rounded-xl leading-snug"
              >
                That didn&apos;t work either. You can try once more, or write something new.
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}

const ReviseVignette = () => (
  <div className="relative w-32 h-32 flex items-center justify-center mb-4">
    <div className="absolute w-24 h-28 bg-[var(--color-surface)] border border-[var(--color-primary)]/20 rounded-[12px] shadow-[0_10px_28px_rgba(49,85,217,0.12)] p-3 flex flex-col gap-3">
      <div className="w-full h-2.5 bg-[var(--color-muted)] rounded-full" />
      <div className="w-3/4 h-2.5 bg-[var(--color-muted)] rounded-full relative overflow-hidden">
        <motion.div 
          className="absolute inset-0 bg-[var(--color-destructive)]/40 origin-left"
          animate={{ scaleX: [0, 1, 0] }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
        />
      </div>
      <div className="w-5/6 h-2.5 bg-[var(--color-muted)] rounded-full" />
    </div>
    <motion.div
      className="absolute top-6 right-0 text-[var(--color-primary)] drop-shadow-md origin-bottom-left"
      animate={{ x: [-5, -25, -5], y: [0, 5, 0], rotate: [-10, -25, -10] }}
      transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
    >
      <PencilSimple size={40} weight="duotone" />
    </motion.div>
  </div>
);

const NotFoundVignette = () => (
  <div className="relative w-32 h-32 flex items-center justify-center mb-4">
    <div className="absolute w-24 h-24 border-2 border-dashed border-[var(--color-primary)]/30 rounded-[16px]" />
    <motion.div
      className="absolute text-[var(--color-primary)] drop-shadow-md"
      animate={{ 
        x: [-15, 15, 5, -15], 
        y: [-10, 10, -15, -10],
        rotate: [-10, 20, -10]
      }}
      transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
    >
      <MagnifyingGlass size={48} weight="duotone" />
    </motion.div>
  </div>
);

const AsleepVignette = () => (
  <div className="relative w-32 h-32 flex items-center justify-center mb-4">
    {[0, 1, 2].map((i) => (
      <motion.div
        key={i}
        className="absolute text-[var(--color-primary)]/50 font-kid font-bold text-xl"
        initial={{ opacity: 0, y: 0, x: 10 }}
        animate={{ opacity: [0, 1, 0], y: -40, x: [10, 25, 10] }}
        transition={{ repeat: Infinity, duration: 2.5, delay: i * 0.8, ease: "easeOut" }}
      >
        Z
      </motion.div>
    ))}
    <motion.div
      className="text-[var(--color-primary)] drop-shadow-sm mt-8"
      animate={{ scale: [0.95, 1.05, 0.95], y: [2, -2, 2] }}
      transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
    >
      <BookOpen size={64} weight="duotone" />
    </motion.div>
  </div>
);

const RetryVignette = () => (
  <div className="relative w-32 h-32 flex items-center justify-center mb-4">
    <div className="absolute w-24 h-24 bg-[var(--color-surface)] border border-[var(--color-primary)]/20 rounded-[16px] shadow-[0_10px_28px_rgba(49,85,217,0.12)] flex items-center justify-center overflow-hidden">
       <motion.div
         className="text-[var(--color-primary)] opacity-80"
         animate={{ rotate: [0, 45, 45, 35, 45, 0] }}
         transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
       >
         <Gear size={56} weight="duotone" />
       </motion.div>
    </div>
    <motion.div
      className="absolute bottom-0 left-2 text-[var(--color-secondary)] drop-shadow-md origin-center"
      animate={{ rotate: [0, 30, 0], x: [0, 5, 0], y: [0, -5, 0] }}
      transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
    >
      <Wrench size={40} weight="fill" />
    </motion.div>
  </div>
);

export default function FailureScreen({
  kind,
  reason,
  jobId,
  inputText = "",
  stylePresetId = null,
  countable = true,
}: Props) {
  const router = useRouter();
  const params = useParams();
  const profileId = (params as { profileId?: string })?.profileId;
  const [submitting, setSubmitting] = useState(false);
  const [retryFailed, setRetryFailed] = useState(false);
  const chainCount = getChainCount();

  async function submitRetry() {
    setSubmitting(true);
    setRetryFailed(false);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // /storybooks is auth-gated; without this header every retry was a silent 401.
          Authorization: `Bearer ${session?.access_token}`,
        },
        // The redo is a brand-new job, so the style has to be re-sent or a legacy row with null style
        // would fall back to the new "gouache" default and the child's book would be silently re-styled.
        body: JSON.stringify({ text: inputText, style_preset_id: stylePresetId ?? "cel" }),
      });
      if (!res.ok) {
        setRetryFailed(true);
        return;
      }
      const data = await res.json();
      router.push(profileId ? `/s/${profileId}/process/${data.job_id}` : `/process/${data.job_id}`);
    } catch {
      setRetryFailed(true);
    } finally {
      setSubmitting(false);
    }
  }

  const writeSomethingNew = (
    <button
      className="w-full rounded-2xl min-h-[56px] px-8 py-4 font-kid font-extrabold text-lg border-2 border-[var(--color-primary)]/25 text-[var(--color-primary)] hover:bg-[var(--color-primary)]/5 active:scale-[0.98] transition-all duration-150 disabled:opacity-50 focus-visible:outline-[var(--color-secondary)] focus-visible:outline-3 focus-visible:outline-offset-3"
      onClick={() => router.push(profileId ? `/s/${profileId}/write` : "/write")}
      disabled={submitting}
    >
      Write something new
    </button>
  );

  const tryDifferent = chainCount >= 3 ? (
    <button
      className="mt-2 font-kid text-lg text-[var(--color-primary)] underline hover:text-[var(--color-primary-deep)] transition-colors focus-visible:outline-[var(--color-secondary)] rounded-md"
      onClick={() => router.push(profileId ? `/s/${profileId}/write` : "/write")}
      disabled={submitting}
    >
      Want to try a different story instead?
    </button>
  ) : null;

  const handleRevise = () => {
    const count = countable ? bumpChain() : chainCount;
    console.log("sb:action", { action: "revise", kind, chain_count: count });
    try { sessionStorage.setItem(PREFILL_KEY, inputText); } catch { /* unavailable */ }
    router.push(profileId ? `/s/${profileId}/write` : "/write");
  };

  // A machine failure is never the child's fault, so both ways out are offered side by side from
  // the first failure. Deliberately NOT auto-retried: a redo is a whole new job at a 900s timeout
  // with fresh paid images (main.py:110), and the commonest machine reason in this pipeline is
  // that timeout itself (run_worker.py:30) — the case most likely to repeat.
  const handleRetry = () => {
    const count = countable ? bumpChain() : chainCount;
    console.log("sb:action", { action: "retry", kind, chain_count: count });
    submitRetry();
  };

  // If the row carries a `reason` at all, use the safe reason taxonomy (spec §5). `null` counts:
  // spec §3 requires old, null, and unrecognized values to render as `system_error`, so only an
  // omitted prop (a frontend-side failure with no job row behind it) falls through to `kind`.
  if (reason !== undefined) {
    if (reason === "child_text") {
      return (
        <FailureCard
          icon={<ReviseVignette />}
          title="Some words need changing before we can make this book."
          buttonLabel="Change my words"
          submitting={submitting}
          onAction={handleRevise}
          secondaryAction={tryDifferent}
          jobId={jobId}
          profileId={profileId}
        />
      );
    }
    if (reason === "character_safety") {
      return (
        <FailureCard
          icon={<RetryVignette />}
          title="We couldn’t safely use the character picture we made. Your words aren’t in trouble."
          buttonLabel={submitting ? "Starting…" : "Make the story again"}
          submitting={submitting}
          onAction={handleRetry}
          secondaryAction={writeSomethingNew}
          error={retryFailed}
          jobId={jobId}
          profileId={profileId}
        />
      );
    }
    if (reason === "scene_safety") {
      return (
        <FailureCard
          icon={<RetryVignette />}
          title="One of the pictures we made couldn’t be used."
          buttonLabel={submitting ? "Starting…" : "Make the story again"}
          submitting={submitting}
          onAction={handleRetry}
          secondaryAction={writeSomethingNew}
          error={retryFailed}
          jobId={jobId}
          profileId={profileId}
        />
      );
    }
    if (reason === "service_busy") {
      return (
        <FailureCard
          icon={<RetryVignette />}
          title="The story-making service is busy right now."
          buttonLabel={submitting ? "Starting…" : "Try again"}
          submitting={submitting}
          onAction={handleRetry}
          secondaryAction={writeSomethingNew}
          error={retryFailed}
          jobId={jobId}
          profileId={profileId}
        />
      );
    }
    if (reason === "worker_stopped") {
      return (
        <FailureCard
          icon={<RetryVignette />}
          title="The story maker stopped before it finished."
          buttonLabel={submitting ? "Starting…" : "Try again"}
          submitting={submitting}
          onAction={handleRetry}
          secondaryAction={writeSomethingNew}
          error={retryFailed}
          jobId={jobId}
          profileId={profileId}
        />
      );
    }
    if (reason === "service_limit") {
      return (
        <FailureCard
          icon={<RetryVignette />}
          title="The story-making allowance has run out."
          subtext="Ask a teacher to help."
          buttonLabel={null}
          submitting={submitting}
          secondaryAction={writeSomethingNew}
          jobId={jobId}
          profileId={profileId}
        />
      );
    }
    if (reason === "book_limit") {
      return (
        <FailureCard
          icon={<RetryVignette />}
          title="This book reached its picture-making limit."
          subtext="Ask a teacher to help."
          buttonLabel={null}
          submitting={submitting}
          secondaryAction={writeSomethingNew}
          jobId={jobId}
          profileId={profileId}
        />
      );
    }
    // Fallback: system_error and unknown/legacy values ("machine", null, etc.)
    return (
      <FailureCard
        icon={<RetryVignette />}
        title="Something interrupted your story."
        buttonLabel={submitting ? "Starting…" : "Try again"}
        submitting={submitting}
        onAction={handleRetry}
        secondaryAction={writeSomethingNew}
        error={retryFailed}
        jobId={jobId}
        profileId={profileId}
      />
    );
  }

  // Fallback to legacy `kind` prop when `reason` is not specified
  if (kind === "revise") {
    return (
      <FailureCard
        icon={<ReviseVignette />}
        title="Hmm..."
        subtext="Let's change a few words."
        buttonLabel="Change my words"
        submitting={submitting}
        onAction={handleRevise}
        secondaryAction={tryDifferent}
        jobId={jobId}
        profileId={profileId}
      />
    );
  }

  if (kind === "not-found") {
    return (
      <FailureCard
        icon={<NotFoundVignette />}
        title="We can't find that story."
        buttonLabel="Write a new story"
        submitting={submitting}
        onAction={() => router.push(profileId ? `/s/${profileId}/write` : "/write")}
        jobId={jobId}
        profileId={profileId}
      />
    );
  }

  if (kind === "asleep") {
    return (
      <FailureCard
        icon={<AsleepVignette />}
        title="Your story went to sleep."
        subtext="You were away for a little while!"
        buttonLabel="Make it again"
        submitting={submitting}
        onAction={submitRetry}
        secondaryAction={writeSomethingNew}
        error={retryFailed}
        jobId={jobId}
        profileId={profileId}
      />
    );
  }

  // Default kind === "retry"
  return (
    <FailureCard
      icon={<RetryVignette />}
      title="Oops! The machine got stuck."
      subtext="That wasn't your fault. Want to make the same story again?"
      buttonLabel={submitting ? "Starting…" : "Make this story again"}
      submitting={submitting}
      onAction={handleRetry}
      secondaryAction={writeSomethingNew}
      error={retryFailed}
      jobId={jobId}
      profileId={profileId}
    />
  );
}
