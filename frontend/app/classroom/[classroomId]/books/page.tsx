"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { createBrowserClient } from "@supabase/ssr";
import BookCard from "@/components/BookCard";
import { StateBadge } from "@/components/BookCard";
import BookReviewDialog from "@/components/BookReviewDialog";
import { StaggerGrid, StaggerItem } from "@/components/StaggerGrid";
import { Job, ReviewDecision, jobState } from "@/lib/types/jobs";

type Tab = "pending" | "approved" | "rejected";

type Toast = {
  message: string;
  jobId: string;
  undoDecision: ReviewDecision;
};

const TOAST_MS = 5000;
const BUCKET = "storybook-images";

export default function BooksPage() {
  const { classroomId } = useParams<{ classroomId: string }>();
  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co",
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key"
  );

  const [jobs, setJobs] = useState<Job[] | null>(null);
  const [thumbnails, setThumbnails] = useState<Record<string, string>>({});
  const [activeTab, setActiveTab] = useState<Tab>("pending");
  const [toast, setToast] = useState<Toast | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [dialogJobId, setDialogJobId] = useState<string | null>(null);
  const [dialogPageUrls, setDialogPageUrls] = useState<string[]>([]);

  // ── Fetch ────────────────────────────────────────────────────────────────

  const fetchJobs = useCallback(async () => {
    const { data } = await supabase
      .from("jobs")
      .select(
        "id, status, failure_reason, approved_at, rejected_at, created_at, input_text, pages, profile_id, profiles(display_nickname, avatar_id)"
      )
      .eq("classroom_id", classroomId)
      .order("created_at", { ascending: false });
    setJobs((data as unknown as Job[]) ?? []);
  }, [classroomId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchJobs();
    const handler = () => {
      if (!document.hidden) fetchJobs();
    };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, [fetchJobs]);

  // ── Sign thumbnails ───────────────────────────────────────────────────────

  useEffect(() => {
    if (!jobs) return;
    const unsigned = jobs.filter((j) => j.pages?.[0] && !thumbnails[j.id]);
    if (!unsigned.length) return;

    Promise.all(
      unsigned.map(async (j) => {
        const path = j.pages![0].image_path;
        const { data } = await supabase.storage
          .from(BUCKET)
          .createSignedUrl(path, 3600);
        return { id: j.id, url: data?.signedUrl ?? null };
      })
    ).then((results) => {
      setThumbnails((prev) => {
        const next = { ...prev };
        for (const r of results) if (r.url) next[r.id] = r.url;
        return next;
      });
    });
  }, [jobs]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Open dialog & sign pages ──────────────────────────────────────────────

  async function openDialog(jobId: string) {
    setDialogJobId(jobId);
    setDialogPageUrls([]);
    const job = jobs?.find((j) => j.id === jobId);
    if (!job?.pages?.length) return;
    const signed = await Promise.all(
      job.pages.map(async (p) => {
        const { data } = await supabase.storage
          .from(BUCKET)
          .createSignedUrl(p.image_path, 3600);
        return data?.signedUrl ?? "";
      })
    );
    setDialogPageUrls(signed);
  }

  // ── Decision ─────────────────────────────────────────────────────────────

  async function callReview(jobId: string, decision: ReviewDecision) {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    const resp = await fetch(
      `${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/review`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ decision }),
      }
    );
    if (!resp.ok) throw new Error(await resp.text());
    return resp.json() as Promise<{ approved_at: string | null; rejected_at: string | null }>;
  }

  function applyDecisionLocally(jobId: string, decision: ReviewDecision) {
    const now = new Date().toISOString();
    setJobs((prev) =>
      prev?.map((j) => {
        if (j.id !== jobId) return j;
        if (decision === "approved") return { ...j, approved_at: now, rejected_at: null };
        if (decision === "rejected") return { ...j, approved_at: null, rejected_at: now };
        return { ...j, approved_at: null, rejected_at: null };
      }) ?? null
    );
  }

  function revertDecision(jobId: string, prev: Job) {
    setJobs((current) =>
      current?.map((j) => (j.id === jobId ? prev : j)) ?? null
    );
  }

  async function handleDecide(decision: ReviewDecision) {
    if (!dialogJobId || !jobs) return;

    const prevJob = jobs.find((j) => j.id === dialogJobId);
    if (!prevJob) return;
    const prevDecision = jobState(prevJob) as ReviewDecision;

    applyDecisionLocally(dialogJobId, decision);

    const pendingAfter = jobs.filter(
      (j) => j.id !== dialogJobId && j.status === "complete" && !j.approved_at && !j.rejected_at
    );
    if (decision !== "pending" && pendingAfter.length > 0) {
      const nextId = pendingAfter[0].id;
      setDialogJobId(nextId);
      openDialog(nextId);
    } else if (decision !== "pending") {
      setDialogJobId(null);
      setDialogPageUrls([]);
    }

    if (decision !== "pending") {
      showToast({
        message: decision === "approved" ? "Approved" : "Rejected",
        jobId: dialogJobId,
        undoDecision: prevDecision,
      });
    }

    try {
      await callReview(dialogJobId, decision);
    } catch {
      revertDecision(dialogJobId, prevJob);
      showToast({
        message: "Could not save — try again",
        jobId: dialogJobId,
        undoDecision: decision,
      });
    }
  }

  async function handleUndo() {
    if (!toast) return;
    const { jobId, undoDecision } = toast;
    clearToast();
    applyDecisionLocally(jobId, undoDecision);
    try {
      await callReview(jobId, undoDecision);
    } catch {
      fetchJobs();
    }
  }

  // ── Toast helpers ─────────────────────────────────────────────────────────

  function showToast(t: Toast) {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(t);
    toastTimer.current = setTimeout(() => setToast(null), TOAST_MS);
  }

  function clearToast() {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(null);
  }

  // ── Derived lists ─────────────────────────────────────────────────────────

  const pendingJobs =
    jobs?.filter(
      (j) => j.status === "complete" && !j.approved_at && !j.rejected_at
    ) ?? [];
  const approvedJobs = jobs?.filter((j) => j.approved_at !== null) ?? [];
  const rejectedJobs = jobs?.filter((j) => j.rejected_at !== null) ?? [];
  const failedJobs = jobs?.filter((j) => j.status === "failed") ?? [];

  const dialogJob = jobs?.find((j) => j.id === dialogJobId) ?? null;

  const tabs: { key: Tab; label: string; count: number }[] = [
    { key: "pending", label: "Needs review", count: pendingJobs.length },
    { key: "approved", label: "Approved", count: approvedJobs.length },
    { key: "rejected", label: "Rejected", count: rejectedJobs.length },
  ];

  const visibleJobs =
    activeTab === "pending"
      ? pendingJobs
      : activeTab === "approved"
      ? approvedJobs
      : rejectedJobs;

  // ── Skeleton ──────────────────────────────────────────────────────────────

  if (jobs === null) {
    return (
      <div className="p-6 sm:p-8 max-w-5xl mx-auto">
        <div className="h-8 w-40 bg-muted rounded-xl animate-pulse mb-6" />
        <div className="flex gap-1 mb-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-10 w-28 bg-muted rounded-xl animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-muted rounded-2xl aspect-[4/3] animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="p-6 sm:p-8 max-w-5xl mx-auto">
      {/* Page heading */}
      <div className="mb-6">
        <h1 className="font-display text-3xl font-extrabold text-foreground">
          {activeTab === "pending" && pendingJobs.length > 0
            ? `${pendingJobs.length} waiting`
            : "Books"}
        </h1>
      </div>

      {/* Tab bar */}
      <div
        role="tablist"
        aria-label="Book review tabs"
        className="flex gap-1 mb-6 border-b border-primary/10"
        onKeyDown={(e) => {
          const keys = ["ArrowLeft", "ArrowRight"];
          if (!keys.includes(e.key)) return;
          const idx = tabs.findIndex((t) => t.key === activeTab);
          const next =
            e.key === "ArrowRight"
              ? (idx + 1) % tabs.length
              : (idx - 1 + tabs.length) % tabs.length;
          setActiveTab(tabs[next].key);
        }}
      >
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={activeTab === t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-4 py-2 text-sm font-bold rounded-t-xl transition-colors relative ${
              activeTab === t.key
                ? "text-primary after:absolute after:bottom-0 after:left-0 after:right-0 after:h-0.5 after:bg-primary"
                : "text-foreground/50 hover:text-foreground/80"
            }`}
          >
            {t.label}
            {t.count > 0 && (
              <span className="ml-1.5 text-xs bg-muted px-1.5 py-0.5 rounded-full">
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Book list */}
      {visibleJobs.length === 0 ? (
        <EmptyState tab={activeTab} />
      ) : (
        <>
          {/* Mobile: cards */}
          <StaggerGrid className="sm:hidden grid grid-cols-1 gap-4">
            {visibleJobs.map((j) => (
              <StaggerItem key={j.id}>
                <BookCard
                  job={j}
                  thumbnailUrl={thumbnails[j.id] ?? null}
                  onOpen={() => openDialog(j.id)}
                />
              </StaggerItem>
            ))}
          </StaggerGrid>
          {/* Desktop: table */}
          <div className="hidden sm:block overflow-x-auto rounded-2xl border border-primary/15 shadow-[0_6px_18px_rgb(49_85_217/10%)]">
            <table className="w-full text-sm">
              <thead className="bg-surface border-b border-primary/10">
                <tr>
                  <th className="text-left px-6 py-3 font-bold text-foreground/60 text-xs uppercase tracking-wider">
                    Student
                  </th>
                  <th className="text-left px-6 py-3 font-bold text-foreground/60 text-xs uppercase tracking-wider">
                    Submitted
                  </th>
                  <th className="text-left px-6 py-3 font-bold text-foreground/60 text-xs uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-primary/10 bg-surface">
                {visibleJobs.map((j) => (
                  <BookTableRow
                    key={j.id}
                    job={j}
                    thumbnailUrl={thumbnails[j.id] ?? null}
                    onOpen={() => openDialog(j.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Didn't finish section */}
      {failedJobs.length > 0 && (
        <details className="mt-10">
          <summary className="cursor-pointer text-sm font-bold text-foreground/50 hover:text-foreground/80 transition-colors list-none flex items-center gap-2">
            <span>▸</span> Didn&apos;t finish ({failedJobs.length})
          </summary>
          <div className="mt-3 space-y-3">
            {failedJobs.map((j) => (
              <FailedBookRow key={j.id} job={j} />
            ))}
          </div>
        </details>
      )}

      {/* Review dialog */}
      <BookReviewDialog
        job={dialogJob}
        pageUrls={dialogPageUrls}
        onDecide={handleDecide}
        onClose={() => {
          setDialogJobId(null);
          setDialogPageUrls([]);
        }}
      />

      {/* Toast */}
      {toast && (
        <div
          role="status"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-foreground text-background px-5 py-3 rounded-xl text-sm font-bold shadow-lg z-50 flex items-center gap-3 max-w-sm"
        >
          <span>{toast.message}</span>
          <button
            onClick={handleUndo}
            className="text-secondary font-bold hover:underline min-h-[44px] px-1"
          >
            Undo
          </button>
        </div>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function EmptyState({ tab }: { tab: Tab }) {
  if (tab === "pending")
    return (
      <div className="bg-surface border border-primary/15 rounded-2xl p-10 text-center">
        <p className="font-display text-xl font-bold text-foreground mb-2">
          Nothing waiting.
        </p>
        <p className="text-sm text-foreground/50">You&apos;re all caught up.</p>
      </div>
    );
  if (tab === "approved")
    return (
      <div className="bg-surface border border-primary/15 rounded-2xl p-10 text-center">
        <p className="text-sm text-foreground/50">
          Nothing approved yet. Books you approve appear in the class gallery.
        </p>
      </div>
    );
  return (
    <div className="bg-surface border border-primary/15 rounded-2xl p-10 text-center">
      <p className="text-sm text-foreground/50">Nothing here.</p>
    </div>
  );
}

function BookTableRow({
  job,
  thumbnailUrl,
  onOpen,
}: {
  job: Job;
  thumbnailUrl: string | null;
  onOpen: () => void;
}) {
  const state = jobState(job);
  const name = job.profiles?.display_nickname ?? "—";
  const date = new Date(job.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  return (
    <tr
      className="hover:bg-background/40 transition-colors cursor-pointer"
      onClick={onOpen}
    >
      <td className="px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-muted overflow-hidden shrink-0">
            {thumbnailUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={thumbnailUrl} alt="" aria-hidden="true" className="w-full h-full object-cover" />
            )}
          </div>
          <span className="font-bold">{name}</span>
        </div>
      </td>
      <td className="px-6 py-3 text-foreground/60">{date}</td>
      <td className="px-6 py-3">
        <StateBadge state={state} />
      </td>
      <td className="px-6 py-3 text-right">
        <button
          className="text-primary text-sm font-bold hover:underline min-h-[44px] px-2"
          onClick={onOpen}
        >
          Review
        </button>
      </td>
    </tr>
  );
}

function FailedBookRow({ job }: { job: Job }) {
  const isSafety = job.failure_reason === "child_text";
  const name = job.profiles?.display_nickname ?? "Unknown";
  const date = new Date(job.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
  return (
    <div className="bg-surface border border-primary/10 rounded-2xl p-4">
      <div className="flex items-center justify-between gap-2 mb-2">
        <p className="font-bold text-sm text-foreground">{name}</p>
        <p className="text-xs text-foreground/50">{date}</p>
      </div>
      {isSafety ? (
        <div>
          <p className="text-sm text-foreground/70 mb-2">
            The safety check stopped this story.
          </p>
          <blockquote className="text-sm text-foreground/60 italic border-l-2 border-primary/20 pl-3">
            {job.input_text}
          </blockquote>
        </div>
      ) : (
        <p className="text-sm text-foreground/70">
          Something went wrong while this was being made. They can try again.
        </p>
      )}
    </div>
  );
}
