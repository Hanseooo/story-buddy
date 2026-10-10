"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { parseRunFilter, RUNS_QUERY_KEY } from "@/utils/metrics";

const STATUS_OPTIONS = [
  { value: "all", label: "All" },
  { value: "complete", label: "Complete" },
  { value: "failed", label: "Failed" },
  { value: "in_progress", label: "In progress" },
];

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

export default function RunFilters({ styles, hasNoStyle }: { styles: string[]; hasNoStyle: boolean }) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { status, style } = parseRunFilter({ status: params.get("status") ?? undefined, style: params.get("style") ?? undefined });
  const query = params.toString();

  useEffect(() => {
    try {
      sessionStorage.setItem(RUNS_QUERY_KEY, query);
    } catch {
      // Private windows can refuse storage; the back link then falls back to the plain list.
    }
  }, [query]);

  function update(key: "status" | "style", value: string) {
    const next = new URLSearchParams(query);
    if (value === "all") next.delete(key);
    else next.set(key, value);
    const q = next.toString();
    router.replace(q ? `${pathname}?${q}` : pathname, { scroll: false });
  }

  const clearButton = (
    <button
      type="button"
      onClick={() => router.replace(pathname, { scroll: false })}
      className={`inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-on-primary hover:bg-primary-deep ${FOCUS}`}
    >
      Clear filters
    </button>
  );
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div role="group" aria-label="Status" className="flex flex-wrap gap-1.5">
        {STATUS_OPTIONS.map((option) => {
          const pressed = status === option.value;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={pressed}
              onClick={() => update("status", option.value)}
              className={`min-h-11 rounded-full px-4 text-sm font-bold transition-colors ${FOCUS} ${
                pressed ? "bg-primary text-on-primary" : "bg-surface neo-border text-foreground/70 hover:bg-muted/40"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      <label className="flex items-center gap-2 text-sm font-bold text-foreground/70">
        Style
        <select
          value={style}
          onChange={(e) => update("style", e.target.value)}
          className={`min-h-11 rounded-xl bg-surface neo-border px-3 text-sm font-medium text-foreground ${FOCUS}`}
        >
          <option value="all">All styles</option>
          {style !== "all" && style !== "none" && !styles.includes(style) && <option value={style}>{style}</option>}
          {styles.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
          {(hasNoStyle || style === "none") && <option value="none">No style</option>}
        </select>
      </label>
      {(status !== "all" || style !== "all") && clearButton}
    </div>
  );
}
