import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import Link from "next/link";
import { Avatar } from "@/components/Avatar";
import { StaggerGrid, StaggerItem } from "@/components/StaggerGrid";
import { displayTitle } from "@/lib/displayTitle";
import GuardedCover from "@/components/GuardedCover";

type Job = {
  id: string;
  moderation_mode?: string;
  approved_at: string;
  title: string | null;
  pages: { scene_id: string; caption: string; image_path: string }[] | null;
  profile_id: string;
  profiles: { display_nickname: string; avatar_id: string | null } | null;
};

export default async function GalleryPage({
  params,
}: {
  params: Promise<{ profileId: string }>;
}) {
  const { profileId } = await params;
  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co",
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key",
    { cookies: { get: (name) => cookieStore.get(name)?.value } },
  );

  const { data } = await supabase
    .from("jobs")
    // spec §5: no input_text. This page spans every classmate's approved book, so the excerpt
    // fallback is not authorized for this viewer — a legacy untitled book reads "Untitled".
    .select("id, status, moderation_mode, approved_at, title, pages, profile_id, profiles!inner(display_nickname, avatar_id)")
    .eq("status", "complete")
    .not("approved_at", "is", null)
    .is("profiles.removed_at", null)
    .order("approved_at", { ascending: false })
    .limit(200);

  const jobs = (data as unknown as Job[]) ?? [];

  const paths = jobs.filter(j => j.moderation_mode !== "teacher_review_v1").flatMap((j) =>
    j.pages?.[0]?.image_path ? [j.pages[0].image_path] : [],
  );
  const signedMap: Record<string, string> = {};
  if (paths.length > 0) {
    const { data: signed } = await supabase.storage
      .from("storybook-images")
      .createSignedUrls(paths, 3600);
    for (const s of signed ?? []) {
      if (s.signedUrl && s.path) signedMap[s.path] = s.signedUrl;
    }
  }

  if (jobs.length === 0) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center px-6">
        <p className="font-kid text-center text-xl text-foreground/70">
          Your class&apos;s books will show up here.
        </p>
      </div>
    );
  }

  return (
    <StaggerGrid className="grid grid-cols-2 gap-4 p-6 sm:grid-cols-3 md:grid-cols-4">
      {jobs.map((job) => {
        const coverPath = job.pages?.[0]?.image_path;
        const coverUrl = coverPath ? signedMap[coverPath] : undefined;
        const nickname = job.profiles?.display_nickname ?? "Unknown";
        const href = `/s/${profileId}/book/${job.id}`;
        const details = (
          <>
            <p className="font-kid truncate text-sm font-bold text-foreground">
              {displayTitle(job.title, null)}
            </p>
            <div className="flex items-center gap-3">
              <Avatar avatarId={job.profiles?.avatar_id ?? null} displayNickname={nickname} size={32} />
              <p className="font-kid truncate text-base font-bold text-foreground">
                by {nickname}
              </p>
            </div>
          </>
        );
        // The cover's Try again cannot sit inside a link, so the link's ::after covers the card
        // (tapping the cover still opens the book) and Try again sits above it. The card, not the
        // clipped link, draws the globals.css focus ring (yellow outline, navy band).
        return (
          <StaggerItem key={job.id}>
            <div className="relative h-full overflow-hidden rounded-2xl border border-primary/15 bg-surface shadow-[0_6px_18px_rgba(49,85,217,0.1)] has-[>a:focus-visible]:outline-3 has-[>a:focus-visible]:outline-offset-3 has-[>a:focus-visible]:outline-secondary has-[>a:focus-visible]:shadow-[0_0_0_3px_var(--foreground)]">
              <GuardedCover job={job} alt={`Cover of book by ${nickname}`} src={coverUrl}
                className="aspect-[4/3] w-full border-b border-primary/15" />
              <Link href={href} className="p-3 flex flex-col gap-1 min-h-11 after:absolute after:inset-0 focus-visible:outline-none focus-visible:shadow-none!">
                {details}
              </Link>
            </div>
          </StaggerItem>
        );
      })}
    </StaggerGrid>
  );
}
