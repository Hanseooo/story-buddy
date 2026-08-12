"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";
import { classify, type JobRow, type JobBucket } from "@/lib/useJob";
import { motion } from "framer-motion";
import { MagicWand, Users, FileDashed, Books, PencilSimple } from "@phosphor-icons/react";

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
          if (path && signedUrl) signedMap[path] = signedUrl;
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

      {!loading && cards.length === 0 && (
        <motion.div 
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex-1 flex flex-col items-center justify-center p-12 text-center bg-surface border-4 border-dashed border-primary/10 rounded-[32px] max-w-2xl mx-auto w-full my-auto"
        >
          <div className="w-24 h-24 bg-secondary/20 text-secondary rounded-full flex items-center justify-center mb-6">
            <Books weight="fill" className="w-12 h-12" aria-hidden="true" />
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
              <BookCard key={card.id} card={card} profileId={profileId} index={idx} />
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
                  <BookCard key={card.id} card={card} profileId={profileId} index={idx} />
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
    // Amended from /write (spec §7.2): /process renders FailureScreen, which reposts
    // the child's own input_text on one tap instead of stranding them on a blank page.
    "terminal-failure": `/s/${profileId}/process/${card.id}`,
    "not-found": `/s/${profileId}/write`,
  };

  // Organic rotation: cycles to make them look like they were dropped on a shelf
  const rotations = [-3, 2, -1, 4, -2];
  const defaultRotation = rotations[index % rotations.length];

  const coverBg = card.coverUrl && card.bucket === "terminal-success" 
    ? "bg-background" 
    : card.bucket === "paused" ? "bg-secondary/10"
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
      whileHover={{ y: -16, rotate: 0, scale: 1.05, zIndex: 10 }}
      whileFocus={{ y: -16, rotate: 0, scale: 1.05, zIndex: 10 }}
      transition={{ 
        type: "spring", 
        stiffness: 400, 
        damping: 25, 
        delay: index * 0.1 
      }}
      className="relative"
    >
      <Link
        href={href[card.bucket]}
        className="block rounded-[20px] sm:rounded-[24px] bg-surface border-2 border-primary/10 overflow-hidden shadow-[0_10px_28px_rgba(49,85,217,0.12)] hover:shadow-[0_22px_60px_rgba(49,85,217,0.2)] transition-shadow outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-4 focus-visible:ring-offset-background"
      >
        {/* Cover Image or Status Graphic */}
        <div className={`relative w-full aspect-[4/5] ${coverBg}`}>
          {card.coverUrl && card.bucket === "terminal-success" ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={card.coverUrl}
              alt=""
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center border-b-2 border-primary/5">
              {card.bucket === "in-flight" && (
                <div className="w-16 h-16 rounded-3xl bg-primary/10 flex items-center justify-center animate-stepper-pulse mb-3">
                  <MagicWand weight="fill" className="w-8 h-8 text-primary" aria-hidden="true" />
                </div>
              )}
              {card.bucket === "paused" && (
                <div className="w-16 h-16 rounded-3xl bg-secondary/20 flex items-center justify-center animate-bounce mb-3">
                  <Users weight="fill" className="w-8 h-8 text-secondary" aria-hidden="true" />
                </div>
              )}
              {(card.bucket === "terminal-failure" || card.bucket === "not-found") && (
                <div className="w-16 h-16 rounded-3xl bg-destructive/10 flex items-center justify-center mb-3">
                  <FileDashed weight="fill" className="w-8 h-8 text-destructive" aria-hidden="true" />
                </div>
              )}
              {card.bucket === "terminal-success" && !card.coverUrl && (
                <div className="w-16 h-16 rounded-3xl bg-primary/10 flex items-center justify-center mb-3">
                  <span className="text-3xl font-display font-extrabold text-primary">?</span>
                </div>
              )}
            </div>
          )}

          {/* Status Badge Overlays */}
          {card.bucket === "in-flight" && (
            <div className="absolute inset-0 flex items-end justify-center pb-4">
              <span className="px-3 py-1.5 rounded-full bg-primary/90 text-on-primary text-xs font-extrabold backdrop-blur-sm shadow-sm">
                Writing...
              </span>
            </div>
          )}
          {card.bucket === "paused" && (
            <div className="absolute inset-0 flex items-end justify-center pb-4">
              <span className="px-3 py-1.5 rounded-full bg-secondary text-on-secondary text-xs font-extrabold shadow-sm">
                Needs characters
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
            {card.title || "Untitled"}
          </p>
        </div>
      </Link>
    </motion.div>
  );
}
