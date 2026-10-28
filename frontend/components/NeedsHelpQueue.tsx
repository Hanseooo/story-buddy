"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import StopStory from "@/components/StopStory";

type HeldItem = {
  review_id: string; job_id: string; title: string | null; author: string | null;
  held_at: string; ready: boolean;
  continuation_pending?: boolean;
};
type Picture = { asset_id: string; label: string; state: "held" | "available" | "not_generated" | "unavailable" };
type Detail = {
  status: string; review_id: string | null; subject_version?: string; generation_epoch?: number;
  title?: string | null; author?: string | null; story_text?: string | null; subject_title?: string | null;
  ready?: boolean; pictures?: Picture[];
  kind?: string; criteria?: string[]; policy_version?: string; current_policy_version?: string;
  detected_themes?: { theme_id: string; reason: string }[];
  theme_check?: { model_id: string; instruction_version: string } | null;
  settings_snapshot?: { theme_ids?: string[]; settings_version?: number; withdrawal_epoch?: number };
  classifier_evidence?: { layer: string; model_id: string; instruction_version: string;
    outcome: string; checked_at: string | null; categories: string[]; reason: string | null }[];
  clearances?: { review_id: string; subject_version: string; label: string }[];
  withdraws_review_id?: string | null; dispatch_state?: string | null;
  replacement_available?: boolean; replacement_disabled_reason?: string | null;
  pending_command?: { review_id: string; subject_version: string; expected_epoch: number; request_id: string;
    action: "allow" | "replace"; policy_version: string; confirmed_criteria: string[]; confirmed: true } | null;
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
      onCount(rows.filter(row => !row.continuation_pending).length);
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
              <p className="text-sm text-foreground/70">{item.author || "Student"} · {item.continuation_pending ? "Decision saved. Delivery pending" : "Waiting for teacher help"}</p>
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
  const [inspected, setInspected] = useState(false);
  const [pending, setPending] = useState(false);
  const [stopped, setStopped] = useState(false);
  const request = useRef<AbortController | null>(null);
  const load = useCallback(async () => {
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(false);
    setInspected(false);
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
      {!stopped && <p className="text-sm text-foreground/70">Inspection leaves this story waiting. No picture is released to the child.</p>}
      <button className={control} disabled={loading || pending} onClick={() => void load()}>Refresh story status</button>
      {loading && <p role="status">Loading current story…</p>}
      {error && <div role="alert"><p>This review is unavailable or your access has changed.</p>
        <button className={control} onClick={() => void load()}>Try loading again</button></div>}
      {detail && <>
        <header><h3 className="text-2xl font-bold break-words">{detail.title || "Untitled story"}</h3>
          <p>{detail.author || "Student"}</p></header>
        {!detail.review_id ? <>
          <p role="status">This story has changed. Current status: {detail.status.replaceAll("_", " ")}.</p>
          {detail.pending_command && <>
            <p className="whitespace-pre-wrap break-words leading-relaxed">{detail.story_text || "Saved story text is unavailable."}</p>
            <ContinueSavedDecision jobId={jobId} command={detail.pending_command} onChanged={load} />
          </>}
        </> : <>
          {!stopped && <>
          <p className="font-bold">Waiting for teacher help</p>
          <p>The whole book stays hidden while this review is open. Earlier clearances cannot be withdrawn here. If uncertain, leave this story waiting.</p>
          {!detail.ready && <p role="status">Finishing the current step. Inspection is available.</p>}
          {!detail.ready && detail.withdraws_review_id && ["pending", "failed"].includes(detail.dispatch_state || "") &&
            <FinishWithdrawal jobId={jobId} detail={detail} onChanged={load} />}
          <section aria-label="Saved story" className="space-y-3">
            <h4 className="font-bold">Saved story</h4>
            <p className="whitespace-pre-wrap break-words leading-relaxed">{detail.story_text || "Saved story text is unavailable."}</p>
          </section>
          {detail.kind === "title" && <section aria-label="Title needing review" className="space-y-3">
            <h4 className="font-bold">Title needing review</h4>
            <p className="whitespace-pre-wrap break-words leading-relaxed">{detail.subject_title || "Saved title is unavailable."}</p>
          </section>}
          {!loading && !error && <section key={`${detail.review_id}-${detail.subject_version}-${revision}`} aria-label="Story pictures" className="space-y-6">
            <h4 className="font-bold">Story pictures</h4>
            {!detail.pictures?.length && <p>No generated pictures are available.</p>}
            {detail.pictures?.map(picture => <ReviewPicture key={picture.asset_id} jobId={jobId}
              reviewId={detail.review_id!} version={detail.subject_version!} picture={picture} onChanged={load}
              onInspected={picture.state === "held" ? setInspected : undefined} />)}
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
            {detail.kind === "optional_themes" && <>
              <p>These classroom preferences request extra review. They do not label the story unsafe. Shared safety checks still apply.</p>
              {detail.detected_themes?.map(theme => <p key={theme.theme_id}>{theme.theme_id.replaceAll("_", " ")}: {theme.reason}</p>)}
              <p>Recorded detector: {detail.theme_check?.model_id || "Unavailable"}</p>
              <p>Instruction version: {detail.theme_check?.instruction_version || "Unavailable"}</p>
            </>}
            {detail.kind !== "optional_themes" && !detail.classifier_evidence?.length && <p>The recorded reason is unavailable</p>}
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
          {!loading && !error && (detail.kind === "scene_image" || detail.kind === "character_reference" || detail.kind === "story_text" || detail.kind === "title" || detail.kind === "optional_themes") && <ResolveSubject
            key={`${detail.review_id}-${detail.subject_version}-${detail.generation_epoch}-${revision}`}
            jobId={jobId} detail={detail} inspected={detail.kind === "title" ? !!detail.subject_title : detail.kind === "story_text" || detail.kind === "optional_themes" ? !!detail.story_text : inspected}
            busy={pending} onPending={setPending} />}
          </>}
          {!loading && !error && <StopStory jobId={jobId} reviewId={detail.review_id}
            epoch={detail.generation_epoch!} ready={!!detail.ready && !pending}
            teacher={{ subjectVersion: detail.subject_version!, policyVersion: detail.current_policy_version || "" }}
            onStopped={() => setStopped(true)} onRefresh={load} onPending={setPending} />}
        </>}
      </>}
    </div>
  </dialog>;
}

function ContinueSavedDecision({ jobId, command, onChanged }: {
  jobId: string; command: NonNullable<Detail["pending_command"]>; onChanged: () => void;
}) {
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const summary = useRef<HTMLHeadingElement>(null);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => { if (message || success) summary.current?.focus(); }, [message, success]);
  async function retry() {
    const controller = new AbortController();
    request.current = controller;
    setPending(true); setMessage(null);
    try {
      const response = await reviewFetch(`/teacher/jobs/${jobId}/moderation-review/decision`, controller.signal,
        { method: "POST", body: JSON.stringify(command) });
      const current = await response.json();
      if (controller.signal.aborted) return;
      if (!response.ok || ["pending", "failed"].includes(current.dispatch_state)) setMessage("Could not finish delivery. Retry the saved decision or refresh story status.");
      else if (["queued", "running"].includes(current.status)) setSuccess(true);
      else onChanged();
    } catch { if (!controller.signal.aborted) setMessage("Could not finish delivery. Retry the saved decision or refresh story status."); }
    finally { if (!controller.signal.aborted) setPending(false); }
  }
  return <section aria-label="Saved safety decision" className="space-y-3">
    {success ? <h4 ref={summary} tabIndex={-1} className="font-bold focus-visible:outline-2 focus-visible:outline-primary">Story continuing</h4> : <>
      <p>Your decision is saved. Continue story retries its pending delivery.</p>
      {message && <h4 ref={summary} tabIndex={-1} role="alert">{message}</h4>}
      <button className={control} disabled={pending} onClick={() => void retry()}>{pending ? "Continuing…" : "Continue story"}</button>
    </>}
  </section>;
}

function ResolveSubject({ jobId, detail, inspected, busy, onPending }: {
  jobId: string; detail: Detail; inspected: boolean; busy: boolean; onPending: (pending: boolean) => void;
}) {
  const themes = detail.kind === "optional_themes";
  const subject = themes ? "themes" : detail.kind === "title" ? "title" : detail.kind === "story_text" ? "story text" : "picture";
  const [confirmed, setConfirmed] = useState<string[]>([]);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitted, setSubmitted] = useState<"allow" | "replace" | null>(null);
  const [outcome, setOutcome] = useState("Story continuing");
  const summary = useRef<HTMLHeadingElement>(null);
  const request = useRef<AbortController | null>(null);
  const body = useRef<string | null>(null);
  useEffect(() => () => { request.current?.abort(); onPending(false); }, [onPending]);
  useEffect(() => { if (message || success) summary.current?.focus(); }, [message, success]);

  async function decide(action: "allow" | "replace") {
    if (pending) return;
    body.current ??= JSON.stringify({ review_id: detail.review_id, subject_version: detail.subject_version,
      expected_epoch: detail.generation_epoch, request_id: crypto.randomUUID(), action,
      policy_version: detail.current_policy_version, confirmed_criteria: action === "allow" ? confirmed : [], confirmed: true });
    setSubmitted(action);
    const controller = new AbortController();
    request.current = controller;
    setPending(true); onPending(true); setMessage(null);
    try {
      const response = await reviewFetch(`/teacher/jobs/${jobId}/moderation-review/decision`, controller.signal,
        { method: "POST", body: body.current });
      const current = await response.json();
      if (controller.signal.aborted) return;
      if (!response.ok) {
        setMessage(response.status === 409 ? "This review has changed or cannot continue. Refresh story status to review it again."
          : "Could not confirm the saved decision. Continue story retries the same request, or refresh story status.");
      } else if (current.dispatch_state === "pending" || current.dispatch_state === "failed") {
        setMessage("Your decision is saved. Delivery is pending. Choose Continue story to retry it.");
      } else {
        setOutcome(current.status === "complete" ? "Story complete" : current.status === "awaiting_teacher"
          ? "Story waiting for teacher help" : ["queued", "running"].includes(current.status)
            ? "Story continuing" : `Current story status: ${String(current.status).replaceAll("_", " ")}`);
        setSuccess(true);
      }
    } catch {
      if (!controller.signal.aborted) setMessage("Could not confirm the saved decision. Continue story retries the same request, or refresh story status.");
    } finally {
      if (!controller.signal.aborted) { setPending(false); onPending(false); }
    }
  }

  return <section aria-label={`Resolve the inspected ${subject}`} className="space-y-4 border-t border-primary/15 pt-5">
    {success ? <h4 ref={summary} tabIndex={-1} className="font-bold text-lg focus-visible:outline-2 focus-visible:outline-primary">{outcome}</h4> : <>
      <h4 className="font-bold text-lg">{themes ? "Accept these themes together" : `Allow this exact ${subject}`}</h4>
      <p>If you are uncertain, leave this story waiting and return later. {themes ? "Accepting themes" : "Allowing safety clearance"} does not approve classroom sharing.</p>
      {detail.kind === "title" ? <p>Read the saved title above. Allowing starts the story with this exact title. The story text and every generated picture receive their own safety checks.</p>
        : themes ? <p>Read the saved story and detected themes above. Acceptance covers these themes together for this submission only. They will not prompt another theme review on later pages. Shared safety checks still apply to every picture.</p>
        : detail.kind === "story_text" ? <p>Read the saved story above. Allowing continues with this unchanged text. Every generated picture receives its own safety checks.</p>
        : !inspected && <p>Show the picture and wait for it to load before allowing it.</p>}
      {!detail.ready && <p role="status">Finishing the current step. Refresh story status before deciding.</p>}
      <fieldset disabled={busy || pending || !!submitted} className="space-y-2">
        <legend className="font-bold">After inspection, confirm each named review criterion</legend>
        {detail.criteria?.map(id => <label key={id} className="flex items-center gap-3 min-h-[44px]">
          <input type="checkbox" checked={confirmed.includes(id)} onChange={event => setConfirmed(values =>
            event.target.checked ? [...values, id] : values.filter(value => value !== id))} />
          {themes ? `I accept ${id.replaceAll("_", " ")} in this submission` : `This ${subject} meets ${id.replaceAll("_", " ")}`}
        </label>)}
      </fieldset>
      {message && <h4 ref={summary} tabIndex={-1} role="alert" className="font-bold focus-visible:outline-2 focus-visible:outline-primary">{message}</h4>}
      {pending && <p role="status">Saving your decision…</p>}
      <button className={control} disabled={busy || pending || !detail.ready || (!submitted &&
        (!inspected || !detail.current_policy_version || !detail.criteria?.length || confirmed.length !== detail.criteria.length))}
        onClick={() => void decide(submitted || "allow")}>{pending ? "Saving…" : submitted ? "Continue story" : themes ? "Accept these themes" : `Allow this ${subject}`}</button>
      {!submitted && !themes && detail.kind !== "story_text" && detail.kind !== "title" && <>
        <p>{detail.kind === "character_reference"
          ? "A replacement keeps the character description, style and any chosen emphasis. It uses the book’s one reference replacement and receives fresh checks. Other details may change."
          : "A replacement keeps the scene, approved references and style. It uses one remaining picture allowance and receives fresh checks. Other details may change."}</p>
        {!detail.replacement_available && <p id="replacement-unavailable">{detail.replacement_disabled_reason === "image_budget_exhausted"
          ? "The image budget is used up. You can still inspect, leave waiting, allow or stop this story."
          : detail.replacement_disabled_reason === "replacement_already_used"
            ? `${detail.kind === "character_reference" ? "This book has used its reference replacement" : "This scene has used its replacement"}. You can still inspect, leave waiting, allow or stop this story.`
            : detail.replacement_disabled_reason === "dependent_scenes_exist"
              ? "Story pictures already depend on this reference. You can allow this exact reference, leave waiting or stop and start a new story."
              : "Replacement is unavailable. Refresh story status or leave this story waiting."}</p>}
        <button className={control} aria-describedby={!detail.replacement_available ? "replacement-unavailable" : undefined}
          disabled={busy || pending || !detail.ready || !inspected || !detail.replacement_available}
          onClick={() => void decide("replace")}>Request replacement picture</button>
      </>}
    </>}
  </section>;
}

function FinishWithdrawal({ jobId, detail, onChanged }: { jobId: string; detail: Detail; onChanged: () => void }) {
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  async function retry() {
    const controller = new AbortController();
    request.current = controller;
    setPending(true); setFailed(false);
    try {
      const response = await reviewFetch(`/teacher/jobs/${jobId}/moderation-review/withdraw`, controller.signal, {
        method: "POST", body: JSON.stringify({ clearance_review_id: detail.withdraws_review_id,
          subject_version: detail.subject_version, expected_epoch: detail.settings_snapshot!.withdrawal_epoch! - 1,
          request_id: detail.review_id, confirmed: true }),
      });
      if (!response.ok) throw new Error("withdrawal_unavailable");
      if (!controller.signal.aborted) onChanged();
    } catch { if (!controller.signal.aborted) setFailed(true); }
    finally { if (!controller.signal.aborted) setPending(false); }
  }
  return <div className="space-y-2">
    <p>The book is hidden. Returning it to review still needs delivery.</p>
    {failed && <p role="alert">Could not finish delivery. Your saved withdrawal remains in place.</p>}
    <button className={control} disabled={pending || detail.settings_snapshot?.withdrawal_epoch === undefined}
      onClick={() => void retry()}>{pending ? "Retrying…" : "Finish returning to review"}</button>
  </div>;
}

export function ClearanceWithdrawal({ jobId, onPending, onWithdrawn }: {
  jobId: string; onPending: (pending: boolean) => void; onWithdrawn: () => void;
}) {
  const [detail, setDetail] = useState<Detail | null>(null);
  const [failed, setFailed] = useState(false);
  const [selected, setSelected] = useState<NonNullable<Detail["clearances"]>[number] | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [outcome, setOutcome] = useState("Story returned to teacher review");
  const [submitted, setSubmitted] = useState(false);
  const [retry, setRetry] = useState(0);
  const request = useRef<AbortController | null>(null);
  const command = useRef<string | null>(null);
  const summary = useRef<HTMLHeadingElement>(null);
  const keep = useRef<HTMLButtonElement>(null);
  const opener = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    request.current = controller;
    async function load() {
      try {
        const response = await reviewFetch(`/teacher/jobs/${jobId}/moderation-review`, controller.signal);
        if (!response.ok) throw new Error("clearances_unavailable");
        const current: Detail = await response.json();
        if (!controller.signal.aborted) { setDetail(current); setFailed(false); }
      } catch { if (!controller.signal.aborted) setFailed(true); }
    }
    void load();
    return () => { request.current?.abort(); onPending(false); };
  }, [jobId, retry, onPending]);
  useEffect(() => { if (selected) keep.current?.focus(); else opener.current?.focus(); }, [selected]);
  useEffect(() => { if (message || success) summary.current?.focus(); }, [message, success]);

  async function withdraw() {
    if (!selected || pending) return;
    command.current ??= JSON.stringify({ clearance_review_id: selected.review_id, subject_version: selected.subject_version,
      expected_epoch: detail?.generation_epoch, request_id: crypto.randomUUID(), confirmed: true });
    setSubmitted(true);
    const controller = new AbortController();
    request.current = controller;
    setPending(true); onPending(true); setMessage(null);
    try {
      const response = await reviewFetch(`/teacher/jobs/${jobId}/moderation-review/withdraw`, controller.signal,
        { method: "POST", body: command.current });
      const current = await response.json();
      if (controller.signal.aborted) return;
      if (!response.ok) setMessage("Could not confirm withdrawal. Retry the same withdrawal or reload safety clearance status.");
      else {
        if (current.status === "awaiting_teacher") {
          onWithdrawn();
          if (["pending", "failed"].includes(current.dispatch_state)) setMessage("The book is hidden and returned to review. Retry withdrawal to finish delivery.");
          else setSuccess(true);
        } else {
          setOutcome(`Current story status: ${String(current.status).replaceAll("_", " ")}`);
          setSuccess(true);
        }
      }
    } catch {
      if (!controller.signal.aborted) setMessage("Could not confirm withdrawal. Retry the same withdrawal or reload safety clearance status.");
    } finally { if (!controller.signal.aborted) { setPending(false); onPending(false); } }
  }

  return <section aria-label="Safety clearances" className="space-y-3 border-t border-primary/15 pt-4">
    {success ? <h3 ref={summary} tabIndex={-1} className="font-bold focus-visible:outline-2 focus-visible:outline-primary">{outcome}</h3> : <>
      <h3 className="font-bold">Safety clearances</h3>
      {failed ? <p role="alert">Safety clearance status is unavailable.</p> : !detail ? <p role="status">Loading safety clearances…</p>
        : !detail.clearances?.length ? <p>No current safety clearances to withdraw.</p> : <div hidden={!!selected}>{detail.clearances.map(clearance =>
          <button key={clearance.review_id} className={control} onClick={event => {
            opener.current = event.currentTarget; command.current = null; setSubmitted(false); setMessage(null); setSelected(clearance);
          }}>Withdraw clearance for {clearance.label}</button>)}</div>}
      {selected && <div role="group" aria-label="Confirm safety withdrawal" className="space-y-3" onKeyDown={event => {
        if (event.key === "Escape" && !pending && !message) {
          event.preventDefault(); event.stopPropagation(); setSelected(null); opener.current?.focus();
        }
      }}>
        <p>Withdrawing clearance hides the whole book from the child and classmates, stops further generation, and clears classroom sharing approval. Writing and review history stay saved. Copies already viewed or downloaded cannot be recalled.</p>
        <button ref={keep} className={control} disabled={pending} onClick={() => {
          setSelected(null); setMessage(null); command.current = null;
          if (submitted) setRetry(value => value + 1);
        }}>{submitted ? "Back to clearance status" : "Keep clearance"}</button>
        <button className={control} disabled={pending} onClick={() => void withdraw()}>{pending ? "Withdrawing…" : "Withdraw safety clearance"}</button>
      </div>}
      {message && <h3 ref={summary} role="alert" tabIndex={-1} className="font-bold focus-visible:outline-2 focus-visible:outline-primary">{message}</h3>}
      <button className={control} disabled={pending} onClick={() => { setSelected(null); setMessage(null); setRetry(value => value + 1); }}>Reload safety clearance status</button>
    </>}
  </section>;
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

function ReviewPicture({ jobId, reviewId, version, picture, onChanged, onInspected }: {
  jobId: string; reviewId: string; version: string; picture: Picture; onChanged: () => void;
  onInspected?: (loaded: boolean) => void;
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
        {url && <img src={url} alt={picture.label || "Story picture"} className="w-full h-auto rounded-2xl"
          onLoad={() => { setLoaded(true); onInspected?.(true); }}
          onError={() => { setFailed(true); onInspected?.(false); }} />}
      </>}
  </figure>;
}
