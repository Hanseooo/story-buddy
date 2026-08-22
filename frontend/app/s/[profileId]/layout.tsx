import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";
import Link from "next/link";
import { StudentTabBar } from "@/components/StudentTabBar";
import { StudentHeader } from "@/components/StudentHeader";

export default async function StudentLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ profileId: string }>;
}) {
  const { profileId } = await params;
  const cookieStore = await cookies();
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co",
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key",
    {
      cookies: {
        get: (name) => cookieStore.get(name)?.value,
      },
    }
  );

  const { data } = await supabase
    .from("profiles")
    .select("display_nickname, role, classroom_id, avatar_id, is_adjudicator")
    .eq("id", profileId)
    .single();

  if (!data) {
    return (
      <div className="font-kid min-h-screen bg-background text-foreground flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-surface border border-primary/20 rounded-2xl p-6 sm:p-8 text-center shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
          <p className="text-lg font-bold text-foreground/80 mb-6">
            Your class isn&apos;t set up anymore. Ask your teacher.
          </p>
          <form action="/auth/signout" method="post">
            <button
              type="submit"
              className="min-h-11 px-6 py-2.5 rounded-xl bg-primary font-extrabold text-on-primary shadow-[0_6px_18px_rgba(49,85,217,0.1)] transition-all hover:-translate-y-[2px] hover:shadow-[0_10px_28px_rgba(49,85,217,0.12)] active:translate-y-0 active:scale-[0.98] active:shadow-[0_6px_18px_rgba(49,85,217,0.1)]"
            >
              Log out
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (data.role !== "student") {
    const researcherPath = data.is_adjudicator ? "/adjudicate" : "/annotate";
    const destination = data.role === "researcher" ? researcherPath : "/classroom";
    const destinationLabel =
      data.role === "researcher"
        ? data.is_adjudicator
          ? "Go to Adjudication Area"
          : "Go to Annotation Area"
        : "Go to Teacher Area";

    return (
      <div className="font-kid min-h-screen bg-background text-foreground flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-surface border border-primary/20 rounded-2xl p-6 sm:p-8 text-center shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
          <p className="text-lg font-bold text-foreground/80 mb-6">
            This part is for students
          </p>
          <Link
            href={destination}
            className="inline-flex min-h-11 items-center justify-center px-6 py-2.5 rounded-xl bg-primary font-extrabold text-on-primary shadow-[0_6px_18px_rgba(49,85,217,0.1)] transition-all hover:-translate-y-[2px] hover:shadow-[0_10px_28px_rgba(49,85,217,0.12)] active:translate-y-0 active:scale-[0.98] active:shadow-[0_6px_18px_rgba(49,85,217,0.1)]"
          >
            {destinationLabel}
          </Link>
          <form action="/auth/signout" method="post" className="mt-4">
            <button
              type="submit"
              className="min-h-11 px-6 py-2.5 rounded-xl border border-primary/20 font-extrabold text-primary transition-colors hover:bg-primary/5"
            >
              Log out
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="font-kid min-h-screen bg-background text-foreground flex flex-col">
      <StudentHeader profileId={profileId} avatarId={data.avatar_id} displayNickname={data.display_nickname} />
      <main className="flex-1 isolate relative z-0 pb-20 md:pb-0">{children}</main>
      <StudentTabBar profileId={profileId} />
    </div>
  );
}
