"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { clearStoppedWriting, saveStoppedWriting, type SavedWriting } from "@/lib/stoppedWriting";

export default function StoppedStory({ jobId, profileId }: { jobId: string; profileId: string }) {
  const [writing, setWriting] = useState<SavedWriting | null>(null);
  const [error, setError] = useState(false);
  const [fallback, setFallback] = useState(false);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const heading = useRef<HTMLHeadingElement>(null);
  const router = useRouter();
  useEffect(() => { heading.current?.focus(); }, []);
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session) { clearStoppedWriting(); throw new Error(); }
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/state`, {
          headers: { Authorization: `Bearer ${session.access_token}` }, cache: "no-store", signal: controller.signal,
        });
        if ([401, 403, 404].includes(response.status)) { clearStoppedWriting(); setWriting(null); }
        if (!response.ok) throw new Error();
        const state = await response.json();
        if (!controller.signal.aborted) {
          if (state.status !== "stopped" || !state.saved_writing) throw new Error();
          setWriting(state.saved_writing); setError(false);
        }
      } catch { if (!controller.signal.aborted) setError(true); }
    })();
    return () => controller.abort();
  }, [jobId, revision]);
  function reuse() {
    if (!writing) return;
    setFallback(true);
    try {
      saveStoppedWriting(profileId, jobId, writing);
      router.push(`/s/${profileId}/write?reuse=${encodeURIComponent(jobId)}`);
    } catch { /* Keep the saved text and copy action on this page. */ }
  }
  const control = "inline-flex items-center justify-center min-h-11 rounded-2xl bg-primary px-6 py-3 font-bold text-on-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50";
  return <section className="mx-auto flex max-w-xl flex-col items-center gap-6 p-6 text-center">
    <h1 ref={heading} tabIndex={-1} className="font-display text-3xl font-extrabold text-primary">This book has stopped. Your writing is saved.</h1>
    {error ? <div role="alert"><p>We couldn’t load your saved writing.</p>
      <button className={control} onClick={() => setRevision(value => value + 1)}>Try loading again</button></div>
      : !writing && <p role="status">Loading your saved writing…</p>}
    <Link className={control} href={`/s/${profileId}`}>Back to my books</Link>
    <button className={control} disabled={!writing || error} onClick={reuse}>Use my writing</button>
    {fallback && writing && <div className="w-full space-y-3">
      <p>If the new story form hasn’t opened, you can copy your writing here.</p>
      <textarea aria-label="Saved writing" readOnly value={writing.text} className="min-h-48 w-full rounded-xl border border-primary/20 p-4" />
      <button className={control} onClick={async () => {
        try { await navigator.clipboard.writeText(writing.text); setCopyMessage("Writing copied."); }
        catch { setCopyMessage("We couldn’t copy it. Select your writing above to copy it yourself."); }
      }}>Copy writing</button>
      {copyMessage && <p role="status">{copyMessage}</p>}
    </div>}
  </section>;
}
