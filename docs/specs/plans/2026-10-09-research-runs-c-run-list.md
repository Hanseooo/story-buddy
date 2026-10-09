# Research Runs C — Run List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `/research/metrics` into a public run log with research aggregates, URL filters, and rows that open a run only for viewers allowed to, without ever sending a hidden title to the browser.

**Architecture:** Pure helpers in `utils/metrics.ts` (aggregates, style breakdown, filters, labels) and `(research)/_shared/viewer.ts` (`canOpenRun`, `hideTitles`). The server page reads `jobs` with the service-role client, nulls hidden titles before rendering, and renders tiles, a by-style table and rows. One small client component, `RunFilters`, owns the URL.

**Tech Stack:** Next.js 16.2 App Router (`searchParams` is a `Promise`; read `frontend/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/page.md`), React 19.2, `@supabase/supabase-js`, Tailwind tokens, `@phosphor-icons/react/dist/ssr` in server components, vitest + Testing Library, pnpm.

**Spec:** `docs/specs/research-run-browser.md` §2, §4.

**Plan set:** A → B → C (this file) → D → E. C needs B's `ResearchViewer`, `getResearchViewer`, metrics `layout.tsx` and `LangfuseButton`. D imports C's `StatusPill`, `statusLabel` and `RUNS_QUERY_KEY`. Branch `feat/research-run-browser`, one PR.

## Global Constraints

- The list stays public. It never selects `input_text`. It selects exactly: `id, status, created_at, style_preset_id, failure_reason, regen_count, image_count, scenes_total, scenes_passed, scenes_unchecked, usd_estimate, langfuse_trace_url, approved_at, title`.
- **A viewer sees a run's title exactly when they can open it.** `title` is set to `null` on the server for every other row, before anything renders.
- Aggregates are computed over all runs; filters apply to the list only.
- "Scene pass rate" is shown as "Page pass rate" (UI only; the field stays `scenePassRate`).
- Filters live in the URL (`?status=failed&style=cel`) and change with `router.replace`, so back from a run restores them.
- Newest first, no pagination.
- Desktop table, cards below `md`. A row the viewer can open is one link named "Open run <title or short id>" and the whole row is clickable.
- Locked rows: signed out → "Sign in to view" linking to `/login?next=/research/metrics/<id>`; researcher on an unapproved run → "Not approved yet"; any other signed-in role → "Researchers only".
- Langfuse buttons only through `LangfuseButton` (flag-gated, warned).
- Every control at least 44 px tall; repo focus ring `focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3`.
- Commits carry no `Co-Authored-By` or generated-by trailer.

## Review Focus

1. **A hidden title in the HTML.** Rendering the row before nulling the title, or passing raw rows to a client component, would ship it. Expect the title absent from the rendered page for a signed-out viewer. Pinned in Task 6 (`page.test.tsx`).
2. **A hand-edited filter** (`?status=bogus`, `?style=` with an unknown style). Expect "all" for an unknown status and the "No runs match these filters" state with a way out for an unknown style, never a crash. Pinned in Task 3.
3. **Runs with no style.** They must form their own "No style" group in the table and be filterable with `style=none`. Pinned in Tasks 2 and 3.
4. **A failed run with no `failure_reason`.** The Failed split must still add up to the Failed count. Pinned in Task 1 ("no reason recorded").
5. **Images per page with no drawn pages yet** (every run failed early). Expect "—", not `NaN` or `Infinity`. Pinned in Task 1.

---

## File map

| File | Responsibility |
|---|---|
| `frontend/utils/metrics.ts` (modify) | `JobRow` fields, new aggregates, `failedSplit`, `styleBreakdown`, `parseRunFilter`, `filterJobs`, `statusLabel`, `RUNS_QUERY_KEY` |
| `frontend/utils/metrics.test.ts` (create) | tests for the above |
| `frontend/app/(research)/_shared/viewer.ts` (modify) | `canOpenRun`, `hideTitles` |
| `frontend/app/(research)/_shared/viewer.test.ts` (create) | access rule tests |
| `frontend/app/(research)/research/metrics/RunFilters.tsx` (create) + `RunFilters.test.tsx` | status chips and style select in the URL |
| `frontend/app/(research)/research/metrics/StatusPill.tsx` (create) | status pill, shared with D |
| `frontend/app/(research)/research/metrics/page.tsx` (rewrite) | the list |
| `frontend/app/(research)/research/metrics/page.test.tsx` (modify) | render tests for title hiding |
| `frontend/app/(research)/research/metrics/loading.tsx` (rewrite), `error.tsx` (create) | states |

All commands run from `frontend/`.

---

### Task 1: New aggregates

**Files:**
- Modify: `frontend/utils/metrics.ts`
- Test: `frontend/utils/metrics.test.ts` (create)

**Interfaces:**
- Produces:
  - `JobRow` gains `image_count?, scenes_unchecked?: number | null`, `approved_at?, title?: string | null`.
  - `computeAggregates(jobs)` additionally returns `failedByReason: Record<string, number>` (key `"unrecorded"` for a null reason), `uncheckedPages: number`, `imagesPerPage: number | null`, `pagesTotal: number`.
  - `failedSplit(byReason: Record<string, number>): string`, e.g. `"4 pipeline error · 1 content blocked"`, largest first.

