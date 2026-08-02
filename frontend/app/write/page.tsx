"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

// Mirrors backend/app/config.py's MIN_STORY_WORDS / MAX_STORY_WORDS. kid-flow-ui owns the
// copy shown for both the 422 and the truncated-book message; this counter is UX only —
// the backend is the actual enforcement point.
const MIN_STORY_WORDS = 5;
const MAX_STORY_WORDS = 800;

function countWords(text: string): number {
  const trimmed = text.trim();
  return trimmed === "" ? 0 : trimmed.split(/\s+/).length;
}

export default function WriteStoryPage() {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  const wordCount = countWords(text);
  const overCap = wordCount > MAX_STORY_WORDS;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!res.ok) {
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
      <button type="submit" disabled={submitting || wordCount < MIN_STORY_WORDS}>
        {submitting ? "Sending..." : "Make my book"}
      </button>
    </form>
  );
}
