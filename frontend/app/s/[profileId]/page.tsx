"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";
import { classify, type JobRow, type JobBucket } from "@/lib/useJob";
import { motion } from "motion/react";

type JobCard = {
  id: string;
  bucket: JobBucket;
  title: string;
  coverUrl: string | null;
};

export default function BookshelfPage({
  params,
}: {
  params: Promise<{ profileId: string }>;
}) {
  const [profileId, setProfileId] = useState<string | null>(null);
  const [cards, setCards] = useState<JobCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    params.then(({ profileId: pid }) => setProfileId(pid));
  }, [params]);

  useEffect(() => {
    if (!profileId) return;
    let cancelled = false;

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
      const { data: jobs } = await supabase
        .from("jobs")
        .select("id, status, current_stage, failure_reason, input_text, pages, reveal")
        // ponytail: explicit filter required — RLS also grants classmates' approved jobs (spec §7.2)
        .eq("profile_id", profileId)
        .order("created_at", { ascending: false });

      if (cancelled || !jobs) {
        setLoading(false);
        return;
      }

      const imagePaths = (jobs as JobRow[])
        .map((j) => j.pages?.[0]?.image_path)
        .filter((p): p is string => Boolean(p));

      const signedMap: Record<string, string> = {};
      if (imagePaths.length > 0) {
        const { data: signed } = await supabase.storage
          .from("storybook-images")
          .createSignedUrls(imagePaths, 3600);
        signed?.forEach(({ path, signedUrl }) => {
          signedMap[path] = signedUrl;
        });
      }

      setCards(
        (jobs as JobRow[]).map((j) => ({
          id: j.id,
          bucket: classify(j),
          title: (j.input_text ?? "").split("\n")[0].slice(0, 60) || "Untitled",
          coverUrl: j.pages?.[0]?.image_path
            ? (signedMap[j.pages[0].image_path] ?? null)
            : null,
        }))
      );
      setLoading(false);
    })();

    return () => {
      cancelled = true;
      supabase.removeChannel(channel);
    };
  }, [profileId]);

  if (!profileId) return null;

  return (
    <main className="font-kid p-6 sm:p-10 max-w-7xl mx-auto min-h-[calc(100vh-80px)] flex flex-col">
      <div className="flex items-center justify-between mb-8 sm:mb-12">
        <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-primary">
          Your Bookshelf
        </h1>
        {cards.length > 0 && (
          <Link 
            href={`/s/${profileId}/write`} 
            className="hidden sm:inline-flex min-h-[48px] px-6 rounded-xl bg-secondary text-on-secondary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform hover:-translate-y-0.5 active:translate-y-1 active:shadow-none items-center"
          >
            + Write a new book
          </Link>
        )}
      </div>

      {!loading && cards.length === 0 && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex-1 flex flex-col items-center justify-center p-12 text-center bg-surface border-4 border-dashed border-primary/10 rounded-[32px] max-w-2xl mx-auto w-full my-auto"
        >
          <div className="w-24 h-24 bg-secondary/20 text-secondary rounded-full flex items-center justify-center mb-6">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
            </svg>
          </div>
          <h2 className="font-display text-3xl font-extrabold text-primary mb-3">Your shelf is empty!</h2>
          <p className="text-foreground/70 text-lg mb-8 max-w-[30ch]">
            Every great library starts with a single book. Let&apos;s make yours!
          </p>
          <Link 
            href={`/s/${profileId}/write`} 
            className="min-h-[56px] px-8 rounded-2xl bg-primary text-on-primary text-xl font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform hover:-translate-y-0.5 active:translate-y-1 active:shadow-none inline-flex items-center justify-center"
          >
            Write my first book
          </Link>
        </motion.div>
      )}

      {cards.length > 0 && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-6 sm:gap-8 lg:gap-10 pb-20">
            {cards.map((card, idx) => (
              <BookCard key={card.id} card={card} profileId={profileId} index={idx} />
            ))}
          </div>
          
          {/* Mobile floating action button */}
          <div className="sm:hidden fixed bottom-6 left-1/2 -translate-x-1/2 w-[calc(100%-48px)] z-20">
            <Link 
              href={`/s/${profileId}/write`} 
              className="flex w-full min-h-[56px] px-6 rounded-2xl bg-secondary text-on-secondary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform active:translate-y-1 active:shadow-none items-center justify-center text-lg"
            >
              + Write a new book
            </Link>
          </div>
        </>
      )}
    </main>
  );
}