- [ ] **Step 1: Write the failing tests.** Create `frontend/utils/metrics.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { computeAggregates, failedSplit, JobRow } from "@/utils/metrics";

const run = (over: Partial<JobRow>): JobRow => ({ id: "x", status: "complete", created_at: "2026-10-01", ...over });

describe("new aggregates", () => {
  it("splits failures by reason, counting a missing reason", () => {
    const jobs = [
      run({ status: "failed", failure_reason: "machine" }),
      run({ status: "failed", failure_reason: "machine" }),
      run({ status: "failed", failure_reason: "machine" }),
      run({ status: "failed", failure_reason: "machine" }),
      run({ status: "failed", failure_reason: "child_text" }),
      run({ status: "failed", failure_reason: null }),
    ];
    const stats = computeAggregates(jobs);

    expect(stats.failedByReason).toEqual({ machine: 4, child_text: 1, unrecorded: 1 });
    expect(failedSplit(stats.failedByReason)).toBe("4 pipeline error · 1 content blocked · 1 no reason recorded");
  });

  it("sums unchecked pages and divides images by pages where both are set", () => {
    const stats = computeAggregates([
      run({ scenes_unchecked: 2, image_count: 9, scenes_total: 6 }),
      run({ scenes_unchecked: 1, image_count: 4, scenes_total: 4 }),
      run({ scenes_unchecked: null, image_count: 5, scenes_total: null }),
    ]);

    expect(stats.uncheckedPages).toBe(3);
    expect(stats.imagesPerPage).toBe(13 / 10);
    expect(stats.pagesTotal).toBe(10);
  });

  it("has no images-per-page figure before any page is drawn", () => {
    const stats = computeAggregates([run({ status: "failed", failure_reason: "machine" })]);

    expect(stats.imagesPerPage).toBeNull();
    expect(stats.uncheckedPages).toBe(0);
  });
});
```

- [ ] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run utils/metrics.test.ts`
Expected: FAIL, `failedSplit` is not exported / `failedByReason` is `undefined`.

- [ ] **Step 3: Implement.** In `frontend/utils/metrics.ts`, extend `JobRow`:

```ts
export interface JobRow {
  id: string;
  status: string;
  created_at: string;
  style_preset_id?: string | null;
  classroom_id?: string | null;
  failure_reason?: string | null;
  regen_count?: number | null;
  image_count?: number | null;
  scenes_total?: number | null;
  scenes_passed?: number | null;
  scenes_unchecked?: number | null;
  usd_estimate?: number | null;
  langfuse_trace_url?: string | null;
  approved_at?: string | null;
  title?: string | null;
}
```

In `computeAggregates`, add beside the existing accumulators:

```ts
  const failedByReason: Record<string, number> = {};
  let uncheckedPages = 0;
  let imageSum = 0;
  let pagesWithImages = 0;
```

inside the existing `for (const job of jobs)` loop:

```ts
    if (job.status === "failed") {
      const reason = job.failure_reason ?? "unrecorded";
      failedByReason[reason] = (failedByReason[reason] ?? 0) + 1;
    }
    if (job.scenes_unchecked != null) {
      uncheckedPages += job.scenes_unchecked;
    }
    // Only runs that recorded both: a failed run usually wrote image_count but never scenes_total.
    if (job.image_count != null && job.scenes_total != null) {
      imageSum += job.image_count;
      pagesWithImages += job.scenes_total;
    }
```

and add to the returned object:

```ts
    failedByReason,
    uncheckedPages,
    imagesPerPage: pagesWithImages > 0 ? imageSum / pagesWithImages : null,
    pagesTotal: sumTotalScenes,
```

After `failureLabel`, add:

```ts
export function failedSplit(byReason: Record<string, number>): string {
  return Object.entries(byReason)
    .sort(([, a], [, b]) => b - a)
    .map(([reason, n]) => `${n} ${reason === "unrecorded" ? "no reason recorded" : failureLabel(reason).toLowerCase()}`)
    .join(" · ");
}
```

- [ ] **Step 4: Run them, plus the existing aggregate tests.**

Run: `pnpm exec vitest run utils/metrics.test.ts "app/(research)/research/metrics/page.test.tsx"`
Expected: all PASS.

- [ ] **Step 5: Commit.**

```bash
git add utils/metrics.ts utils/metrics.test.ts
git commit -m "feat(metrics): failed split, unchecked pages, images per page"
```

---

### Task 2: By-style breakdown

**Files:**
- Modify: `frontend/utils/metrics.ts`
- Test: `frontend/utils/metrics.test.ts` (append)

**Interfaces:**
- Consumes: `computeAggregates` (Task 1).
- Produces: `type StyleRow = { style: string | null; runs: number; jobPassRate: number | null; pagePassRate: number | null; avgCost: number | null }` and `styleBreakdown(jobs: JobRow[]): StyleRow[]`, most runs first, the `null` ("No style") group last. A rate is `null` when nothing in the group could produce it.

- [ ] **Step 1: Write the failing test.** Append:

```ts
import { styleBreakdown } from "@/utils/metrics";

