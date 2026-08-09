import Link from "next/link";
import { getTeacherContext } from "@/utils/supabase/teacher";
import ClassroomSwitcher from "./ClassroomSwitcher";
import ClassroomTabs from "./ClassroomTabs";
import TeacherTabBar from "./TeacherTabBar";
import { SignOut } from "@phosphor-icons/react/dist/ssr";

type Props = {
  children: React.ReactNode;
};

export default async function TeacherShell({ children }: Props) {
  const { profile, classrooms: classList } = await getTeacherContext();

  return (
    <div className="font-sans min-h-screen bg-background text-foreground flex flex-col">
      <header className="bg-surface border-b border-primary/15 px-4 sm:px-8 py-3 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-2 sm:gap-4">
          <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
            <Link href="/" className="hidden sm:flex items-center gap-2 shrink-0">
              <div className="grid size-8 place-items-center rounded-[9px_9px_9px_3px] overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src="/logo.png" alt="" className="h-full w-full object-contain scale-[1.35]" />
              </div>
              <span className="font-display text-lg font-extrabold text-primary">
                StoryBuddy
              </span>
            </Link>
            <ClassroomSwitcher classrooms={classList} />
          </div>

          <ClassroomTabs />

          <div className="flex items-center gap-1 sm:gap-2 shrink-0">
            <Link
              href="/settings"
              className="hidden sm:block text-sm font-bold text-foreground/70 hover:text-foreground px-3 py-2 rounded-xl hover:bg-muted transition-colors"
            >
              {profile.display_name ?? "Settings"}
            </Link>
            <form action="/auth/signout" method="post">
              <button
                type="submit"
                aria-label="Log out"
                className="flex items-center justify-center min-w-10 min-h-10 sm:min-w-0 sm:min-h-11 sm:px-4 sm:py-2 rounded-xl sm:border border-primary/20 text-sm font-bold hover:bg-muted transition-colors text-foreground/70 hover:text-foreground"
              >
                <span className="hidden sm:inline">Log out</span>
                <SignOut weight="bold" className="w-5 h-5 sm:hidden" />
              </button>
            </form>
          </div>
        </div>
      </header>

      <main className="flex-1 pb-20 sm:pb-0">{children}</main>
      <TeacherTabBar />
    </div>
  );
}
