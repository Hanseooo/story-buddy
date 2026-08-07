import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";
import { redirect } from "next/navigation";
import Link from "next/link";
import ClassroomSwitcher from "./ClassroomSwitcher";

type Props = {
  classroomId?: string;
  children: React.ReactNode;
};

export default async function TeacherShell({ classroomId, children }: Props) {
  const cookieStore = await cookies();
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { get: (name) => cookieStore.get(name)?.value } }
  );

  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { data: profile } = await supabase
    .from("profiles")
    .select("id, role, display_name")
    .eq("id", user.id)
    .single();

  if (!profile) redirect("/login");
  if (profile.role !== "teacher") redirect(`/s/${profile.id}`);

  const { data: classroomData } = await supabase
    .from("classrooms")
    .select("id, name, code")
    .eq("owner_id", user.id)
    .order("created_at");

  const classList = classroomData ?? [];

  return (
    <div className="font-sans min-h-screen bg-background text-foreground flex flex-col">
      <header className="bg-surface border-b border-primary/15 px-5 py-3 sm:px-8 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-display text-lg font-extrabold text-primary">
              StoryBuddy
            </span>
            <ClassroomSwitcher classrooms={classList} currentId={classroomId} />
          </div>

          {classroomId && (
            <nav
              className="hidden sm:flex items-center gap-1"
              aria-label="Classroom tabs"
            >
              <Link
                href={`/classroom/${classroomId}`}
                className="px-4 py-2 rounded-xl text-sm font-bold hover:bg-muted transition-colors"
              >
                Roster
              </Link>
              <span
                className="px-4 py-2 rounded-xl text-sm font-bold text-foreground/40 cursor-not-allowed"
                aria-disabled="true"
                title="Available in a future update"
              >
                Books
              </span>
            </nav>
          )}

          <div className="flex items-center gap-2">
            <Link
              href="/settings"
              className="hidden sm:block text-sm font-bold text-foreground/70 hover:text-foreground px-3 py-2 rounded-xl hover:bg-muted transition-colors"
            >
              {profile.display_name ?? "Settings"}
            </Link>
            <form action="/auth/signout" method="post">
              <button
                type="submit"
                className="min-h-11 px-4 py-2 rounded-xl border border-primary/20 text-sm font-bold hover:bg-muted transition-colors"
              >
                Log out
              </button>
            </form>
          </div>
        </div>
      </header>

      <main className="flex-1">{children}</main>
    </div>
  );
}