describe("styleBreakdown", () => {
  it("groups by style with No style last", () => {
    const rows = styleBreakdown([
      run({ style_preset_id: "cel", status: "complete", scenes_total: 5, scenes_passed: 5, usd_estimate: 0.25 }),
      run({ style_preset_id: "cel", status: "failed", usd_estimate: 0.125 }),
      run({ style_preset_id: null, status: "complete", scenes_total: 2, scenes_passed: 2 }),
      run({ style_preset_id: "gouache", status: "complete", scenes_total: 4, scenes_passed: 3, usd_estimate: 0.5 }),
      run({ style_preset_id: "gouache", status: "running" }),
    ]);

    expect(rows).toEqual([
      { style: "cel", runs: 2, jobPassRate: 0.5, pagePassRate: 1, avgCost: 0.1875 },
      { style: "gouache", runs: 2, jobPassRate: 1, pagePassRate: 0.75, avgCost: 0.5 },
      { style: null, runs: 1, jobPassRate: 1, pagePassRate: 1, avgCost: null },
    ]);
  });
});
```

(Move the import to the top of the file.)

- [ ] **Step 2: Run it and confirm it fails.**

Run: `pnpm exec vitest run utils/metrics.test.ts -t styleBreakdown`
Expected: FAIL, `styleBreakdown is not a function`.

- [ ] **Step 3: Implement.** Append to `utils/metrics.ts`:

```ts
export type StyleRow = {
  style: string | null;
  runs: number;
  jobPassRate: number | null;
  pagePassRate: number | null;
  avgCost: number | null;
};

export function styleBreakdown(jobs: JobRow[]): StyleRow[] {
  const groups = new Map<string | null, JobRow[]>();
  for (const job of jobs) {
    const key = job.style_preset_id ?? null;
    groups.set(key, [...(groups.get(key) ?? []), job]);
  }
  return [...groups]
    .map(([style, rows]) => {
      const s = computeAggregates(rows);
      const costed = rows.filter((r) => r.usd_estimate != null);
      return {
        style,
        runs: rows.length,
        jobPassRate: s.complete + s.failed > 0 ? s.jobPassRate : null,
        pagePassRate: s.pagesTotal > 0 ? s.scenePassRate : null,
        avgCost: costed.length > 0 ? costed.reduce((sum, r) => sum + Number(r.usd_estimate), 0) / costed.length : null,
      };
    })
    .sort((a, b) => (a.style === null ? 1 : b.style === null ? -1 : b.runs - a.runs));
}
```

- [ ] **Step 4: Run it and confirm it passes.**

Run: `pnpm exec vitest run utils/metrics.test.ts`
Expected: all PASS.

- [ ] **Step 5: Commit.**

```bash
git add utils/metrics.ts utils/metrics.test.ts
git commit -m "feat(metrics): by-style breakdown"
```

---

### Task 3: Filters, status labels, the remembered query key

**Files:**
- Modify: `frontend/utils/metrics.ts`
- Test: `frontend/utils/metrics.test.ts` (append)

**Interfaces:**
- Produces:
  - `type RunStatusFilter = "all" | "complete" | "failed" | "in_progress"`; `type RunFilter = { status: RunStatusFilter; style: string }` where `style` is `"all"`, `"none"` (no style) or a preset id.
  - `parseRunFilter(params: Record<string, string | string[] | undefined>): RunFilter`; an unknown status reads as `"all"`.
  - `filterJobs(jobs: JobRow[], filter: RunFilter): JobRow[]`; `in_progress` is any status other than `complete` and `failed`.
  - `STATUS_LABELS` and `statusLabel(status: string): string` (`complete` → "Complete", `failed` → "Failed", `queued` → "Queued", `running` → "Running", `awaiting_confirm` → "Waiting for the child"; unknown passes through).
  - `RUNS_QUERY_KEY = "research-runs-query"`: sessionStorage key `RunFilters` writes and Plan D's back link reads.

- [ ] **Step 1: Write the failing tests.** Append:

```ts
import { filterJobs, parseRunFilter } from "@/utils/metrics";

describe("run filters", () => {
  const jobs = [
    run({ id: "a", status: "complete", style_preset_id: "cel" }),
    run({ id: "b", status: "failed", style_preset_id: "cel" }),
    run({ id: "c", status: "awaiting_confirm", style_preset_id: null }),
    run({ id: "d", status: "failed", style_preset_id: null }),
  ];
  const ids = (rows: JobRow[]) => rows.map((r) => r.id);

  it("reads the URL, treating an unknown status as all", () => {
    expect(parseRunFilter({ status: "failed", style: "cel" })).toEqual({ status: "failed", style: "cel" });
    expect(parseRunFilter({ status: "bogus" })).toEqual({ status: "all", style: "all" });
    expect(parseRunFilter({ status: ["failed", "complete"] })).toEqual({ status: "failed", style: "all" });
  });

  it("filters by status, by missing style, and by both", () => {
    expect(ids(filterJobs(jobs, { status: "in_progress", style: "all" }))).toEqual(["c"]);
    expect(ids(filterJobs(jobs, { status: "all", style: "none" }))).toEqual(["c", "d"]);
    expect(ids(filterJobs(jobs, { status: "failed", style: "cel" }))).toEqual(["b"]);
    expect(ids(filterJobs(jobs, { status: "all", style: "pixel" }))).toEqual([]);
  });
});
```

- [ ] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run utils/metrics.test.ts -t "run filters"`
Expected: FAIL, `parseRunFilter is not a function`.

- [ ] **Step 3: Implement.** Append to `utils/metrics.ts`:

