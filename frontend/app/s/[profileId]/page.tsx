"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";
import { classify, type JobRow, type JobBucket } from "@/lib/useJob";
import { displayTitle } from "@/lib/displayTitle";
import { signPaths } from "@/lib/signedUrls";
import { motion } from "framer-motion";
import { MagicWand, Users, FileDashed, Books, PencilSimple, WarningCircle, ArrowsClockwise } from "@phosphor-icons/react";
import Loading from "./loading";

type JobCard = {
  id: string;
  bucket: JobBucket;
  title: string;
};

// Per-card cover state (spec §5.9): no key = still loading, null = no cover, string = ready.
type Covers = Record<string, string | null>;

const coverPath = (job: JobRow) => job.pages?.[0]?.image_path || undefined;

// Each cover goes to `onCover` as it arrives, so cards fill in one by one (spec AC-03).
// One round for every cover, then one retry for the failed ones only (spec AC-07, §5.4);
// a cover still missing after that ends as null. A rejected call fails every path it had not delivered.
async function signCovers(rows: JobRow[], signal: AbortSignal, onCover: (jobId: string, url: string | null) => void) {
  const sign = async (pairs: Array<[JobRow, string]>) => {
    const arrived = new Set<string>();
    await signPaths(pairs.map(([, path]) => path), pairs.map(([job]) => job), signal, (path, url) => {
      arrived.add(path);
      if (signal.aborted) return;
      for (const [job, p] of pairs) if (p === path) onCover(job.id, url);
    }).catch(() => {});
    return pairs.filter(([, path]) => !arrived.has(path));
  };
  const failed = await sign(rows.flatMap((j): Array<[JobRow, string]> => {
    const path = coverPath(j);
    return path ? [[j, path]] : [];
  }));
  if (failed.length === 0 || signal.aborted) return;
  const lost = await sign(failed);
  if (!signal.aborted) for (const [job] of lost) onCover(job.id, null);
}

