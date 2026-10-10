"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";
import { ArrowLeft } from "@phosphor-icons/react";
import { RUNS_QUERY_KEY } from "@/utils/metrics";

const noSubscription = () => () => {};

function readQuery(): string | null {
  try {
    return sessionStorage.getItem(RUNS_QUERY_KEY);
  } catch {
    return null;
  }
}

export default function BackLink() {
  const query = useSyncExternalStore(noSubscription, readQuery, () => null);
  return (
    <Link
      href={query ? `/research/metrics?${query}` : "/research/metrics"}
      className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-bold text-foreground/70 hover:text-foreground focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
    >
      <ArrowLeft weight="bold" className="size-4" aria-hidden />
      All runs
    </Link>
  );
}