```ts
export type RunStatusFilter = "all" | "complete" | "failed" | "in_progress";
export type RunFilter = { status: RunStatusFilter; style: string };

const STATUS_FILTERS: RunStatusFilter[] = ["all", "complete", "failed", "in_progress"];

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export function parseRunFilter(params: Record<string, string | string[] | undefined>): RunFilter {
  const status = first(params.status);
  return {
    status: STATUS_FILTERS.includes(status as RunStatusFilter) ? (status as RunStatusFilter) : "all",
    style: first(params.style) || "all",
  };
}

export function filterJobs(jobs: JobRow[], filter: RunFilter): JobRow[] {
  return jobs.filter((job) => {
    const status =
      filter.status === "all" ||
      (filter.status === "in_progress"
        ? job.status !== "complete" && job.status !== "failed"
        : job.status === filter.status);
    const style =
      filter.style === "all" ||
      (filter.style === "none" ? job.style_preset_id == null : job.style_preset_id === filter.style);
    return status && style;
  });
}

export const STATUS_LABELS: Record<string, string> = {
  complete: "Complete",
  failed: "Failed",
  queued: "Queued",
  running: "Running",
  awaiting_confirm: "Waiting for the child",
};

export function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

// sessionStorage key: the list writes its query here, the run page's back link reads it.
export const RUNS_QUERY_KEY = "research-runs-query";
```

- [ ] **Step 4: Run them and confirm they pass.**

Run: `pnpm exec vitest run utils/metrics.test.ts`
Expected: all PASS.

- [ ] **Step 5: Commit.**

```bash
git add utils/metrics.ts utils/metrics.test.ts
git commit -m "feat(metrics): run filters and status labels"
```

---

### Task 4: `canOpenRun` and `hideTitles`

**Files:**
- Modify: `frontend/app/(research)/_shared/viewer.ts`
- Test: `frontend/app/(research)/_shared/viewer.test.ts` (create)

**Interfaces:**
- Consumes: `ResearchViewer` (Plan B Task 3).
- Produces:
  - `canOpenRun(viewer: ResearchViewer | null, job: { approved_at?: string | null }): boolean`: researcher and (adjudicator or approved). Mirrors the backend rule (ADR-064 rule 2); the backend still enforces it on its own.
  - `hideTitles<T extends { title?: string | null; approved_at?: string | null }>(viewer: ResearchViewer | null, jobs: T[]): T[]`: copies with `title: null` where `canOpenRun` is false.

- [ ] **Step 1: Write the failing tests.** Create `viewer.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { canOpenRun, hideTitles, ResearchViewer } from "./viewer";

const annotator: ResearchViewer = { id: "r-1", role: "researcher", isAdjudicator: false, displayName: null };
const adjudicator: ResearchViewer = { id: "r-2", role: "researcher", isAdjudicator: true, displayName: null };
const teacher: ResearchViewer = { id: "t-1", role: "teacher", isAdjudicator: false, displayName: null };
const approved = { approved_at: "2026-10-02T00:00:00Z" };
const unapproved = { approved_at: null };

describe("canOpenRun", () => {
  it.each([
    ["signed out", null, false, false],
    ["teacher", teacher, false, false],
    ["annotator", annotator, true, false],
    ["adjudicator", adjudicator, true, true],
  ] as const)("%s: approved %s, unapproved %s", (_, viewer, onApproved, onUnapproved) => {
    expect(canOpenRun(viewer, approved)).toBe(onApproved);
    expect(canOpenRun(viewer, unapproved)).toBe(onUnapproved);
  });
});

describe("hideTitles", () => {
  it("keeps a title only where the viewer can open the run", () => {
    const rows = [
      { id: "a", title: "Approved Kite", ...approved },
      { id: "b", title: "Unapproved Kite", ...unapproved },
    ];

    expect(hideTitles(annotator, rows).map((r) => r.title)).toEqual(["Approved Kite", null]);
    expect(hideTitles(null, rows).map((r) => r.title)).toEqual([null, null]);
    expect(rows[1].title).toBe("Unapproved Kite"); // input untouched
  });
});
```

- [ ] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run "app/(research)/_shared/viewer.test.ts"`
Expected: FAIL, `canOpenRun is not a function`.

- [ ] **Step 3: Implement.** Append to `viewer.ts`:

```ts
// One rule for the title and the link: a viewer sees a run's title exactly when they can open it.
// The backend enforces the same rule on its own (ADR-064 rule 2); this only decides what renders.
export function canOpenRun(viewer: ResearchViewer | null, job: { approved_at?: string | null }): boolean {
  return viewer?.role === "researcher" && (viewer.isAdjudicator || job.approved_at != null);
}

export function hideTitles<T extends { title?: string | null; approved_at?: string | null }>(
  viewer: ResearchViewer | null,
  jobs: T[]
): T[] {
  return jobs.map((job) => (canOpenRun(viewer, job) ? job : { ...job, title: null }));
}
```

- [ ] **Step 4: Run them and confirm they pass.**

Run: `pnpm exec vitest run "app/(research)/_shared/viewer.test.ts"`
Expected: 5 passed.

- [ ] **Step 5: Commit.**

```bash
git add "app/(research)/_shared/viewer.ts" "app/(research)/_shared/viewer.test.ts"
git commit -m "feat(research): canOpenRun decides both the title and the link"
```

---

### Task 5: `RunFilters`

**Files:**
- Create: `frontend/app/(research)/research/metrics/RunFilters.tsx`
- Test: `frontend/app/(research)/research/metrics/RunFilters.test.tsx`

**Interfaces:**
- Consumes: `RUNS_QUERY_KEY` (Task 3).
- Produces: `RunFilters({ styles, hasNoStyle }: { styles: string[]; hasNoStyle: boolean })`, default export, client component. Status chips are `<button aria-pressed>` in a group named "Status"; the style control is a native `<select>` labelled "Style". Writes the current query to `sessionStorage[RUNS_QUERY_KEY]` (try/catch; private windows may throw).

- [ ] **Step 1: Write the failing test.**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import RunFilters from "./RunFilters";

const replace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/research/metrics",
  useSearchParams: () => new URLSearchParams("style=cel"),
}));

describe("RunFilters", () => {
  it("keeps the other filter and replaces history instead of pushing", () => {
    render(<RunFilters styles={["cel", "gouache"]} hasNoStyle />);

    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Failed" }));
    expect(replace).toHaveBeenLastCalledWith("/research/metrics?style=cel&status=failed", { scroll: false });

    fireEvent.change(screen.getByLabelText("Style"), { target: { value: "all" } });
    expect(replace).toHaveBeenLastCalledWith("/research/metrics", { scroll: false });
  });
});
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/RunFilters.test.tsx"`
Expected: FAIL, `Failed to resolve import "./RunFilters"`.