function BookCard({
  card,
  profileId,
  index,
}: {
  card: JobCard;
  profileId: string;
  index: number;
}) {
  const href: Record<JobBucket, string> = {
    "terminal-success": `/s/${profileId}/book/${card.id}`,
    "in-flight": `/s/${profileId}/process/${card.id}`,
    paused: `/s/${profileId}/process/${card.id}`,
    "terminal-failure": `/s/${profileId}/write`,
    "not-found": `/s/${profileId}/write`,
  };

  const label: Record<JobBucket, string> = {
    "terminal-success": card.title,
    "in-flight": "Still making it…",
    paused: "Come meet your cast!",
    "terminal-failure": "This one didn't finish",
    "not-found": card.title,
  };

  // Organic rotation: cycles to make them look like they were dropped on a shelf
  const rotations = [-3, 2, -1, 4, -2];
  const defaultRotation = rotations[index % rotations.length];

  return (
    <motion.div
      initial={{ rotate: defaultRotation, y: 0 }}
      whileHover={{ y: -16, rotate: 0, scale: 1.05, zIndex: 10 }}
      whileFocus={{ y: -16, rotate: 0, scale: 1.05, zIndex: 10 }}
      transition={{ type: "spring", stiffness: 400, damping: 25 }}
      className="relative"
    >
      <Link
        href={href[card.bucket]}
        className="block rounded-[20px] sm:rounded-[24px] bg-surface border-2 border-primary/10 overflow-hidden shadow-[0_10px_28px_rgba(49,85,217,0.12)] hover:shadow-[0_22px_60px_rgba(49,85,217,0.2)] transition-shadow outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-4 focus-visible:ring-offset-background"
      >
        {/* Cover Image or Status Graphic */}
        {card.coverUrl && card.bucket === "terminal-success" ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={card.coverUrl}
            alt=""
            className="w-full aspect-[4/5] object-cover"
          />
        ) : (
          <div className="w-full aspect-[4/5] flex flex-col items-center justify-center bg-background border-b-2 border-primary/5">
            {card.bucket === "in-flight" && (
              <div className="w-16 h-16 rounded-3xl bg-primary/10 flex items-center justify-center animate-stepper-pulse mb-3">
                <span className="text-3xl" aria-hidden="true">✨</span>
              </div>
            )}
            {card.bucket === "paused" && (
              <div className="w-16 h-16 rounded-3xl bg-secondary/20 flex items-center justify-center animate-bounce mb-3">
                <span className="text-3xl" aria-hidden="true">👀</span>
              </div>
            )}
            {(card.bucket === "terminal-failure" || card.bucket === "not-found") && (
              <div className="w-16 h-16 rounded-3xl bg-destructive/10 flex items-center justify-center mb-3">
                <span className="text-3xl" aria-hidden="true">📝</span>
              </div>
            )}
            {card.bucket === "terminal-success" && !card.coverUrl && (
              <div className="w-16 h-16 rounded-3xl bg-primary/10 flex items-center justify-center mb-3">
                <span className="text-3xl font-display font-extrabold text-primary">?</span>
              </div>
            )}
          </div>
        )}
        
        {/* Spine/Title area */}
        <div className="p-4 sm:p-5 bg-surface relative z-10 border-t-2 border-primary/5">
          <p className="font-extrabold text-sm sm:text-base text-foreground line-clamp-2 leading-snug">
            {label[card.bucket]}
          </p>
        </div>
      </Link>
    </motion.div>
  );
}
