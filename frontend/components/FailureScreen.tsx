"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";

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

  const tryDifferent = (
    <button
      className="rounded-2xl min-h-[44px] px-6 font-kid text-sm underline"
      onClick={() => router.push(`/s/${profileId}/write`)}
      disabled={submitting}
    >
      Want to try a different story instead?
    </button>
  );

  if (kind === "revise") {
    return (
      <div className="flex flex-col items-center gap-6 p-8">
        <p className="font-kid text-lg text-center">Hmm — let&apos;s change a few words.</p>
        <button
          className="rounded-2xl neo-border neo-shadow min-h-[44px] px-6 font-kid disabled:opacity-50"
          onClick={() => {
            const count = countable ? bumpChain() : chainCount;
            console.log("sb:action", { action: "revise", kind, chain_count: count });
            try { sessionStorage.setItem(PREFILL_KEY, inputText); } catch { /* unavailable */ }
            router.push(`/s/${profileId}/write`);
          }}
          disabled={submitting}
        >
          Change my words
        </button>
        {chainCount >= 3 && tryDifferent}
      </div>
    );
  }

  if (kind === "not-found") {
    return (
      <div className="flex flex-col items-center gap-6 p-8">
        <p className="font-kid text-lg text-center">We can&apos;t find that story.</p>
        <button
          className="rounded-2xl neo-border neo-shadow min-h-[44px] px-6 font-kid"
          onClick={() => router.push(`/s/${profileId}/write`)}
        >
          Write a new story
        </button>
      </div>
    );
  }

  if (kind === "asleep") {
    return (
      <div className="flex flex-col items-center gap-6 p-8">
        <p className="font-kid text-lg text-center">
          Your story went to sleep while you were away.
        </p>
        <button
          className="rounded-2xl neo-border neo-shadow min-h-[44px] px-6 font-kid disabled:opacity-50"
          onClick={submitRetry}
          disabled={submitting}
        >
          Make it again
        </button>
      </div>
    );
  }

  // kind === "retry"
  return (
    <div className="flex flex-col items-center gap-6 p-8">
      <p className="font-kid text-lg text-center">
        Oops! The story machine got stuck. That wasn&apos;t your fault.
      </p>
      <button
        className="rounded-2xl neo-border neo-shadow min-h-[44px] px-6 font-kid disabled:opacity-50"
        onClick={() => {
          const count = countable ? bumpChain() : chainCount;
          console.log("sb:action", { action: "retry", kind, chain_count: count });
          submitRetry();
        }}
        disabled={submitting}
      >
        Try again
      </button>
      {chainCount >= 3 && tryDifferent}
    </div>
  );
}
