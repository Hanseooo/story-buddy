"use client";

import { useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

export default function StopStory({ jobId, reviewId, epoch, ready, teacher, onStopped, onRefresh, onPending }: {
  jobId: string; reviewId: string; epoch: number; ready: boolean;
  teacher?: { subjectVersion: string; policyVersion: string };
  onStopped: () => void; onRefresh: () => void; onPending?: (pending: boolean) => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const keep = useRef<HTMLButtonElement>(null);
  const summary = useRef<HTMLHeadingElement>(null);
  const request = useRef<AbortController | null>(null);
  const body = useRef<string | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [stopped, setStopped] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const control = "min-h-11 rounded-xl px-4 py-2 font-bold text-primary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50";
  useEffect(() => () => { request.current?.abort(); onPending?.(false); }, [onPending]);
  useEffect(() => { if (message || stopped) summary.current?.focus(); }, [message, stopped]);
  function cancel() {
    dialog.current?.close();
    opener.current?.focus();
  }
  async function stop() {
    dialog.current?.close();
    body.current ??= JSON.stringify({ review_id: reviewId, expected_epoch: epoch,
      request_id: crypto.randomUUID(), confirmed: true,
      ...(teacher ? { subject_version: teacher.subjectVersion, policy_version: teacher.policyVersion,
        action: "stop", confirmed_criteria: [] } : {}) });
    const controller = new AbortController();
    setSubmitted(true);
    request.current = controller;
    setPending(true); onPending?.(true); setMessage(null);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) throw new Error();
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}${teacher
        ? `/teacher/jobs/${jobId}/moderation-review/decision` : `/jobs/${jobId}/stop`}`, {
        method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
        cache: "no-store", signal: controller.signal, body: body.current,
      });
      const current = await response.json();
      if (controller.signal.aborted) return;
      if (!response.ok) {
        setMessage(response.status === 409 ? "Your story has changed. Check its current status before deciding again."
          : "We couldn’t confirm the stop. Retry stop or check your story’s status.");
      } else if (current.status === "stopped") {
        setStopped(true); onStopped();
      } else setMessage("Your story has changed. Check its current status before deciding again.");
    } catch { if (!controller.signal.aborted) setMessage("We couldn’t confirm the stop. Retry stop or check your story’s status."); }
    finally { if (!controller.signal.aborted) { setPending(false); onPending?.(false); } }
  }
  return <section aria-label="Stop story" className="space-y-3">
    {stopped ? <h4 ref={summary} tabIndex={-1}>Story stopped. The writing is saved.</h4> : <>
      {message && <h4 ref={summary} tabIndex={-1} role="alert">{message}</h4>}
      {pending && <p role="status">Stopping this story…</p>}
      {submitted ? <>
        <button className={control} disabled={pending} onClick={() => void stop()}>Retry stop</button>
        <button className={control} disabled={pending} onClick={onRefresh}>Check story status</button>
      </> : <button ref={opener} className={control} disabled={!ready || pending} onClick={() => {
        dialog.current?.showModal(); keep.current?.focus();
      }}>Stop this story</button>}
      {!ready && <p role="status">Finishing the current step. Check story status before stopping.</p>}
    </>}
    <dialog ref={dialog} aria-labelledby={`stop-${jobId}`} onCancel={event => { event.preventDefault(); event.stopPropagation(); cancel(); }}
      className="m-auto w-[calc(100%_-_2rem)] max-w-md rounded-2xl bg-background p-6 text-foreground backdrop:bg-foreground/50">
      <h3 id={`stop-${jobId}`} className="text-xl font-bold">Stop making this book? Your writing will stay saved.</h3>
      <div className="mt-5 flex flex-wrap gap-3">
        <button ref={keep} className={control} onClick={cancel}>Keep waiting</button>
        <button className={control} onClick={() => void stop()}>Stop this story</button>
      </div>
    </dialog>
  </section>;
}
