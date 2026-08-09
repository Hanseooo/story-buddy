"use client";

import { useEffect, useState } from "react";
import { createBrowserClient } from "@supabase/ssr";

export default function PendingCount({ classroomId }: { classroomId: string }) {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    const supabase = createBrowserClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    );
    supabase
      .from("jobs")
      .select("id", { count: "exact", head: true })
      .eq("classroom_id", classroomId)
      .eq("status", "complete")
      .is("approved_at", null)
      .is("rejected_at", null)
      .then(({ count: c }) => setCount(c));
  }, [classroomId]);

  if (!count) return null;
  return (
    <span
      aria-live="polite"
      className="ml-1 bg-secondary text-foreground text-xs font-bold px-2 py-0.5 rounded-full min-w-[20px] text-center"
    >
      {count}
    </span>
  );
}
