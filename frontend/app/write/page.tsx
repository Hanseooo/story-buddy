"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { resetFailChain } from "@/components/FailureScreen";

const MIN_STORY_WORDS = 5;
const MAX_STORY_WORDS = 800;

const PREFILL_KEY = "sb.prefill";
const CHAIN_KEY = "sb.failChain";

function countWords(text: string): number {
  const trimmed = text.trim();
  return trimmed === "" ? 0 : trimmed.split(/\s+/).length;
}

export default function WriteStoryPage() {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [postError, setPostError] = useState(false);
  const [chainCount, setChainCount] = useState(0);
  const router = useRouter();

  useEffect(() => {
    let prefill: string | null = null;
    try {
      prefill = sessionStorage.getItem(PREFILL_KEY);
      if (prefill !== null) {
        sessionStorage.removeItem(PREFILL_KEY);
      }
    } catch { /* storage unavailable */ }

    if (prefill !== null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setText(prefill);
      try {
        setChainCount(Number(sessionStorage.getItem(CHAIN_KEY) ?? 0));
      } catch { /* unavailable */ }
    } else {
      resetFailChain();
    }
  }, []);

  const wordCount = countWords(text);
  const overCap = wordCount > MAX_STORY_WORDS;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setPostError(false);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
        setPostError(true);
        return;
      }
      const data = await res.json();
      router.push(`/process/${data.job_id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Write your story..."
        aria-label="story text"
      />
      <p aria-live="polite">
        {wordCount} words
        {overCap ? " — your story will be trimmed to fit" : ""}
      </p>
      {postError && (
        <p role="alert" className="text-destructive font-kid text-sm">
          Something went wrong — please try again.
        </p>
      )}
      {chainCount >= 3 && (
        <button
          type="button"
          className="text-sm underline font-kid"
          onClick={() => setText("")}
        >
          Want to try a different story instead?
        </button>
      )}
      <button type="submit" disabled={submitting || wordCount < MIN_STORY_WORDS}>
        {submitting ? "Sending..." : "Make my book"}
      </button>
    </form>
  );
}
