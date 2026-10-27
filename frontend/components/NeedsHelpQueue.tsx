"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabaseClient";

type HeldItem = {
  review_id: string; job_id: string; title: string | null; author: string | null;
  held_at: string; ready: boolean;
};
type Picture = { asset_id: string; label: string; state: "held" | "available" | "not_generated" | "unavailable" };
type Detail = {
  status: string; review_id: string | null; subject_version?: string; generation_epoch?: number;
  title?: string | null; author?: string | null; story_text?: string | null;
  ready?: boolean; pictures?: Picture[];
};
const control = "min-h-[44px] px-4 py-2 rounded-xl font-bold text-primary hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary disabled:opacity-50";

async function reviewFetch(path: string, signal: AbortSignal, options?: RequestInit) {
  const { data: { session } } = await supabase.auth.getSession();
  return fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    ...options, signal, cache: "no-store",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${session?.access_token}` },
  });
}

export default function NeedsHelpQueue({ classroomId, active, onCount, onBack }: {
  classroomId: string; active: boolean; onCount: (count: number) => void; onBack: () => void;
}) {
  const [items, setItems] = useState<HeldItem[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const opener = useRef<HTMLElement | null>(null);
  const queue = useRef<HTMLElement | null>(null);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setFailed(false);
    try {
      const response = await reviewFetch(`/teacher/classrooms/${classroomId}/moderation-reviews`, controller.signal);
      if (!response.ok) throw new Error("queue_unavailable");
      const rows: HeldItem[] = await response.json();
      if (controller.signal.aborted) return;
      setItems(rows);
      onCount(rows.length);
    } catch {
      if (!controller.signal.aborted) setFailed(true);
    }
  }, [classroomId, onCount]);

  useEffect(() => {
    // Match Books: refresh the authenticated read on mount and on external changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    const refresh = () => { if (!document.hidden) void load(); };
    document.addEventListener("visibilitychange", refresh);
    const channel = supabase.channel(`teacher-holds-${classroomId}`)
      .on("postgres_changes", { event: "*", schema: "public", table: "jobs", filter: `classroom_id=eq.${classroomId}` }, refresh)
      .subscribe();
    return () => {
      request.current?.abort();
      document.removeEventListener("visibilitychange", refresh);
      void supabase.removeChannel(channel);
    };
  }, [classroomId, load]);

  function close() {
    setSelected(null);
    if (opener.current?.isConnected) opener.current.focus();
    else queue.current?.focus();
    void load();
  }

  return (
    <section ref={queue} tabIndex={-1} hidden={!active} aria-label="Needs your help" className="focus-visible:outline-2 focus-visible:outline-primary">
      {failed ? <div role="alert" className="p-6 bg-surface rounded-2xl border border-primary/15">
        <p>Could not load stories needing your help.</p>
        <button className={control} onClick={() => void load()}>Try loading again</button>
      </div> : items === null ? <p role="status" className="p-6">Loading stories needing your help…</p>
        : items.length === 0 ? <div className="p-8 bg-surface rounded-2xl border border-primary/15">
          <p className="font-bold">No stories need your help</p>
          <button className={control} onClick={onBack}>Back to Books</button>
        </div> : <ul className="divide-y divide-primary/15 rounded-2xl border border-primary/15 bg-surface">
          {items.map(item => <li key={item.job_id} className="p-4 flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0 break-words">
              <p className="font-bold">{item.title || "Untitled story"}</p>
              <p className="text-sm text-foreground/70">{item.author || "Student"} · Waiting for teacher help</p>
              <p className="text-sm text-foreground/60">Held {new Date(item.held_at).toLocaleString()}</p>
            </div>
            <button className={control} aria-label={`Inspect ${item.title || "Untitled story"}`} onClick={event => {
              opener.current = event.currentTarget;
              setSelected(item.job_id);
            }}>Inspect story</button>
          </li>)}
        </ul>}
      {selected && <HeldStory key={selected} jobId={selected} onClose={close} />}
    </section>
  );
}

function HeldStory({ jobId, onClose }: { jobId: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(false);
    // Unmount pictures immediately on invalidation, including previously revealed blobs.
    setRevision(value => value + 1);
    try {
      const response = await reviewFetch(`/teacher/jobs/${jobId}/moderation-review`, controller.signal);
      if (!response.ok) {
        if ([401, 403, 404].includes(response.status)) setDetail(null);
        throw new Error("review_unavailable");
      }
      const current: Detail = await response.json();
      if (!controller.signal.aborted) setDetail(current);
    } catch {
      if (!controller.signal.aborted) setError(true);
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    dialog.current?.showModal();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
    const refresh = () => { if (!document.hidden) void load(); };
    document.addEventListener("visibilitychange", refresh);
    const channel = supabase.channel(`teacher-review-${jobId}`)
      .on("postgres_changes", { event: "*", schema: "public", table: "jobs", filter: `id=eq.${jobId}` }, refresh)
      .subscribe();
    return () => {
      request.current?.abort();
      document.removeEventListener("visibilitychange", refresh);
      void supabase.removeChannel(channel);
    };
  }, [jobId, load]);

  function close() {
    dialog.current?.close();
    onClose();
  }

  return <dialog ref={dialog} aria-labelledby="held-story-title" onCancel={event => { event.preventDefault(); close(); }}
    className="m-0 h-dvh w-screen max-h-none max-w-none border-0 bg-background text-foreground p-0 backdrop:bg-foreground/50">
    <div className="max-w-3xl mx-auto px-5 py-6 sm:px-8 space-y-6">
      <div className="flex flex-wrap justify-between gap-3 items-center">
        <h2 id="held-story-title" className="text-2xl font-bold">Needs your help</h2>
        <button autoFocus className={control} onClick={close}>Back to Needs your help</button>
      </div>
      <p className="text-sm text-foreground/70">Inspection leaves this story waiting. No picture is released to the child.</p>
      <button className={control} disabled={loading} onClick={() => void load()}>Refresh story status</button>
      {loading && <p role="status">Loading current story…</p>}
      {error && <div role="alert"><p>This review is unavailable or your access has changed.</p>
        <button className={control} onClick={() => void load()}>Try loading again</button></div>}
      {detail && <>
        <header><h3 className="text-2xl font-bold break-words">{detail.title || "Untitled story"}</h3>
          <p>{detail.author || "Student"}</p></header>
        {!detail.review_id ? <p role="status">This story has changed. Current status: {detail.status.replaceAll("_", " ")}.</p> : <>
          <p className="font-bold">Waiting for teacher help</p>
          {!detail.ready && <p role="status">Finishing the current step. Inspection is available.</p>}
          <section aria-label="Saved story" className="space-y-3">
            <h4 className="font-bold">Saved story</h4>
            <p className="whitespace-pre-wrap break-words leading-relaxed">{detail.story_text || "Saved story text is unavailable."}</p>
          </section>
          {!loading && !error && <section key={`${detail.review_id}-${detail.subject_version}-${revision}`} aria-label="Story pictures" className="space-y-6">
            <h4 className="font-bold">Story pictures</h4>
            {!detail.pictures?.length && <p>No generated pictures are available.</p>}
            {detail.pictures?.map(picture => <ReviewPicture key={picture.asset_id} jobId={jobId}
              reviewId={detail.review_id!} version={detail.subject_version!} picture={picture} onChanged={load} />)}
          </section>}
        </>}
      </>}
    </div>
  </dialog>;
}

function ReviewPicture({ jobId, reviewId, version, picture, onChanged }: {
  jobId: string; reviewId: string; version: string; picture: Picture; onChanged: () => void;
}) {
  const [revealed, setRevealed] = useState(picture.state === "available");
  const [attempt, setAttempt] = useState(0);
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (!revealed || picture.state === "not_generated") return;
    const controller = new AbortController();
    let objectUrl: string | null = null;
    async function load() {
      try {
        const base = `/teacher/jobs/${jobId}/moderation-review`;
        const response = picture.state === "held"
          ? await reviewFetch(`${base}/reveal`, controller.signal, { method: "POST", body: JSON.stringify({ review_id: reviewId, subject_version: version }) })
          : await reviewFetch(`${base}/images/${encodeURIComponent(picture.asset_id)}?review_id=${encodeURIComponent(reviewId)}&subject_version=${encodeURIComponent(version)}`, controller.signal);
        if ([401, 403, 409].includes(response.status)) { onChanged(); return; }
        if (!response.ok) throw new Error("image_unavailable");
        const bytes = await response.blob();
        if (controller.signal.aborted) return;
        objectUrl = URL.createObjectURL(bytes);
        setUrl(objectUrl);
      } catch {
        if (!controller.signal.aborted) setFailed(true);
      }
    }
    void load();
    return () => { controller.abort(); if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [jobId, reviewId, version, picture.asset_id, picture.state, revealed, attempt, onChanged]);

  return <figure className="space-y-3 border-t border-primary/15 pt-4">
    <figcaption className="break-words">{picture.label || "Story picture"}</figcaption>
    {picture.state === "unavailable" ? <div><p>Picture context unavailable.</p><button className={control} onClick={onChanged}>Try loading again</button></div>
      : picture.state === "not_generated" ? <p className="text-foreground/60">Picture not generated yet</p>
      : !revealed ? <div className="p-6 rounded-2xl bg-muted">
        <p className="font-bold">This picture needs your review</p>
        <button className={control} onClick={() => setRevealed(true)}>Show picture to review</button>
      </div> : failed ? <div role="alert">
        <p>Picture unavailable. Your story context is still here.</p>
        <button className={control} onClick={() => { setUrl(null); setFailed(false); setLoaded(false); setAttempt(value => value + 1); }}>Try loading again</button>
      </div> : <>
        {!loaded && <p role="status">Loading picture…</p>}
        {/* Guarded bytes only. No Storage URL is exposed to the browser. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        {url && <img src={url} alt={picture.label || "Story picture"} className="w-full h-auto rounded-2xl" onLoad={() => setLoaded(true)} onError={() => setFailed(true)} />}
      </>}
  </figure>;
}
