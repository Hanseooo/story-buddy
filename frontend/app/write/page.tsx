"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function WriteStoryPage() {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/storybooks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    router.push(`/process/${data.job_id}`);
  }

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Write your story..."
        aria-label="story text"
      />
      <button type="submit" disabled={submitting}>
        {submitting ? "Sending..." : "Make my book"}
      </button>
    </form>
  );
}
