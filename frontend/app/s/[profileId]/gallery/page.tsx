import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import Link from "next/link";

type Job = {
  id: string;
  approved_at: string;
  pages: { scene_id: string; caption: string; image_path: string }[] | null;
  profile_id: string;
  profiles: { display_nickname: string } | null;
};

export default async function GalleryPage({
  params,
}: {
  params: Promise<{ profileId: string }>;
}) {
  const { profileId } = await params;
  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { get: (name) => cookieStore.get(name)?.value } },
  );

  const { data } = await supabase
    .from("jobs")
    .select("id, approved_at, pages, profile_id, profiles!inner(display_nickname)")
    .not("approved_at", "is", null)
    .is("profiles.removed_at", null)
    .order("approved_at", { ascending: false })
    .limit(200);

  const jobs: Job[] = data ?? [];

  const paths = jobs.flatMap((j) =>
    j.pages?.[0]?.image_path ? [j.pages[0].image_path] : [],
  );
  const signedMap: Record<string, string> = {};
  if (paths.length > 0) {
    const { data: signed } = await supabase.storage
      .from("storybook-images")
      .createSignedUrls(paths, 3600);
    for (const s of signed ?? []) {
      if (s.signedUrl) signedMap[s.path] = s.signedUrl;
    }
  }

  if (jobs.length === 0) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center px-6">
        <p className="text-center text-muted-foreground">
          Your class&apos;s books will show up here.
        </p>
      </div>
    );
  }

  return (
    <ul className="grid grid-cols-2 gap-4 p-6 sm:grid-cols-3 md:grid-cols-4">
      {jobs.map((job) => {
        const coverPath = job.pages?.[0]?.image_path;
        const coverUrl = coverPath ? signedMap[coverPath] : undefined;
        const nickname = job.profiles?.display_nickname ?? "Unknown";
        return (
          <li key={job.id}>
            <Link
              href={`/s/${profileId}/book/${job.id}`}
              className="block overflow-hidden rounded-xl"
            >
              {coverUrl ? (
                <img
                  src={coverUrl}
                  alt={`Cover of book by ${nickname}`}
                  className="aspect-[3/4] w-full object-cover"
                />
              ) : (
                <div className="aspect-[3/4] w-full rounded-xl bg-muted/20" />
              )}
              <p className="mt-2 text-sm font-semibold">by {nickname}</p>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
