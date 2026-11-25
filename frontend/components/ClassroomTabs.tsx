"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import PendingCount from "./PendingCount";

export default function ClassroomTabs() {
  const pathname = usePathname();
  const match = pathname.match(/^\/classroom\/([^/]+)/);
  if (!match) return null;
  const id = match[1];
  const isRoster = pathname === `/classroom/${id}`;
  const isBooks = pathname.startsWith(`/classroom/${id}/books`);
  const tab = (active: boolean) =>
    `min-h-11 px-4 py-2 rounded-xl text-sm font-bold transition-colors flex items-center ${
      active ? "bg-primary/10 text-primary" : "hover:bg-muted"
    }`;
  return (
    <nav className="hidden sm:flex items-center gap-1" aria-label="Classroom tabs">
      <Link
        href={`/classroom/${id}`}
        aria-current={isRoster ? "page" : undefined}
        className={tab(isRoster)}
      >
        Roster
      </Link>
      <Link
        href={`/classroom/${id}/books`}
        aria-current={isBooks ? "page" : undefined}
        className={tab(isBooks)}
      >
        Books
        <PendingCount classroomId={id} />
      </Link>
    </nav>
  );
}
