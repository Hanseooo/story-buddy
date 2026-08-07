import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";
import Link from "next/link";

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
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get: (name) => cookieStore.get(name)?.value,
      },
    }
  );

  const { data } = await supabase
    .from("profiles")
    .select("display_nickname, role, classroom_id")
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
              className="min-h-11 px-6 py-2.5 rounded-xl bg-primary font-extrabold text-on-primary shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5"
            >
              Log out
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (data.role !== "student") {
    return (
      <div className="font-kid min-h-screen bg-background text-foreground flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-surface border border-primary/20 rounded-2xl p-6 sm:p-8 text-center shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
          <p className="text-lg font-bold text-foreground/80 mb-6">
            This part is for students
          </p>
          <Link
            href="/classroom"
            className="inline-flex min-h-11 items-center justify-center px-6 py-2.5 rounded-xl bg-primary font-extrabold text-on-primary shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5"
          >
            Go to Teacher Area
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="font-kid min-h-screen bg-background text-foreground flex flex-col">
      <header className="bg-surface border-b border-primary/15 px-5 py-3 sm:px-8">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <span className="font-display text-xl font-extrabold text-primary">
            Hi, {data.display_nickname}!
          </span>
          <form action="/auth/signout" method="post">
            <button
              type="submit"
              className="min-h-11 px-4 py-2 rounded-xl border border-primary/20 font-bold text-sm text-foreground hover:bg-muted transition-colors"
            >
              Log out
            </button>
          </form>
        </div>
      </header>
      <main className="flex-1">{children}</main>
    </div>
  );
}
