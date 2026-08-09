"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Users, Books } from "@phosphor-icons/react";
import PendingCount from "./PendingCount";

export default function TeacherTabBar() {
  const pathname = usePathname();
  const match = pathname.match(/^\/classroom\/([^/]+)/);
  if (!match) return null;
  const id = match[1];

  const isRoster = pathname === `/classroom/${id}`;
  const isBooks = pathname.startsWith(`/classroom/${id}/books`);

  return (
    <nav
      className="sm:hidden fixed bottom-0 left-0 right-0 z-30 bg-surface border-t border-primary/15"
      style={{ paddingBottom: "env(safe-area-bottom-inset, env(safe-area-inset-bottom))" }}
    >
      <div className="flex">
        <Link
          href={`/classroom/${id}`}
          aria-current={isRoster ? "page" : undefined}
          className={[
            "font-sans flex flex-1 flex-col items-center gap-0.5 py-2 min-h-[44px]",
            "text-sm font-bold transition-all active:scale-[0.98]",
            isRoster ? "text-primary" : "text-foreground/60",
          ].join(" ")}
        >
          <span aria-hidden="true" className="flex h-6 items-center justify-center">
            <Users weight={isRoster ? "fill" : "regular"} className="h-6 w-6" />
          </span>
          <span>Roster</span>
        </Link>
        <Link
          href={`/classroom/${id}/books`}
          aria-current={isBooks ? "page" : undefined}
          className={[
            "font-sans flex flex-1 flex-col items-center gap-0.5 py-2 min-h-[44px] relative",
            "text-sm font-bold transition-all active:scale-[0.98]",
            isBooks ? "text-primary" : "text-foreground/60",
          ].join(" ")}
        >
          <span aria-hidden="true" className="flex h-6 w-12 items-center justify-center relative">
            <Books weight={isBooks ? "fill" : "regular"} className="h-6 w-6" />
            <div className="absolute top-0 right-0 -mr-2 -mt-1 scale-75 origin-top-right">
              <PendingCount classroomId={id} />
            </div>
          </span>
          <span>Books</span>
        </Link>
      </div>
    </nav>
  );
}
