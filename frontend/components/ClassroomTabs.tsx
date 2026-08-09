"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import PendingCount from "./PendingCount";

export default function ClassroomTabs() {
  const pathname = usePathname();
  const match = pathname.match(/^\/classroom\/([^/]+)/);
  if (!match) return null;
  const id = match[1];
  return (
    <nav className="hidden sm:flex items-center gap-1" aria-label="Classroom tabs">
      <Link
        href={`/classroom/${id}`}
        className="px-4 py-2 rounded-xl text-sm font-bold hover:bg-muted transition-colors"
      >
        Roster
      </Link>
      <Link
        href={`/classroom/${id}/books`}
        className="px-4 py-2 rounded-xl text-sm font-bold hover:bg-muted transition-colors flex items-center"
      >
        Books
        <PendingCount classroomId={id} />
      </Link>
    </nav>
  );
}