- [ ] **Step 3: Implement.**

```tsx
"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { RUNS_QUERY_KEY } from "@/utils/metrics";

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
  const status = params.get("status") ?? "all";
  const style = params.get("style") ?? "all";
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
          {styles.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
          {hasNoStyle && <option value="none">No style</option>}
        </select>
      </label>
    </div>
  );
}
```

- [ ] **Step 4: Run it and confirm it passes.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/RunFilters.test.tsx"`
Expected: 1 passed.

- [ ] **Step 5: Commit.**

```bash
git add "app/(research)/research/metrics/RunFilters.tsx" "app/(research)/research/metrics/RunFilters.test.tsx"
git commit -m "feat(metrics): status and style filters in the URL"
```

---

### Task 6: The list page, its states, and title hiding end to end

**Files:**
- Create: `frontend/app/(research)/research/metrics/StatusPill.tsx`
- Rewrite: `frontend/app/(research)/research/metrics/page.tsx`
- Rewrite: `frontend/app/(research)/research/metrics/loading.tsx`
- Create: `frontend/app/(research)/research/metrics/error.tsx`
- Test: `frontend/app/(research)/research/metrics/page.test.tsx` (append)

**Interfaces:**
- Consumes: everything from Tasks 1-5; `getResearchViewer` (B3); `LangfuseButton` (B5).
- Produces: `StatusPill({ status }: { status: string })`, default export, server-safe (no hooks). Plan D's header uses it.

- [ ] **Step 1: Write the failing render tests.** Append to `page.test.tsx` (its existing `computeAggregates` tests stay):

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, vi, beforeEach } from "vitest";
import RunsPage from "./page";

const RUN_ID = "3f9a1c2e-0000-4000-8000-000000000001";
const mockViewer = vi.hoisted(() => vi.fn());
const mockRows = vi.hoisted(() => vi.fn());

vi.mock("../../_shared/getResearchViewer", () => ({ getResearchViewer: mockViewer }));
vi.mock("@supabase/supabase-js", () => ({
  createClient: () => ({ from: () => ({ select: () => ({ order: mockRows }) }) }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/research/metrics",
  useSearchParams: () => new URLSearchParams(),
}));

describe("RunsPage", () => {
  beforeEach(() => {
    mockRows.mockResolvedValue({
      data: [{ id: RUN_ID, status: "failed", created_at: "2026-10-01T10:00:00Z", title: "Secret Kite",
               approved_at: null, failure_reason: "machine", style_preset_id: "cel" }],
      error: null,
    });
  });

  it("signed out: no title anywhere, and a sign-in link to the run", async () => {
    mockViewer.mockResolvedValue(null);
    render(await RunsPage({ searchParams: Promise.resolve({}) }));

    expect(screen.queryByText(/Secret Kite/)).toBeNull();
    expect(screen.getAllByRole("link", { name: "Sign in to view" })[0]).toHaveAttribute(
      "href",
      `/login?next=/research/metrics/${RUN_ID}`
    );
  });

  it("adjudicator: the row is a link named after the title", async () => {
    mockViewer.mockResolvedValue({ id: "r-2", role: "researcher", isAdjudicator: true, displayName: null });
    render(await RunsPage({ searchParams: Promise.resolve({}) }));

    expect(screen.getAllByRole("link", { name: "Open run Secret Kite" })[0]).toHaveAttribute(
      "href",
      `/research/metrics/${RUN_ID}`
    );
  });
});
```

Merge the `vitest` import with the file's existing one (`expect, test`).

- [ ] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/page.test.tsx"`
Expected: the two `RunsPage` tests FAIL (the current page renders no titles or links of this shape, and takes no `searchParams`); the four aggregate tests pass.

- [ ] **Step 3: Write `StatusPill.tsx`.**

```tsx
import { statusLabel } from "@/utils/metrics";

const TONE: Record<string, string> = {
  complete: "bg-success/15 text-success",
  failed: "bg-destructive/15 text-destructive",
  awaiting_confirm: "bg-warning/20 text-foreground",
};

export default function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider ${
        TONE[status] ?? "bg-muted text-foreground/70"
      }`}
    >
      {statusLabel(status)}
    </span>
  );
}
```

- [ ] **Step 4: Rewrite `page.tsx`.**

```tsx
import { createClient } from "@supabase/supabase-js";
import Link from "next/link";
import { CheckCircle, Clock, Lock, XCircle } from "@phosphor-icons/react/dist/ssr";
import LangfuseButton from "@/components/LangfuseButton";
import {
  computeAggregates,
  failedSplit,
  failureLabel,
  filterJobs,
  formatJob,
  JobRow,
  parseRunFilter,
  styleBreakdown,
} from "@/utils/metrics";
import { getResearchViewer } from "../../_shared/getResearchViewer";
import { canOpenRun, hideTitles, ResearchViewer } from "../../_shared/viewer";
import RunFilters from "./RunFilters";
import StatusPill from "./StatusPill";

