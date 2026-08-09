import Link from "next/link";
import { getTeacherContext } from "@/utils/supabase/teacher";
import ClassroomSwitcher from "./ClassroomSwitcher";
import ClassroomTabs from "./ClassroomTabs";

type Props = {
  children: React.ReactNode;
};

export default async function TeacherShell({ children }: Props) {
  const { profile, classrooms: classList } = await getTeacherContext();

  return (
    <div className="font-sans min-h-screen bg-background text-foreground flex flex-col">
      <header className="bg-surface border-b border-primary/15 px-5 py-3 sm:px-8 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="font-display text-lg font-extrabold text-primary">
              StoryBuddy
            </span>
            <ClassroomSwitcher classrooms={classList} />
          </div>

          <ClassroomTabs />

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
