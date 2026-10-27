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
  kind?: string; criteria?: string[]; policy_version?: string; current_policy_version?: string;
  settings_snapshot?: { theme_ids?: string[]; settings_version?: number };
  classifier_evidence?: { layer: string; model_id: string; instruction_version: string;
    outcome: string; checked_at: string | null; categories: string[]; reason: string | null }[];
};
type Criterion = { id: string; name: string; trigger: string; exception: string };
type Policy = { policy_version: string; audience: string; basis: string; scope: string;
  guidance: string; theme_scope: string; criteria: Criterion[]; optional_themes: Criterion[] };
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
      <ReviewCriteria />
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
          {!loading && !error && <section aria-label="Why this story is held" className="space-y-4 break-words">
            <h4 className="font-bold">Why this story is held</h4>
            <p>{detail.kind === "optional_themes" ? "Optional classroom themes" : "Shared safety"}</p>
            <p>Recorded criteria: {detail.criteria?.length ? detail.criteria.map(id => id.replaceAll("_", " ")).join(", ") : "Unavailable"}</p>
            <p>Policy at submission: {detail.policy_version || "Unavailable"}</p>
            <p>Current policy: {detail.current_policy_version || "Unavailable"}</p>
            <p>Captured settings version: {detail.settings_snapshot?.settings_version ?? "Unavailable"}</p>
            <p>Optional themes at submission: {detail.settings_snapshot?.theme_ids
              ? detail.settings_snapshot.theme_ids.map(id => id.replaceAll("_", " ")).join(", ") || "None enabled"
              : "Unavailable"}</p>
            {!detail.classifier_evidence?.length && <p>The recorded reason is unavailable</p>}
            {detail.classifier_evidence?.map((evidence, index) => <div key={index} className="space-y-2 border-t border-primary/15 pt-3">
              <h5 className="font-bold">{evidence.layer === "primary" ? "Primary classifier" : "Backstop classifier"}</h5>
              <dl className="space-y-1 text-sm">
                <dt>Recorded model</dt><dd>{evidence.model_id || "Unavailable"}</dd>
                <dt>Instruction version</dt><dd>{evidence.instruction_version || "Unavailable"}</dd>
                <dt>Recorded outcome</dt><dd>{evidence.outcome.replaceAll("_", " ")}</dd>
                <dt>Checked at</dt><dd>{evidence.checked_at ? new Date(evidence.checked_at).toLocaleString() : "Unavailable"}</dd>
                <dt>Recorded labels</dt><dd>{evidence.categories?.join(", ") || "Unavailable"}</dd>
              </dl>
              <p className="whitespace-pre-wrap">{evidence.reason?.trim() || "The recorded reason is unavailable"}</p>
            </div>)}
            <ReviewCriteria />
          </section>}
        </>}
      </>}
    </div>
  </dialog>;
}

function ReviewCriteria() {
  const panel = useRef<HTMLDetailsElement>(null);
  const request = useRef<AbortController | null>(null);
  const [policy, setPolicy] = useState<Policy | null>(null);
  const [loading, setLoading] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => () => request.current?.abort(), []);

  async function load() {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setFailed(false);
    try {
      const response = await reviewFetch("/teacher/moderation-policy", controller.signal);
      if (!response.ok) throw new Error("policy_unavailable");
      const current: Policy = await response.json();
      if (!controller.signal.aborted) setPolicy(current);
    } catch {
      if (!controller.signal.aborted) { setPolicy(null); setFailed(true); }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }

  function close() {
    if (panel.current) {
      panel.current.open = false;
      panel.current.querySelector("summary")?.focus();
    }
  }

  return <details ref={panel} className="py-4 space-y-4" onToggle={event => {
    if (event.currentTarget.open) void load();
  }} onKeyDown={event => {
    if (event.key === "Escape" && panel.current?.open) { event.preventDefault(); event.stopPropagation(); close(); }
  }}>
    <summary className={`${control} cursor-pointer`}>Review criteria</summary>
    <button className={control} onClick={close}>Close review criteria</button>
    {loading && <p role="status">Loading review criteria…</p>}
    {failed && <div role="alert"><p>Review criteria are unavailable.</p>
      <button className={control} onClick={() => void load()}>Try loading criteria again</button></div>}
    {!loading && policy && <div className="space-y-5 max-w-prose break-words">
      <p>{policy.basis}</p><p>{policy.audience}</p><p>Current policy: {policy.policy_version}</p>
      <p>{policy.scope}</p><p>{policy.guidance}</p>
      <h4 className="text-xl font-bold">Shared safety criteria</h4>
      {policy.criteria.map(criterion => <div key={criterion.id} className="space-y-2">
        <h5 className="font-bold">{criterion.name}</h5>
        <p className="text-sm font-bold">Hold boundary</p><p>{criterion.trigger}</p>
        <p className="text-sm font-bold">Permitted context and boundary examples</p><p>{criterion.exception}</p>
      </div>)}
      <h4 className="text-xl font-bold">Optional classroom themes</h4><p>{policy.theme_scope}</p>
      {policy.optional_themes.map(theme => <div key={theme.id} className="space-y-2">
        <h5 className="font-bold">{theme.name}</h5>
        <p className="text-sm font-bold">Trigger when enabled</p><p>{theme.trigger}</p>
        <p className="text-sm font-bold">Does not trigger</p><p>{theme.exception}</p>
      </div>)}
    </div>}
  </details>;
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
