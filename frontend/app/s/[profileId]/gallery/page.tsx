import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import Link from "next/link";
import { Avatar } from "@/components/Avatar";
import { StaggerGrid, StaggerItem } from "@/components/StaggerGrid";

type Job = {
  id: string;
  approved_at: string;
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
    .select("id, approved_at, pages, profile_id, profiles!inner(display_nickname, avatar_id)")
    .not("approved_at", "is", null)
    .is("profiles.removed_at", null)
    .order("approved_at", { ascending: false })
    .limit(200);

  const jobs = (data as unknown as Job[]) ?? [];

  const paths = jobs.flatMap((j) =>
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
        return (
          <StaggerItem key={job.id}>
            <Link
              href={`/s/${profileId}/book/${job.id}`}
              className="block overflow-hidden rounded-2xl border border-primary/15 bg-surface shadow-[0_6px_18px_rgba(49,85,217,0.1)] outline-none h-full"
            >
              {coverUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={coverUrl}
                  alt={`Cover of book by ${nickname}`}
                  loading="lazy"
                  className="aspect-[3/4] w-full border-b border-primary/15 bg-muted object-cover"
                />
              ) : (
                <div className="aspect-[3/4] w-full border-b border-primary/15 bg-muted" />
              )}
              <div className="p-3 flex items-center gap-3">
                <Avatar avatarId={job.profiles?.avatar_id ?? null} displayNickname={nickname} size={32} />
                <p className="font-kid truncate text-base font-bold text-foreground">
                  by {nickname}
                </p>
              </div>
            </Link>
          </StaggerItem>
        );
      })}
    </StaggerGrid>
  );
}
