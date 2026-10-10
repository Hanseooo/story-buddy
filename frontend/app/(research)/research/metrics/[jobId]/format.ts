import type { RunStep } from "./types";

export function totalDurationMs(steps: RunStep[]): number | null {
  const known = steps.flatMap((step) => (step.duration_ms == null ? [] : [step.duration_ms]));
  return known.length > 0 ? known.reduce((sum, ms) => sum + ms, 0) : null;
}

export function formatDuration(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const seconds = Math.round(ms / 1000);
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
  return `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min`;
}