export default function BookshelfPage({
  params,
}: {
  params: Promise<{ profileId: string }>;
}) {
  const [profileId, setProfileId] = useState<string | null>(null);
  const [cards, setCards] = useState<JobCard[]>([]);
  const [covers, setCovers] = useState<Covers>({});
  const [loading, setLoading] = useState(true);
  // The list read failed (spec AC-06, OD-01). Bumping `attempt` re-runs the load effect.
  const [listFailed, setListFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [unreadNotes, setUnreadNotes] = useState<string[]>([]);

  useEffect(() => {
    params.then(({ profileId: pid }) => setProfileId(pid));
  }, [params]);

  useEffect(() => {
    if (!profileId) return;
    let active: AbortController | undefined;
    async function loadNotes() {
      active?.abort();
      const controller = new AbortController();
      active = controller;
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (controller.signal.aborted) return;
        if (!session) { setUnreadNotes([]); return; }
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/me/notes`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
          cache: "no-store", signal: controller.signal,
        });
        if (!response.ok) throw new Error("notes unavailable");
        const notes: { job_id: string; seen: boolean }[] = await response.json();
        if (!controller.signal.aborted) setUnreadNotes(notes.filter(note => !note.seen).map(note => note.job_id));
      } catch {
        if (!controller.signal.aborted) setUnreadNotes([]);
      }
    }
    void loadNotes();
    window.addEventListener("focus", loadNotes);
    return () => { active?.abort(); window.removeEventListener("focus", loadNotes); };
  }, [profileId]);

  useEffect(() => {
    if (!profileId) return;
    let cancelled = false;
    const imageController = new AbortController();
    // Realtime cover loads, one per card: a newer update aborts the older load (spec §4, SH-02).
    // A card here belongs to Realtime, so the first load never sets its cover.
    const liveCovers = new Map<string, AbortController>();
    // Last known bucket and cover path per card, so a repeat UPDATE keeps the shown cover (spec AC-05).
    const known = new Map<string, { bucket: JobBucket; path?: string }>();

    // Subscribe first, then SELECT — same ordering as useJob (avoids missed updates)
    const channel = supabase
      .channel(`shelf-${profileId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "jobs",
          filter: `profile_id=eq.${profileId}`,
        },
        (payload: { new: JobRow }) => {
          const row = payload.new;
          const bucket = classify(row);
          const path = coverPath(row);
          const before = known.get(row.id);
          known.set(row.id, { bucket, path });
          if (bucket === "terminal-success" && (before?.bucket !== "terminal-success" || before.path !== path)) {
            liveCovers.get(row.id)?.abort();
            const controller = new AbortController();
            liveCovers.set(row.id, controller);
            setCovers((prev) => {
              const next = { ...prev };
              if (path) delete next[row.id];
              else next[row.id] = null;
              return next;
            });
            if (path) void signCovers([row], controller.signal, (jobId, url) => setCovers((prev) => ({ ...prev, [jobId]: url })));
          }
          setCards((prev) =>
            prev.map((c) =>
              c.id === payload.new.id
                ? { ...c, bucket: classify(payload.new) }
                : c
            )
          );
        }
      )
      .subscribe();

    (async () => {
      const { data: jobs, error } = await supabase
        .from("jobs")
        .select("id, status, moderation_mode, input_text, title, pages")
        // ponytail: explicit filter required — RLS also grants classmates' approved jobs (spec §7.2)
        .eq("profile_id", profileId)
        .order("created_at", { ascending: false });

      if (cancelled) return;
      if (error || !jobs) {
        setListFailed(true);
        setLoading(false);
        return;
      }

      const rows = jobs as JobRow[];
      for (const j of rows) if (!known.has(j.id)) known.set(j.id, { bucket: classify(j), path: coverPath(j) });
      // Cards render now; covers fill in as signing finishes (spec AC-02, AC-03).
      setCards(
        rows.map((j) => ({
          id: j.id,
          bucket: classify(j),
          title: displayTitle(j.title, j.input_text),
        }))
      );
      const setFirstCover = (jobId: string, url: string | null) => {
        if (!cancelled && !liveCovers.has(jobId)) setCovers((prev) => ({ ...prev, [jobId]: url }));
      };
      for (const j of rows) if (!coverPath(j)) setFirstCover(j.id, null);
      setLoading(false);

      if (rows.some(coverPath)) await signCovers(rows, imageController.signal, setFirstCover);
    })();

    return () => {
      cancelled = true;
      imageController.abort();
      for (const controller of liveCovers.values()) controller.abort();
      supabase.removeChannel(channel);
    };
  }, [profileId, attempt]);

  if (!profileId) return null;

  // An issued URL that fails in <img> would fail again from cache, so no retry (spec AC-10, §5.4).
  const coverFailed = (jobId: string, url: string) =>
    setCovers((prev) => (prev[jobId] === url ? { ...prev, [jobId]: null } : prev));

  // Same skeleton as the route loading file (spec §5.7), so the heading never sits over an empty grid.
  if (loading) {
    return (
      <>
        <p role="status" aria-live="polite" className="sr-only">Loading your bookshelf</p>
        <div aria-hidden="true">
          <Loading />
        </div>
      </>
    );
  }

  const retryList = () => {
    setListFailed(false);
    setLoading(true);
    setAttempt((n) => n + 1);
  };

  // Failed jobs are permanent (terminal jobs are immutable — kid-flow S3), so they are
  // tucked away instead of deleted; keeps the shelf tidy with no delete surface.
  const shelfCards = cards.filter((c) => c.bucket !== "terminal-failure");
  const failedCards = cards.filter((c) => c.bucket === "terminal-failure");

  return (
    <main className="font-kid p-6 sm:p-10 max-w-7xl mx-auto min-h-[calc(100vh-80px)] flex flex-col">
      <div className="flex items-center justify-between mb-8 sm:mb-12">
        <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-primary">
          Your Bookshelf
        </h1>
        {cards.length > 0 && (
          <Link 
            href={`/s/${profileId}/write`} 
            className="group hidden sm:inline-flex min-h-[48px] px-6 rounded-xl bg-secondary text-on-secondary font-extrabold shadow-[0_6px_18px_rgba(49,85,217,0.1)] transition-all hover:-translate-y-[2px] hover:shadow-[0_10px_28px_rgba(49,85,217,0.12)] active:translate-y-0 active:scale-[0.98] active:shadow-[0_6px_18px_rgba(49,85,217,0.1)] items-center gap-2"
          >
            <PencilSimple weight="bold" className="w-5 h-5 group-hover:rotate-12 transition-transform" />
            Write a new book
          </Link>
        )}
      </div>

      {listFailed && (
        <div
          role="alert"
          className="flex-1 flex flex-col items-center justify-center p-12 text-center bg-surface border border-primary/15 rounded-[32px] max-w-2xl mx-auto w-full my-auto"
        >
          <div className="size-20 bg-warning/15 text-warning rounded-2xl flex items-center justify-center mb-6">
            <WarningCircle weight="duotone" className="size-10" aria-hidden="true" />
          </div>
          <h2 className="font-display text-3xl font-extrabold text-primary mb-3">We couldn&apos;t open your bookshelf</h2>
          <p className="text-foreground/70 text-lg mb-8 max-w-[30ch]">
            Don&apos;t worry, your stories are safe! Let&apos;s try that again.
          </p>
          <button
            type="button"
            onClick={retryList}
            className="min-h-[56px] px-8 rounded-2xl bg-primary text-on-primary text-xl font-extrabold inline-flex items-center justify-center gap-2 hover:bg-primary-deep active:scale-[0.98] transition-all cursor-pointer focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <ArrowsClockwise weight="bold" className="size-5" aria-hidden="true" />
            Try again
          </button>
        </div>
      )}

      {!listFailed && cards.length === 0 && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex-1 flex flex-col items-center justify-center p-12 text-center bg-surface border-4 border-dashed border-primary/10 rounded-[32px] max-w-2xl mx-auto w-full my-auto"
        >
          <div className="size-20 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mb-6 shadow-sm">
            <Books weight="duotone" className="size-10" aria-hidden="true" />
          </div>
          <h2 className="font-display text-3xl font-extrabold text-primary mb-3">Your shelf is empty!</h2>
          <p className="text-foreground/70 text-lg mb-8 max-w-[30ch]">
            Every great library starts with a single book. Let&apos;s make yours!
          </p>
          <Link 
            href={`/s/${profileId}/write`} 
            className="min-h-[56px] px-8 rounded-2xl bg-primary text-on-primary text-xl font-extrabold shadow-[0_10px_28px_rgba(49,85,217,0.12)] transition-all hover:-translate-y-[2px] hover:shadow-[0_22px_60px_rgba(49,85,217,0.16)] active:translate-y-0 active:scale-[0.98] active:shadow-[0_10px_28px_rgba(49,85,217,0.12)] inline-flex items-center justify-center"
          >
            Write my first book
          </Link>
        </motion.div>
      )}

      {cards.length > 0 && (
        <>
          <motion.div 
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6 sm:gap-8 lg:gap-10 pb-20"
            initial="hidden"
            animate="show"
            variants={{
              hidden: { opacity: 0 },
              show: { opacity: 1, transition: { staggerChildren: 0.1 } }
            }}
          >
            {shelfCards.map((card, idx) => (
              <BookCard key={card.id} card={card} cover={covers[card.id]} onCoverError={coverFailed} profileId={profileId} index={idx} hasNote={unreadNotes.includes(card.id)} />
            ))}
          </motion.div>

          {/* Didn't finish — collapsed, same pattern as the teacher books page */}
          {failedCards.length > 0 && (
            <details className="mb-24 sm:mb-10">
              <summary className="cursor-pointer list-none flex items-center gap-2 font-extrabold text-foreground/50 hover:text-foreground/80 transition-colors min-h-[44px]">
                <span aria-hidden="true">▸</span> Didn&apos;t finish ({failedCards.length})
              </summary>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6 sm:gap-8 lg:gap-10 mt-6">
                {failedCards.map((card, idx) => (
                  <BookCard key={card.id} card={card} cover={covers[card.id]} onCoverError={coverFailed} profileId={profileId} index={idx} />
                ))}
              </div>
            </details>
          )}

          {/* Mobile floating action button */}
          <div className="sm:hidden fixed bottom-24 left-1/2 -translate-x-1/2 w-[calc(100%-48px)] z-20">
            <Link 
              href={`/s/${profileId}/write`} 
              className="group flex w-full min-h-[56px] px-6 rounded-2xl bg-secondary text-on-secondary font-extrabold shadow-[0_10px_28px_rgba(49,85,217,0.12)] transition-all hover:-translate-y-[2px] hover:shadow-[0_22px_60px_rgba(49,85,217,0.16)] active:translate-y-0 active:scale-[0.98] active:shadow-[0_10px_28px_rgba(49,85,217,0.12)] items-center justify-center text-lg gap-2"
            >
              <PencilSimple weight="bold" className="w-5 h-5 group-hover:rotate-12 transition-transform" />
              Write a new book
            </Link>
          </div>
        </>
      )}
    </main>
  );
}

