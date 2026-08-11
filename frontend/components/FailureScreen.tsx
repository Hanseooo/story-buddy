"use client";

import { useState, ReactNode } from "react";
import { useRouter, useParams } from "next/navigation";
import { Wrench, Gear, MagnifyingGlass, PencilSimple, BookOpen } from "@phosphor-icons/react";
import { motion } from "framer-motion";

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
  kind: FailureKind;
  inputText?: string;
  countable?: boolean;
};

function FailureCard({
  icon,
  title,
  subtext,
  buttonLabel,
  onAction,
  submitting,
  secondaryAction
}: {
  icon: ReactNode;
  title: string;
  subtext?: string;
  buttonLabel: string;
  onAction: () => void;
  submitting: boolean;
  secondaryAction?: ReactNode;
}) {
  return (
    <div className="w-full max-w-lg mx-auto bg-surface rounded-[24px] p-8 md:p-12 flex flex-col items-center gap-6 shadow-[0_10px_28px_rgba(49,85,217,0.12)] text-center my-8">
      <div className="text-primary opacity-80 mb-2">
        {icon}
      </div>
      <div className="flex flex-col gap-2">
        <h2 className="font-display text-3xl md:text-4xl text-foreground tracking-tight leading-[1.1] max-w-[320px] mx-auto">
          {title}
        </h2>
        {subtext && (
          <p className="font-kid text-lg text-foreground/80 max-w-[320px] mx-auto">
            {subtext}
          </p>
        )}
      </div>
      <div className="flex flex-col items-center w-full gap-4 mt-2">
        <button
          className="bg-primary text-surface rounded-2xl min-h-[44px] px-8 py-3 font-kid text-lg hover:-translate-y-[1px] transition-transform duration-150 disabled:opacity-50 disabled:hover:translate-y-0 disabled:cursor-not-allowed"
          onClick={onAction}
          disabled={submitting}
        >
          {buttonLabel}
        </button>
        {secondaryAction}
      </div>
    </div>
  );
}

export default function FailureScreen({
  kind,
  inputText = "",
  countable = true,
}: Props) {
  const router = useRouter();
  const { profileId } = useParams() as { profileId: string };
  const [submitting, setSubmitting] = useState(false);
  const chainCount = getChainCount();

  function submitRetry() {
    setSubmitting(true);
    fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: inputText }),
    })
      .then(res => (res.ok ? res.json() : null))
      .then(data => { if (data) router.push(`/s/${profileId}/process/${data.job_id}`); })
      .finally(() => setSubmitting(false));
  }

  const tryDifferent = chainCount >= 3 ? (
    <button
      className="mt-2 font-kid text-base text-primary underline hover:text-primary-deep transition-colors"
      onClick={() => router.push(`/s/${profileId}/write`)}
      disabled={submitting}
    >
      Want to try a different story instead?
    </button>
  ) : null;

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

  if (kind === "revise") {
    return (
      <FailureCard
        icon={<ReviseVignette />}
        title="Hmm..."
        subtext="Let's change a few words."
        buttonLabel="Change my words"
        submitting={submitting}
        onAction={() => {
          const count = countable ? bumpChain() : chainCount;
          console.log("sb:action", { action: "revise", kind, chain_count: count });
          try { sessionStorage.setItem(PREFILL_KEY, inputText); } catch { /* unavailable */ }
          router.push(`/s/${profileId}/write`);
        }}
        secondaryAction={tryDifferent}
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
        onAction={() => router.push(`/s/${profileId}/write`)}
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
      />
    );
  }

  // kind === "retry"
  return (
    <FailureCard
      icon={<RetryVignette />}
      title="Oops! The machine got stuck."
      subtext="That wasn't your fault."
      buttonLabel="Try again"
      submitting={submitting}
      onAction={() => {
        const count = countable ? bumpChain() : chainCount;
        console.log("sb:action", { action: "retry", kind, chain_count: count });
        submitRetry();
      }}
      secondaryAction={tryDifferent}
    />
  );
}