export const revalidate = 0;

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

const pct = (rate: number | null) => (rate == null ? "—" : `${(rate * 100).toFixed(1)}%`);
const usd = (value: number | null) => (value == null ? "—" : `$${value.toFixed(4)}`);

function Tile({ label, value, note, tone = "text-foreground" }: { label: string; value: string; note: string; tone?: string }) {
  return (
    <div className="flex flex-col justify-between gap-3 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6">
      <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">{label}</div>
      <div className={`font-display text-3xl font-extrabold sm:text-4xl ${tone}`}>{value}</div>
      <p className="text-xs font-medium text-foreground/50">{note}</p>
    </div>
  );
}

function RunName({ job, viewer }: { job: JobRow; viewer: ResearchViewer | null }) {
  const name = job.title ?? `Run ${formatJob(job).shortId}`;
  if (canOpenRun(viewer, job)) {
    // after:inset-0 stretches this link over its row or card, so the whole row opens the run.
    return (
      <Link
        href={`/research/metrics/${job.id}`}
        aria-label={`Open run ${name}`}
        className={`font-bold text-foreground after:absolute after:inset-0 hover:text-primary ${FOCUS}`}
      >
        {name}
      </Link>
    );
  }
  return (
    <div className="flex flex-col gap-0.5">
      <span className="font-mono font-medium text-foreground">{name}</span>
      <span className="inline-flex items-center gap-1 text-xs text-foreground/60">
        <Lock weight="bold" className="size-3.5" aria-hidden />
        {viewer === null ? (
          <Link
            href={`/login?next=/research/metrics/${job.id}`}
            className={`relative z-10 inline-flex min-h-11 items-center font-bold text-primary hover:underline ${FOCUS}`}
          >
            Sign in to view
          </Link>
        ) : viewer.role === "researcher" ? (
          "Not approved yet"
        ) : (
          "Researchers only"
        )}
      </span>
    </div>
  );
}

