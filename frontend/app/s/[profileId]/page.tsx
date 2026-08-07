"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabase } from "@/lib/supabaseClient";
import { classify, type JobRow, type JobBucket } from "@/lib/useJob";

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

      if (cancelled || !jobs) return;

      const imagePaths = (jobs as JobRow[])
        .map((j) => j.pages?.[0]?.image_path)
        .filter((p): p is string => Boolean(p));

      const signedMap: Record<string, string> = {};
      if (imagePaths.length > 0) {
        const { data: signed } = await supabase.storage
          .from("pages")
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
    })();

    return () => {
      cancelled = true;
      supabase.removeChannel(channel);
    };
  }, [profileId]);

  if (!profileId) return null;

  return (
    <main className="font-kid p-6">
      <h1 className="font-display text-2xl font-extrabold text-primary mb-6">
        Your Books
      </h1>
      {cards.length === 0 && (
        <p className="text-foreground/70">
          No books yet.{" "}
          <Link href={`/s/${profileId}/write`} className="underline text-primary">
            Write one!
          </Link>
        </p>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {cards.map((card) => (
          <BookCard key={card.id} card={card} profileId={profileId} />
        ))}
      </div>
    </main>
  );
}

function BookCard({
  card,
  profileId,
}: {
  card: JobCard;
  profileId: string;
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

  return (
    <Link
      href={href[card.bucket]}
      className="block rounded-2xl bg-surface border border-primary/15 overflow-hidden hover:shadow-md transition-shadow"
    >
      {card.coverUrl && card.bucket === "terminal-success" && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={card.coverUrl}
          alt=""
          className="w-full aspect-square object-cover"
        />
      )}
      <div className="p-3">
        <p className="font-bold text-sm text-foreground truncate">
          {label[card.bucket]}
        </p>
      </div>
    </Link>
  );
}