function BookCard({
  card,
  cover,
  onCoverError,
  profileId,
  index,
  hasNote = false,
}: {
  card: JobCard;
  cover: string | null | undefined;
  onCoverError: (jobId: string, url: string) => void;
  profileId: string;
  index: number;
  hasNote?: boolean;
}) {
  const href: Record<JobBucket, string> = {
    "terminal-success": `/s/${profileId}/book/${card.id}`,
    "in-flight": `/s/${profileId}/process/${card.id}`,
    paused: `/s/${profileId}/process/${card.id}`,
    "teacher-held": `/s/${profileId}/process/${card.id}`,
    stopped: `/s/${profileId}/process/${card.id}`,
    // Amended from /write (spec §7.2): /process renders FailureScreen, which reposts
    // the child's own input_text on one tap instead of stranding them on a blank page.
    "terminal-failure": `/s/${profileId}/process/${card.id}`,
    "not-found": `/s/${profileId}/write`,
  };

  // Organic rotation: cycles to make them look like they were dropped on a shelf
  const rotations = [-3, 2, -1, 4, -2];
  const defaultRotation = rotations[index % rotations.length];

  // Tracks which URL finished loading, so a new cover from Realtime pulses and fades in again.
  const [loadedCover, setLoadedCover] = useState<string | null>(null);
  const coverLoaded = Boolean(cover) && loadedCover === cover;
  // The entrance delay is the default transition, which hover and focus also use, so it ends once the card is in.
  const [entered, setEntered] = useState(false);

  const coverBg = card.bucket === "paused" || card.bucket === "teacher-held" ? "bg-secondary/10"
    : (card.bucket === "terminal-failure" || card.bucket === "not-found") ? "bg-destructive/5"
    : card.bucket === "in-flight" ? "bg-primary/5"
    : "bg-background";

  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 50, rotate: 0 },
        show: { opacity: 1, y: 0, rotate: defaultRotation }
      }}
      initial="hidden"
      animate="show"
      whileHover={{ y: -2, rotate: 0, zIndex: 10, transition: { type: "spring", bounce: 0, duration: 0.15 } }}
      whileFocus={{ y: -2, rotate: 0, zIndex: 10, transition: { type: "spring", bounce: 0, duration: 0.15 } }}
      transition={{ type: "spring", bounce: 0, duration: 0.25, delay: entered ? 0 : Math.min(index, 8) * 0.05 }}
      onAnimationComplete={() => setEntered(true)}
      className="relative"
    >
      <Link
        href={href[card.bucket]}
        className="block rounded-[20px] sm:rounded-[24px] bg-surface border-2 border-primary/10 overflow-hidden shadow-[0_10px_28px_rgba(49,85,217,0.12)] hover:shadow-[0_22px_60px_rgba(49,85,217,0.2)] transition-shadow outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-4 focus-visible:ring-offset-background"
      >
        {/* Cover Image or Status Graphic */}
        <div className={`relative w-full aspect-[4/5] ${coverBg}`}>
          {card.bucket === "terminal-success" && cover !== null ? (
            <>
              {!coverLoaded && <div className="absolute inset-0 animate-pulse bg-muted/50" />}
              {cover && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={cover}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  onLoad={() => setLoadedCover(cover)}
                  onError={() => onCoverError(card.id, cover)}
                  className={`relative w-full h-full object-cover transition-opacity duration-[var(--duration-slow)] ${coverLoaded ? "opacity-100" : "opacity-0"}`}
                />
              )}
            </>
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center border-b-2 border-primary/5">
              {card.bucket === "in-flight" && (
                <div className="w-16 h-16 rounded-3xl bg-primary/10 flex items-center justify-center animate-stepper-pulse mb-3">
                  <MagicWand weight="fill" className="w-8 h-8 text-primary" aria-hidden="true" />
                </div>
              )}
              {(card.bucket === "paused" || card.bucket === "teacher-held") && (
                <div className="w-16 h-16 rounded-3xl bg-secondary/20 flex items-center justify-center mb-3">
                  <Users weight="fill" className="w-8 h-8 text-secondary" aria-hidden="true" />
                </div>
              )}
              {(card.bucket === "terminal-failure" || card.bucket === "not-found") && (
                <div className="w-16 h-16 rounded-3xl bg-destructive/10 flex items-center justify-center mb-3">
                  <FileDashed weight="fill" className="w-8 h-8 text-destructive" aria-hidden="true" />
                </div>
              )}
              {card.bucket === "terminal-success" && (
                <div className="w-16 h-16 rounded-3xl bg-primary/10 flex items-center justify-center mb-3">
                  <Books weight="duotone" className="w-8 h-8 text-primary" aria-hidden="true" />
                </div>
              )}
            </div>
          )}

          {/* Status Badge Overlays */}
          {card.bucket === "stopped" && <div className="absolute inset-0 flex items-end justify-center pb-4">
            <span className="px-3 py-1.5 rounded-full bg-muted text-foreground text-xs font-extrabold">Writing saved</span>
          </div>}
          {card.bucket === "in-flight" && (
            <div className="absolute inset-0 flex items-end justify-center pb-4">
              <span className="px-3 py-1.5 rounded-full bg-primary text-on-primary text-xs font-extrabold shadow-sm">
                Writing...
              </span>
            </div>
          )}
          {(card.bucket === "paused" || card.bucket === "teacher-held") && (
            <div className="absolute inset-0 flex items-end justify-center pb-4">
              <span className="px-3 py-1.5 rounded-full bg-secondary text-on-secondary text-xs font-extrabold shadow-sm">
                {card.bucket === "teacher-held" ? "Waiting for your teacher" : "Needs characters"}
              </span>
            </div>
          )}
          {card.bucket === "terminal-failure" && (
            <div className="absolute inset-0 flex items-end justify-center pb-4">
              <span className="px-3 py-1.5 rounded-full bg-destructive text-on-destructive text-xs font-extrabold shadow-sm">
                Didn&apos;t finish
              </span>
            </div>
          )}
        </div>
        
        {/* Spine/Title area */}
        <div className="p-4 sm:p-5 bg-surface relative z-10 border-t-2 border-primary/5">
          <p className="font-extrabold text-sm sm:text-base text-foreground line-clamp-2 leading-snug">
            {card.title}
          </p>
          {hasNote && card.bucket === "terminal-success" && (
            <p className="mt-2 rounded-xl bg-secondary/20 px-2 py-1 text-xs font-extrabold text-foreground">
              A note from your teacher
            </p>
          )}
        </div>
      </Link>
    </motion.div>
  );
}