export default async function RunsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const supabase = createClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE_KEY!);
  const [viewer, { data, error }] = await Promise.all([
    getResearchViewer(),
    supabase
      .from("jobs")
      .select(`
        id, status, created_at, style_preset_id, failure_reason, regen_count, image_count,
        scenes_total, scenes_passed, scenes_unchecked, usd_estimate, langfuse_trace_url,
        approved_at, title
      `)
      .order("created_at", { ascending: false }),
  ]);
  if (error) throw new Error(error.message);

  // A title is redacted (ADR-059) but can still identify a donated story (#108). It leaves the
  // server only for a viewer who can open that run.
  const jobs = hideTitles(viewer, (data ?? []) as JobRow[]);
  const stats = computeAggregates(jobs);
  const byStyle = styleBreakdown(jobs);
  const filter = parseRunFilter(await searchParams);
  const shown = filterJobs(jobs, filter);
  const styleIds = byStyle.flatMap((row) => (row.style ? [row.style] : []));
  const hasNoStyle = byStyle.some((row) => row.style === null);
  const showTrace = process.env.NEXT_PUBLIC_SHOW_LANGFUSE_LINKS === "true";
  const concluded = stats.complete + stats.failed;

  return (
    <main className="mx-auto max-w-7xl space-y-8 p-4 font-sans sm:p-6 lg:space-y-10 lg:p-10">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Runs</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          Every story the pipeline has run, with research totals. Signed-in researchers can open a run to see the
          path it took through the graph.
        </p>
      </div>

      <section aria-label="Totals" className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
        <Tile label="Total runs" value={String(stats.totalRuns)} note="Every submitted story, newest first below." />
        <Tile
          label="Job pass rate"
          value={pct(concluded > 0 ? stats.jobPassRate : null)}
          note={`${stats.complete} of ${concluded} finished runs made a book.`}
          tone="text-primary"
        />
        <Tile
          label="Page pass rate"
          value={pct(stats.pagesTotal > 0 ? stats.scenePassRate : null)}
          note="Pages the judge passed, across runs that drew pages."
        />
        <Tile label="Est. total cost" value={`$${stats.estCost.toFixed(2)}`} note="Estimated OpenRouter and fal.ai spend, USD." />
        <Tile label="Unchecked pages" value={String(stats.uncheckedPages)} note="Pages the judge gave no answer on." />
        <Tile
          label="Images per page"
          value={stats.imagesPerPage == null ? "—" : stats.imagesPerPage.toFixed(2)}
          note="1.0 means no redraws."
        />
      </section>

      <section aria-label="Status" className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
        <div className="flex items-center justify-between rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Complete</div>
          <div className="flex items-center gap-2 font-display text-xl font-bold text-success">
            {stats.complete} <CheckCircle weight="fill" className="size-5" aria-hidden />
          </div>
        </div>
        <div className="flex flex-col gap-1 rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
          <div className="flex items-center justify-between">
            <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Failed</div>
            <div className="flex items-center gap-2 font-display text-xl font-bold text-destructive">
              {stats.failed} <XCircle weight="fill" className="size-5" aria-hidden />
            </div>
          </div>
          {stats.failed > 0 && <p className="text-xs font-medium text-foreground/60">{failedSplit(stats.failedByReason)}</p>}
        </div>
        <div className="flex items-center justify-between rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
          <div className="text-xs font-semibold uppercase tracking-widest text-foreground/50">In progress</div>
          <div className="flex items-center gap-2 font-display text-xl font-bold text-foreground/70">
            {stats.inProgress} <Clock weight="fill" className="size-5" aria-hidden />
          </div>
        </div>
      </section>

      {byStyle.length > 0 && (
        <section className="space-y-3">
          <h2 className="font-display text-2xl font-bold">By style</h2>
          <div className="overflow-x-auto rounded-2xl bg-surface neo-border neo-shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-muted bg-muted/20 text-xs font-semibold uppercase tracking-wider text-foreground/50">
                <tr>
                  <th scope="col" className="px-4 py-3">Style</th>
                  <th scope="col" className="px-4 py-3">Runs</th>
                  <th scope="col" className="px-4 py-3">Job pass</th>
                  <th scope="col" className="px-4 py-3">Page pass</th>
                  <th scope="col" className="px-4 py-3">Avg cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-muted/40 font-mono text-xs">
                {byStyle.map((row) => (
                  <tr key={row.style ?? "none"}>
                    <th scope="row" className="px-4 py-3 font-sans font-bold">{row.style ?? "No style"}</th>
                    <td className="px-4 py-3">{row.runs}</td>
                    <td className="px-4 py-3">{pct(row.jobPassRate)}</td>
                    <td className="px-4 py-3">{pct(row.pagePassRate)}</td>
                    <td className="px-4 py-3">{usd(row.avgCost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="space-y-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 className="font-display text-2xl font-bold">All runs</h2>
          {jobs.length > 0 && <RunFilters styles={styleIds} hasNoStyle={hasNoStyle} />}
        </div>

        {jobs.length === 0 ? (
          <div className="rounded-3xl bg-surface p-8 text-center neo-border neo-shadow-sm">
            <p className="font-bold">No runs recorded yet.</p>
            <p className="mt-1 text-sm text-foreground/60">A run appears here when a student submits a story.</p>
          </div>
        ) : shown.length === 0 ? (
          <div className="flex flex-col items-center gap-4 rounded-3xl bg-surface p-8 text-center neo-border neo-shadow-sm">
            <p className="font-bold">No runs match these filters</p>
            <Link
              href="/research/metrics"
              replace
              scroll={false}
              className={`inline-flex min-h-11 items-center rounded-xl bg-primary px-5 text-sm font-bold text-on-primary hover:bg-primary-deep ${FOCUS}`}
            >
              Clear filters
            </Link>
          </div>
        ) : (
          <>
            <div className="hidden overflow-hidden rounded-3xl bg-surface neo-border neo-shadow-sm md:block">
              <table className="w-full text-left text-sm text-foreground/80">
                <thead className="border-b border-muted bg-muted/20 text-xs font-semibold uppercase tracking-wider text-foreground/50">
                  <tr>
                    <th scope="col" className="px-6 py-4">Run</th>
                    <th scope="col" className="px-6 py-4">Status</th>
                    <th scope="col" className="px-6 py-4">Style</th>
                    <th scope="col" className="px-6 py-4">Pages</th>
                    <th scope="col" className="px-6 py-4">Redraws</th>
                    <th scope="col" className="px-6 py-4">Cost</th>
                    <th scope="col" className="px-6 py-4">Created</th>
                    {showTrace && <th scope="col" className="px-6 py-4 text-right">Trace</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-muted/40">
                  {shown.map((job) => {
                    const { shortId, formattedDate, scenesDisplay, costDisplay } = formatJob(job);
                    return (
                      <tr key={job.id} className="relative transition-colors hover:bg-muted/10">
                        <td className="px-6 py-4"><RunName job={job} viewer={viewer} /></td>
                        <td className="whitespace-nowrap px-6 py-4">
                          <StatusPill status={job.status} />
                          {job.status === "failed" && job.failure_reason && (
                            <div className="mt-1 text-[11px] font-medium text-destructive/80">{failureLabel(job.failure_reason)}</div>
                          )}
                        </td>
                        <td className="whitespace-nowrap px-6 py-4 text-xs font-medium">{job.style_preset_id ?? "No style"}</td>
                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs">{scenesDisplay}</td>
                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs">{job.regen_count ?? "—"}</td>
                        <td className="whitespace-nowrap px-6 py-4 font-mono text-xs">{costDisplay}</td>
                        <td className="whitespace-nowrap px-6 py-4 text-xs text-foreground/60">{formattedDate}</td>
                        {showTrace && (
                          <td className="whitespace-nowrap px-6 py-4 text-right">
                            <LangfuseButton
                              url={job.langfuse_trace_url}
                              label={`Open Langfuse trace for ${job.title ?? `run ${shortId}`}`}
                            />
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <ul className="grid grid-cols-1 gap-4 md:hidden">
              {shown.map((job) => {
                const { shortId, formattedDate, scenesDisplay, costDisplay } = formatJob(job);
                return (
                  <li key={job.id} className="relative flex flex-col gap-4 rounded-2xl bg-surface p-5 neo-border neo-shadow-sm">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex min-w-0 flex-col gap-1">
                        <RunName job={job} viewer={viewer} />
                        <span className="text-xs font-medium text-foreground/50">{formattedDate}</span>
                      </div>
                      <StatusPill status={job.status} />
                    </div>
                    {job.status === "failed" && job.failure_reason && (
                      <div className="rounded-lg bg-destructive/10 p-3 text-xs font-medium text-destructive/90">
                        {failureLabel(job.failure_reason)}
                      </div>
                    )}
                    <dl className="grid grid-cols-3 gap-2 border-y border-muted/40 py-3">
                      <div><dt className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Pages</dt><dd className="font-mono text-sm">{scenesDisplay}</dd></div>
                      <div><dt className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Redraws</dt><dd className="font-mono text-sm">{job.regen_count ?? "—"}</dd></div>
                      <div><dt className="text-[10px] font-bold uppercase tracking-wider text-foreground/40">Cost</dt><dd className="font-mono text-sm">{costDisplay}</dd></div>
                    </dl>
                    <div className="flex items-center justify-between">
                      <span className="rounded-md bg-muted/40 px-2 py-1 text-xs font-medium">{job.style_preset_id ?? "No style"}</span>
                      <LangfuseButton url={job.langfuse_trace_url} label={`Open Langfuse trace for ${job.title ?? `run ${shortId}`}`} />
                    </div>
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </section>
    </main>
  );
}
```

The old "How are these calculated?" `<details>` is gone on purpose: each tile carries its own note (spec §4).

- [ ] **Step 5: Run the tests and confirm they pass.**

Run: `pnpm exec vitest run "app/(research)/research/metrics"`
Expected: all PASS.

- [ ] **Step 6: Break it on purpose.** In `page.tsx`, replace `hideTitles(viewer, (data ?? []) as JobRow[])` with `(data ?? []) as JobRow[]`. Run the page test. Expected: `signed out: no title anywhere` FAILS, because the locked row now renders "Secret Kite". Restore the line and re-run: PASS. If it stayed green, the test is not guarding the title; rewrite it before moving on.

- [ ] **Step 7: Rewrite `loading.tsx`** (the header is real now, rendered by the layout; the skeleton covers only the page):

```tsx
export default function MetricsLoading() {
  return (
    <div aria-busy="true" aria-label="Loading runs" className="mx-auto max-w-7xl animate-pulse space-y-8 p-4 sm:p-6 lg:space-y-10 lg:p-10">
      <div className="flex flex-col gap-3">
        <div className="h-10 w-40 rounded-xl bg-muted md:h-12" />
        <div className="h-5 w-full max-w-[65ch] rounded-lg bg-muted/60" />
      </div>
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="min-h-[132px] rounded-3xl bg-surface p-5 neo-border">
            <div className="h-3 w-20 rounded-full bg-muted" />
            <div className="mt-4 h-8 w-24 rounded-xl bg-muted" />
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-11 w-24 rounded-full bg-muted" />
        ))}
      </div>
      <div className="hidden overflow-hidden rounded-3xl bg-surface neo-border md:block">
        <div className="h-12 border-b border-muted bg-muted/20" />
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-[72px] border-b border-muted/40 last:border-0" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 md:hidden">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-40 rounded-2xl bg-muted/30 neo-border" />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Create `error.tsx`** (same shape as `annotate/error.tsx`, with Retry and a way back):

```tsx
"use client";

import { useEffect } from "react";
import Link from "next/link";
import { ArrowLeft, ArrowsClockwise, WarningCircle } from "@phosphor-icons/react";
import * as Sentry from "@sentry/nextjs";

export default function MetricsError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") Sentry.captureException(error);
    else console.error("Runs list error caught:", error);
  }, [error]);

  return (
    <div role="alert" className="flex min-h-[60dvh] items-center justify-center p-6">
      <div className="w-full max-w-md rounded-[24px] border border-primary/15 bg-surface p-8 text-center shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
        <WarningCircle className="mx-auto mb-4 size-12 text-destructive" weight="duotone" aria-hidden />
        <h1 className="mb-2 font-display text-2xl font-extrabold">We couldn&apos;t load the runs</h1>
        <p className="mb-6 text-sm text-foreground/70">The run list did not load. Try again, or go back to the methodology page.</p>
        <div className="flex flex-col gap-3">
          <button
            type="button"
            onClick={reset}
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-on-primary hover:bg-primary-deep focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <ArrowsClockwise className="size-5" weight="bold" aria-hidden />
            Try again
          </button>
          <Link
            href="/research"
            className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-primary/20 px-5 text-sm font-bold hover:bg-muted/40 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            <ArrowLeft className="size-5" weight="bold" aria-hidden />
            Back to Methodology
          </Link>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 9: Full frontend checks.**

Run: `pnpm lint && pnpm test && pnpm build`
Expected: lint clean, every test file passes, build succeeds. If `supabase.select(...)` typing rejects the `as JobRow[]` cast, change it to `as unknown as JobRow[]` and say so in the commit body.

- [ ] **Step 10: Commit.**

```bash
git add "app/(research)/research/metrics"
git commit -m "feat(metrics): run list with aggregates, filters and locked rows (#107)"
```

---

## Checked in the browser by Plan E

The list's signed-out, annotator and adjudicator views, the filtered-empty state, the error state, and phone width are driven in Plan E Task 5, once the detail page exists for the row links to land on.
