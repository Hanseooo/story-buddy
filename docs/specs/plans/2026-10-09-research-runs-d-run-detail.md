# Research Runs D — Run Detail Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/research/metrics/[jobId]` shows one run as a readable report (header, summary, story, characters, every page attempt, safety, run details, raw JSON), with a clear message for every state the backend can answer with.

**Architecture:** A server component calls Plan A's `GET /research/runs/{job_id}` through one function, `loadRun`, which turns each HTTP answer into a typed result. The page maps that result to a state or to sections. Sections are server components. Only the image viewer, the back link and the copy button are client components. Plan E adds the pipeline graph between the summary and the story.

**Tech Stack:** Next.js 16.2 App Router (`params` is a `Promise`; `error.tsx` gets `reset`; read `frontend/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/error.md`), React 19.2, `@supabase/ssr` server client, Tailwind tokens, phosphor icons, vitest + Testing Library, pnpm.

**Spec:** `docs/specs/research-run-browser.md` §5.1 (response shape), §5.2, §5.4.

**Plan set:** A → B → C → D (this file) → E `2026-10-09-research-runs-e-graph.md`. D needs A's route, B's metrics `layout.tsx` and `LangfuseButton`, C's `StatusPill` and `RUNS_QUERY_KEY`, and the existing `formatJob`. E mounts the graph in D's page. Branch `feat/research-run-browser`, one PR.

## Global Constraints

- The page shows `story.redacted_text` and `scene.text_excerpt` only. It never asks for or shows raw story text (ADR-064 rule 3).
- Every image is a signed URL from the backend, valid 3600 s. No image is fetched by path from the browser.
- Access is the backend's call. The page never decides it; it shows what the backend answered.
- "Models: not recorded for this run" is shown on every run (ADR-064 rule 5). Prompt versions appear only where the state records them.
- Every image's alt text names what it is: `Reference for <name>`, `Page <n>, attempt <m>`.
- Failure reasons and verdict checks get labels from one map in `utils/metrics.ts`. An unknown value shows as is.
- Every control at least 44 px tall; focus ring `focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3`.
- Times in the timing table are UTC and say so.
- Commits carry no `Co-Authored-By` or generated-by trailer.

## Review Focus

1. **A run blocked at the input gate** has no input safety result (router writes are lost, spec §5.1). Expect "Input safety result not recorded", not "Passed" and not a crash. Pinned in Task 6 (`page.test.tsx`).
2. **A run with no checkpoint thread** (`checkpointed: false`). Expect the header and summary from the row and "No recorded steps for this run", with no empty sections under it. Pinned in Task 6.
3. **A storage object that is gone** (`image_url: null`, or a URL that 404s). Expect a placeholder that still carries the alt text. Pinned in Task 3.
4. **A page the judge never answered on** (`vlm_verdict: null`, `passed: false`). Expect "Not checked", not "Failed". Pinned in Task 4.
5. **The backend down or answering 5xx.** Expect `error.tsx` with Retry, not a blank page or a "Run not found" that lies. Pinned in Task 1 (`loadRun` throws on 500) plus the browser check in Plan E.

---

## File map

All under `frontend/app/(research)/research/metrics/[jobId]/` unless the path says otherwise.

| File | Responsibility |
|---|---|
| `types.ts` | `RunDetail` and its parts, mirroring `backend/app/research.py:project_run` |
| `__fixtures__/run.json` | a response produced by Plan A's real `project_run` |
| `loadRun.ts` + `loadRun.test.ts` | session token → fetch → typed result |
| `format.ts` + `format.test.ts` | `totalDurationMs`, `formatDuration` |
| `BackLink.tsx` + `BackLink.test.tsx` | "All runs", restoring the list's filters |
| `ImageViewer.tsx` + `ImageViewer.test.tsx` | thumbnail, broken placeholder, native `<dialog>` viewer |
| `sections/SafetyBadge.tsx` | one badge for passed / flagged / not checked |
| `sections/Story.tsx`, `Characters.tsx`, `Pages.tsx` | §5.2 items 4-5 plus the story text |
| `sections/Safety.tsx`, `RunDetails.tsx`, `RawJson.tsx` | §5.2 items 6-8 |
| `sections/sections.test.tsx` | shipped ribbon, labels, not-checked attempt, copy |
| `SummaryStrip.tsx` | §5.2 item 2 |
| `page.tsx` + `page.test.tsx`, `loading.tsx`, `error.tsx` | the page and its states |
| `frontend/utils/metrics.ts` (modify) | `SCENE_FAILURE_LABELS`, `sceneFailureLabel`, `VERDICT_CHECK_LABELS` |

Commands run from `frontend/` unless they start with `cd`.

The spec's §5.2 list has no story section, but the story text is in the response and a run is hard to read without it. This plan adds a "Story" section after the summary, and Task 6 adds it to the spec's list.

---

### Task 1: Types, the fixture, and `loadRun`

**Files:**
- Create: `[jobId]/types.ts`, `[jobId]/__fixtures__/run.json`, `[jobId]/loadRun.ts`
- Test: `[jobId]/loadRun.test.ts`

**Interfaces:**
- Consumes: `GET /research/runs/{job_id}` (Plan A Task 3): 200 with the `project_run` shape; 401; 403 with `detail` `"not_approved"` or `"researchers_only"`; 404 `"not_found"`; 422 on a malformed id. `createSupabaseServerClient()` from `@/utils/supabase/server` (async).
- Produces:
  - `RunDetail`, `RunJob`, `RunCharacter`, `RunScene`, `RunAttempt`, `RunStep`, `EndedOn`, `RunCost`, `ModerationResult`, `RefVerdict`, `VlmVerdict` from `./types`.
  - `type RunLoad = { kind: "ok"; run: RunDetail } | { kind: "signed_out" } | { kind: "forbidden"; reason: "not_approved" | "researchers_only" } | { kind: "not_found" }`.
  - `loadRun(jobId: string): Promise<RunLoad>`. Throws on any other status or a network error, so `error.tsx` catches it.

- [ ] **Step 1: Write `types.ts`.**

```ts
// Mirrors GET /research/runs/{job_id}: backend/app/research.py:project_run. Change both together.

export type ModerationResult = { passed: boolean; categories: string[] };

export type RefVerdict = {
  differences_observed: string;
  contradictions: string[];
  matches_description: boolean;
  attributes_present: string[];
  text_free: boolean;
};

export type VlmVerdict = {
  differences_observed: string;
  same_character: boolean;
  attributes_present: string[];
  style_match: boolean;
  anatomy_intact: boolean;
  subjects_unique: boolean;
  text_free: boolean;
};

export type RunCharacter = {
  char_id: string;
  name: string;
  description: {
    species: string | null;
    colours: string[];
    body_features: string[];
    clothing: string[];
    notes: string | null;
    is_humanoid: boolean;
  };
  ref_image_url: string | null;
  ref_moderation_status: string | null;
  ref_verdict: RefVerdict | null;
  ref_verdict_prompt_version: number | null;
};

export type RunAttempt = {
  image_url: string | null;
  prompt: string | null;
  passed: boolean;
  failure_reasons: string[];
  vlm_verdict: VlmVerdict | null;
  scene_contradictions: string[] | null;
};

export type RunScene = {
  scene_id: string;
  text_excerpt: string;
  caption: string | null;
  visual_direction: string | null;
  characters_present: string[];
  objects_present: string[];
  moderation_status: string | null;
  regeneration_count: number;
  shipped_attempt: number | null;
  attempts: RunAttempt[];
};

export type RunStep = { node: string; started_at: string; duration_ms: number | null };

export type EndedOn = { node: string; kind: "failed" | "waiting" | "running" };

export type RunCost = {
  image_count: number;
  regen_count: number;
  usd_estimate: number;
  ref_retry_count: number;
  ref_mod_retry_count: number;
};

export type RunJob = {
  id: string;
  title: string | null;
  status: string;
  style_preset_id: string | null;
  created_at: string;
  failure_reason: string | null;
  langfuse_trace_url: string | null;
  usd_estimate: number | null;
  image_count: number | null;
  regen_count: number | null;
  ref_retry_count: number | null;
  scenes_total: number | null;
  scenes_passed: number | null;
  scenes_unchecked: number | null;
  approved: boolean;
};

export type RunDetail = {
  job: RunJob;
  checkpointed: boolean;
  story: { redacted_text: string | null; word_count: number; truncated: boolean } | null;
  steps: RunStep[];
  ended_on: EndedOn | null;
  moderation: { input: ModerationResult | null } | null;
  characters: RunCharacter[];
  scenes: RunScene[];
  cost: RunCost | null;
  // The projected StoryMemory, shown raw. `objects` and `locations` are read by name.
  state:
    | ({ objects?: { obj_id: string; name: string }[]; locations?: { loc_id: string; name: string }[] } & Record<
        string,
        unknown
      >)
    | null;
};
```

- [ ] **Step 2: Capture the fixture from Plan A's real projection.** It runs `project_run` on Plan A's two-page test history, so the JSON is what the backend code produces, not a hand-typed guess:

```bash
mkdir -p "app/(research)/research/metrics/[jobId]/__fixtures__"
cd ../backend && uv run python -c "import tests.conftest, json; from tests.test_research_runs import _history, _job, _memory, _sign; from app.research import project_run; print(json.dumps(project_run(_job(), _history((), _memory()), _sign), indent=2))" > "../frontend/app/(research)/research/metrics/[jobId]/__fixtures__/run.json"
```

Open the file and check by eye: `job.title` is `"The Red Kite"`, two scenes, `scenes[0].shipped_attempt` is `1`, image URLs start with `signed:`, and `SENTINEL` appears nowhere. If `SENTINEL` appears, stop: Plan A's privacy test should have caught it.

- [ ] **Step 3: Write the failing `loadRun` tests.** Create `loadRun.test.ts`:

```ts
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import fixture from "./__fixtures__/run.json";
import { loadRun } from "./loadRun";

const JOB = "3f9a1c2e-0000-4000-8000-000000000001";
const mockSession = vi.hoisted(() => vi.fn());

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: async () => ({ auth: { getSession: mockSession } }),
}));

const answer = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });

describe("loadRun", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    mockSession.mockResolvedValue({ data: { session: { access_token: "tok" } } });
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("signed out never calls the backend", async () => {
    mockSession.mockResolvedValue({ data: { session: null } });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    expect(await loadRun(JOB)).toEqual({ kind: "signed_out" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the bearer token, uncached, and returns the run", async () => {
    const fetchMock = vi.fn().mockResolvedValue(answer(200, fixture));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadRun(JOB);

    expect(fetchMock).toHaveBeenCalledWith(`http://api.test/research/runs/${JOB}`, {
      headers: { Authorization: "Bearer tok" },
      cache: "no-store",
    });
    expect(result.kind === "ok" && result.run.job.title).toBe("The Red Kite");
  });

  it.each([
    [401, { detail: "Not authenticated" }, { kind: "signed_out" }],
    [403, { detail: "not_approved" }, { kind: "forbidden", reason: "not_approved" }],
    [403, { detail: "researchers_only" }, { kind: "forbidden", reason: "researchers_only" }],
    [404, { detail: "not_found" }, { kind: "not_found" }],
    [422, { detail: [] }, { kind: "not_found" }],
  ])("maps %i %j", async (status, body, expected) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(answer(status, body)));
    expect(await loadRun(JOB)).toEqual(expected);
  });

  it("throws on a server error so error.tsx shows Retry", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(answer(500, { detail: "boom" })));
    await expect(loadRun(JOB)).rejects.toThrow("500");
  });
});
```

- [ ] **Step 4: Run them and confirm they fail.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/loadRun.test.ts"`
Expected: FAIL, `Failed to resolve import "./loadRun"`.

- [ ] **Step 5: Implement `loadRun.ts`.**

```ts
import { createSupabaseServerClient } from "@/utils/supabase/server";
import type { RunDetail } from "./types";

export type RunLoad =
  | { kind: "ok"; run: RunDetail }
  | { kind: "signed_out" }
  | { kind: "forbidden"; reason: "not_approved" | "researchers_only" }
  | { kind: "not_found" };

// The backend decides access (ADR-064 rule 2). This only turns its answer into a page state.
export async function loadRun(jobId: string): Promise<RunLoad> {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return { kind: "signed_out" };

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/research/runs/${encodeURIComponent(jobId)}`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: "no-store",
  });
  if (res.ok) return { kind: "ok", run: (await res.json()) as RunDetail };
  if (res.status === 401) return { kind: "signed_out" };
  if (res.status === 403) {
    const body = await res.json().catch(() => null);
    return { kind: "forbidden", reason: body?.detail === "not_approved" ? "not_approved" : "researchers_only" };
  }
  // 422 is a malformed id in the URL. To a reader that is a run that does not exist.
  if (res.status === 404 || res.status === 422) return { kind: "not_found" };
  throw new Error(`Run viewer backend answered ${res.status}`);
}
```

- [ ] **Step 6: Run them and confirm they pass.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/loadRun.test.ts"`
Expected: 8 passed.

- [ ] **Step 7: Break it on purpose.** Delete the `res.status === 422 ||` arm. Run: the `422` case FAILS (it throws instead). Restore: PASS.

- [ ] **Step 8: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]"
git commit -m "feat(run-detail): RunDetail type, captured fixture, loadRun (#104)"
```

---

### Task 2: Labels, durations, and the back link

**Files:**
- Modify: `frontend/utils/metrics.ts`
- Create: `[jobId]/format.ts`, `[jobId]/BackLink.tsx`
- Test: `frontend/utils/metrics.test.ts` (append), `[jobId]/format.test.ts`, `[jobId]/BackLink.test.tsx`

**Interfaces:**
- Consumes: `RUNS_QUERY_KEY` (Plan C Task 3), `RunStep` (Task 1).
- Produces:
  - `SCENE_FAILURE_LABELS: Record<string, string>`, `sceneFailureLabel(reason: string): string`.
  - `VERDICT_CHECK_LABELS: Record<"same_character" | "style_match" | "anatomy_intact" | "subjects_unique" | "text_free", string>`.
  - `totalDurationMs(steps: RunStep[]): number | null` (sum of known durations; `null` when none is known), `formatDuration(ms: number | null): string`.
  - `BackLink()`, default export, client component: a link named "All runs" to `/research/metrics` plus the remembered query.

- [ ] **Step 1: Write the failing tests.** Append to `utils/metrics.test.ts`:

```ts
import { sceneFailureLabel } from "@/utils/metrics";

describe("sceneFailureLabel", () => {
  it("labels the closed set and passes unknown values through", () => {
    expect(sceneFailureLabel("wrong_colour")).toBe("Wrong colour");
    expect(sceneFailureLabel("character_absent")).toBe("Character missing");
    expect(sceneFailureLabel("new_reason")).toBe("new_reason");
  });
});
```

Create `[jobId]/format.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { formatDuration, totalDurationMs } from "./format";

describe("durations", () => {
  it("sums known durations and skips the failing step's null", () => {
    expect(
      totalDurationMs([
        { node: "a", started_at: "", duration_ms: 1500 },
        { node: "b", started_at: "", duration_ms: 2500 },
        { node: "c", started_at: "", duration_ms: null },
      ])
    ).toBe(4000);
    expect(totalDurationMs([{ node: "a", started_at: "", duration_ms: null }])).toBeNull();
  });

  it("reads as seconds, minutes, or hours", () => {
    expect(formatDuration(1500)).toBe("1.5 s");
    expect(formatDuration(125_000)).toBe("2 min 5 s");
    expect(formatDuration(7_380_000)).toBe("2 h 3 min");
    expect(formatDuration(null)).toBe("—");
  });
});
```

Create `[jobId]/BackLink.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RUNS_QUERY_KEY } from "@/utils/metrics";
import BackLink from "./BackLink";

afterEach(() => sessionStorage.clear());

describe("BackLink", () => {
  it("returns to the list with the filters it had", () => {
    sessionStorage.setItem(RUNS_QUERY_KEY, "status=failed&style=cel");
    render(<BackLink />);
    expect(screen.getByRole("link", { name: "All runs" })).toHaveAttribute(
      "href",
      "/research/metrics?status=failed&style=cel"
    );
  });

  it("falls back to the plain list", () => {
    render(<BackLink />);
    expect(screen.getByRole("link", { name: "All runs" })).toHaveAttribute("href", "/research/metrics");
  });
});
```

- [ ] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run utils/metrics.test.ts "app/(research)/research/metrics/[jobId]/format.test.ts" "app/(research)/research/metrics/[jobId]/BackLink.test.tsx"`
Expected: FAIL, `sceneFailureLabel` not exported; `./format` and `./BackLink` do not resolve.

- [ ] **Step 3: Implement.** Append to `utils/metrics.ts`, after `failureLabel`:

```ts
// FailureReason, backend/contracts/story_memory.py. Unknown values pass through as-is.
export const SCENE_FAILURE_LABELS: Record<string, string> = {
  wrong_colour: "Wrong colour",
  wrong_species: "Wrong species",
  wrong_body_feature: "Wrong body feature",
  wrong_clothing: "Wrong clothing",
  wrong_style: "Wrong style",
  different_face: "Different face",
  character_absent: "Character missing",
};

export function sceneFailureLabel(reason: string): string {
  return SCENE_FAILURE_LABELS[reason] ?? reason;
}

// The judge's yes/no checks on a page (VlmVerdict). Shown when one is false.
export const VERDICT_CHECK_LABELS = {
  same_character: "Same character",
  style_match: "Style matches",
  anatomy_intact: "Anatomy intact",
  subjects_unique: "No duplicate characters",
  text_free: "No lettering",
} as const;
```

Create `[jobId]/format.ts`:

```ts
import type { RunStep } from "./types";

export function totalDurationMs(steps: RunStep[]): number | null {
  const known = steps.flatMap((s) => (s.duration_ms == null ? [] : [s.duration_ms]));
  return known.length > 0 ? known.reduce((sum, ms) => sum + ms, 0) : null;
}

export function formatDuration(ms: number | null): string {
  if (ms == null) return "—";
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)} s`;
  const seconds = Math.round(ms / 1000);
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ${seconds % 60} s`;
  return `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min`;
}
```

Create `[jobId]/BackLink.tsx`. It reads storage through `useSyncExternalStore`, so the server renders the plain link and the client swaps in the remembered query without a set-state-in-effect:

```tsx
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
    return null; // private windows can refuse storage
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
```

- [ ] **Step 4: Run them and confirm they pass.**

Run: the Step 2 command.
Expected: all PASS.

- [ ] **Step 5: Commit.**

```bash
git add utils/metrics.ts utils/metrics.test.ts "app/(research)/research/metrics/[jobId]"
git commit -m "feat(run-detail): failure labels, durations, back link with filters"
```

---

### Task 3: `ImageViewer`

**Files:**
- Create: `[jobId]/ImageViewer.tsx`
- Test: `[jobId]/ImageViewer.test.tsx`

**Interfaces:**
- Produces: `ImageViewer({ src, alt, className }: { src: string | null; alt: string; className?: string })`, default export, client component. With a `src`: a button named `Enlarge <alt>` that opens a native modal `<dialog>` (Escape, backdrop click and a "Close image" button close it; the browser returns focus to the button). Without one, or after the image fails to load: a `role="img"` placeholder named `alt` reading "Image unavailable".

- [ ] **Step 1: Write the failing test.**

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import ImageViewer from "./ImageViewer";

beforeAll(() => {
  // jsdom has <dialog> but not its modal methods. These do to `open` what the browser does.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

describe("ImageViewer", () => {
  it("opens the image large and closes it", () => {
    render(<ImageViewer src="https://img.test/a.webp" alt="Page 1, attempt 2" />);

    fireEvent.click(screen.getByRole("button", { name: "Enlarge Page 1, attempt 2" }));
    const dialog = screen.getByRole("dialog", { name: "Page 1, attempt 2" });
    expect(dialog).toHaveAttribute("open");

    fireEvent.click(screen.getByRole("button", { name: "Close image" }));
    expect(dialog).not.toHaveAttribute("open");
  });

  it("shows a named placeholder when there is no image or it fails to load", () => {
    const { unmount } = render(<ImageViewer src={null} alt="Reference for Mia" />);
    expect(screen.getByRole("img", { name: "Reference for Mia" })).toHaveTextContent("Image unavailable");
    unmount();

    render(<ImageViewer src="https://img.test/gone.webp" alt="Page 2, attempt 1" />);
    fireEvent.error(screen.getAllByAltText("Page 2, attempt 1")[0]);
    expect(screen.getByRole("img", { name: "Page 2, attempt 1" })).toHaveTextContent("Image unavailable");
    expect(screen.queryByRole("button", { name: /Enlarge/ })).toBeNull();
  });
});
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/ImageViewer.test.tsx"`
Expected: FAIL, `Failed to resolve import "./ImageViewer"`.

- [ ] **Step 3: Implement.**

```tsx
"use client";

import { useRef, useState } from "react";
import { ImageBroken, X } from "@phosphor-icons/react";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

export default function ImageViewer({ src, alt, className = "" }: { src: string | null; alt: string; className?: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [broken, setBroken] = useState(false);

  if (!src || broken) {
    return (
      <div
        role="img"
        aria-label={alt}
        className={`flex flex-col items-center justify-center gap-1 rounded-xl bg-muted/40 text-foreground/50 ${className}`}
      >
        <ImageBroken weight="duotone" className="size-8" aria-hidden />
        <span className="px-2 text-center text-xs font-medium">Image unavailable</span>
      </div>
    );
  }

  return (
    <>
      <button
        type="button"
        aria-label={`Enlarge ${alt}`}
        onClick={() => ref.current?.showModal()}
        className={`block overflow-hidden rounded-xl bg-muted/30 ${FOCUS} ${className}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt={alt} onError={() => setBroken(true)} className="size-full object-cover" />
      </button>
      <dialog
        ref={ref}
        aria-label={alt}
        onClick={(e) => {
          if (e.target === ref.current) ref.current?.close();
        }}
        className="m-auto max-h-[92dvh] max-w-[92vw] rounded-2xl bg-surface p-0 backdrop:bg-foreground/60 backdrop:backdrop-blur-sm"
      >
        <div className="relative">
          <button
            type="button"
            aria-label="Close image"
            onClick={() => ref.current?.close()}
            className={`absolute right-2 top-2 inline-flex size-11 items-center justify-center rounded-full bg-surface/90 neo-border ${FOCUS}`}
          >
            <X weight="bold" className="size-5" aria-hidden />
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={src} alt={alt} className="block max-h-[90dvh] w-auto max-w-full" />
        </div>
      </dialog>
    </>
  );
}
```

- [ ] **Step 4: Run it and confirm it passes.**

Run: the Step 2 command.
Expected: 2 passed.

- [ ] **Step 5: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]/ImageViewer.tsx" "app/(research)/research/metrics/[jobId]/ImageViewer.test.tsx"
git commit -m "feat(run-detail): single-image viewer with a broken-image placeholder"
```

---

### Task 4: Story, Characters and Pages sections

**Files:**
- Create: `[jobId]/sections/SafetyBadge.tsx`, `sections/Story.tsx`, `sections/Characters.tsx`, `sections/Pages.tsx`
- Test: `[jobId]/sections/sections.test.tsx`

**Interfaces:**
- Consumes: `RunDetail` parts (Task 1), `ImageViewer` (Task 3), `sceneFailureLabel`, `VERDICT_CHECK_LABELS` (Task 2).
- Produces (all default exports, server-safe):
  - `SafetyBadge({ status, label }: { status: string | null; label: string })`: "`label` passed" / "`label` flagged" or "failed" / "`label` not checked".
  - `Story({ story }: { story: RunDetail["story"] })`, section id `story`.
  - `Characters({ characters }: { characters: RunCharacter[] })`, section id `characters`.
  - `Pages({ scenes, characters, objects }: { scenes: RunScene[]; characters: RunCharacter[]; objects: { obj_id: string; name: string }[] })`, section id `pages`.
  - Section ids `story`, `characters`, `pages`, `safety`, `details`, `raw` are the anchors Plan E's node panel links to.

- [ ] **Step 1: Write the failing tests.** Create `sections/sections.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import fixture from "../__fixtures__/run.json";
import type { RunDetail } from "../types";
import Pages from "./Pages";

const RUN = fixture as unknown as RunDetail;

describe("Pages", () => {
  it("marks the shipped attempt and labels the judge's reasons", () => {
    render(<Pages scenes={RUN.scenes} characters={RUN.characters} objects={[]} />);

    const page1 = screen.getByRole("article", { name: "Page 1" });
    const attempts = within(page1).getAllByRole("listitem", { name: /^Attempt \d$/ });
    expect(attempts).toHaveLength(2);
    expect(within(attempts[0]).queryByText("Shipped")).toBeNull();
    expect(within(attempts[0]).getByText("Failed")).toBeInTheDocument();
    expect(within(attempts[0]).getByText("Wrong colour")).toBeInTheDocument();
    expect(within(attempts[1]).getByText("Shipped")).toBeInTheDocument();
    expect(within(attempts[1]).getByRole("button", { name: "Enlarge Page 1, attempt 2" })).toBeInTheDocument();
  });

  it("says Not checked when the judge gave no answer", () => {
    const scene = { ...RUN.scenes[1], shipped_attempt: null, attempts: [{ ...RUN.scenes[1].attempts[0], passed: false, vlm_verdict: null }] };
    render(<Pages scenes={[scene]} characters={RUN.characters} objects={[]} />);

    expect(screen.getByText("Not checked")).toBeInTheDocument();
    expect(screen.queryByText("Failed")).toBeNull();
  });
});
```

- [ ] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/sections"`
Expected: FAIL, `Failed to resolve import "./Pages"`.

- [ ] **Step 3: Write `SafetyBadge.tsx`.**

```tsx
import { Hourglass, ShieldCheck, ShieldWarning } from "@phosphor-icons/react/dist/ssr";

export default function SafetyBadge({ status, label }: { status: string | null; label: string }) {
  if (status === "passed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2.5 py-1 text-xs font-bold text-success">
        <ShieldCheck weight="fill" className="size-4" aria-hidden />
        {label} passed
      </span>
    );
  }
  if (status == null) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-bold text-foreground/70">
        <Hourglass weight="bold" className="size-4" aria-hidden />
        {label} not checked
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-destructive/15 px-2.5 py-1 text-xs font-bold text-destructive">
      <ShieldWarning weight="fill" className="size-4" aria-hidden />
      {label} {status}
    </span>
  );
}
```

- [ ] **Step 4: Write `Story.tsx`.**

```tsx
import type { RunDetail } from "../types";

export default function Story({ story }: { story: RunDetail["story"] }) {
  return (
    <section id="story" aria-labelledby="story-heading" className="scroll-mt-6 space-y-3">
      <h2 id="story-heading" className="font-display text-2xl font-bold">Story</h2>
      {story?.redacted_text ? (
        <div className="rounded-3xl bg-surface p-5 neo-border neo-shadow-sm">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-foreground/50">
            Redacted · {story.word_count} words{story.truncated ? " · cut to the word limit" : ""}
          </p>
          <p className="max-w-[70ch] whitespace-pre-line text-base leading-relaxed">{story.redacted_text}</p>
        </div>
      ) : (
        <p className="text-sm text-foreground/60">No story text recorded for this run.</p>
      )}
    </section>
  );
}
```

- [ ] **Step 5: Write `Characters.tsx`.**

```tsx
import ImageViewer from "../ImageViewer";
import type { RunCharacter } from "../types";
import SafetyBadge from "./SafetyBadge";

function Chips({ label, values }: { label: string; values: string[] }) {
  if (values.length === 0) return null;
  return (
    <div>
      <dt className="text-[11px] font-bold uppercase tracking-wider text-foreground/50">{label}</dt>
      <dd className="mt-1 flex flex-wrap gap-1.5">
        {values.map((v) => (
          <span key={v} className="rounded-md bg-muted/50 px-2 py-0.5 text-xs font-medium">{v}</span>
        ))}
      </dd>
    </div>
  );
}

export default function Characters({ characters }: { characters: RunCharacter[] }) {
  return (
    <section id="characters" aria-labelledby="characters-heading" className="scroll-mt-6 space-y-3">
      <h2 id="characters-heading" className="font-display text-2xl font-bold">Characters</h2>
      {characters.length === 0 ? (
        <p className="text-sm text-foreground/60">No characters were recorded.</p>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {characters.map((c) => (
            <li key={c.char_id} className="flex flex-col gap-4 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:flex-row">
              <ImageViewer src={c.ref_image_url} alt={`Reference for ${c.name}`} className="aspect-square w-full sm:w-40 sm:shrink-0" />
              <div className="flex min-w-0 flex-col gap-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-display text-xl font-bold">{c.name}</h3>
                  <SafetyBadge status={c.ref_moderation_status} label="Reference safety" />
                </div>
                <dl className="space-y-2">
                  <Chips label="Species" values={c.description.species ? [c.description.species] : []} />
                  <Chips label="Colours" values={c.description.colours} />
                  <Chips label="Body" values={c.description.body_features} />
                  <Chips label="Clothing" values={c.description.clothing} />
                </dl>
                {c.ref_verdict ? (
                  <div className="text-sm">
                    <p className={`font-bold ${c.ref_verdict.matches_description ? "text-success" : "text-destructive"}`}>
                      {c.ref_verdict.matches_description ? "Judge: matches the description" : "Judge: does not match the description"}
                    </p>
                    {c.ref_verdict.contradictions.length > 0 && (
                      <ul className="mt-1 list-disc space-y-0.5 pl-5 text-foreground/80">
                        {c.ref_verdict.contradictions.map((x) => <li key={x}>{x}</li>)}
                      </ul>
                    )}
                  </div>
                ) : (
                  <p className="text-sm text-foreground/60">The reference was not judged.</p>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
```

- [ ] **Step 6: Write `Pages.tsx`.**

```tsx
import { sceneFailureLabel, VERDICT_CHECK_LABELS } from "@/utils/metrics";
import ImageViewer from "../ImageViewer";
import type { RunAttempt, RunCharacter, RunScene } from "../types";
import SafetyBadge from "./SafetyBadge";

function Verdict({ attempt }: { attempt: RunAttempt }) {
  if (attempt.passed) {
    return <span className="rounded-full bg-success/15 px-2.5 py-1 text-xs font-bold text-success">Passed</span>;
  }
  // A failure reason means the judge answered, even when the verdict object was not kept.
  if (attempt.vlm_verdict == null && attempt.failure_reasons.length === 0) {
    return <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-bold text-foreground/70">Not checked</span>;
  }
  return <span className="rounded-full bg-destructive/15 px-2.5 py-1 text-xs font-bold text-destructive">Failed</span>;
}

function AttemptCard({ attempt, page, index, shipped }: { attempt: RunAttempt; page: number; index: number; shipped: boolean }) {
  const failedChecks = attempt.vlm_verdict
    ? (Object.keys(VERDICT_CHECK_LABELS) as (keyof typeof VERDICT_CHECK_LABELS)[]).filter((k) => attempt.vlm_verdict?.[k] === false)
    : [];
  return (
    <li
      aria-label={`Attempt ${index + 1}`}
      className={`relative flex flex-col gap-3 rounded-2xl bg-background p-3 neo-border ${shipped ? "ring-3 ring-success" : ""}`}
    >
      {shipped && (
        <span className="absolute left-3 top-3 z-10 rounded-full bg-success px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-on-success">
          Shipped
        </span>
      )}
      <ImageViewer src={attempt.image_url} alt={`Page ${page}, attempt ${index + 1}`} className="aspect-square w-full" />
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm font-bold">Attempt {index + 1}</span>
        <Verdict attempt={attempt} />
      </div>
      {(attempt.failure_reasons.length > 0 || failedChecks.length > 0) && (
        <ul aria-label="What the judge flagged" className="flex flex-wrap gap-1.5">
          {attempt.failure_reasons.map((r) => (
            <li key={r} className="rounded-md bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive">{sceneFailureLabel(r)}</li>
          ))}
          {failedChecks.map((k) => (
            <li key={k} className="rounded-md bg-warning/20 px-2 py-0.5 text-xs font-medium">Not: {VERDICT_CHECK_LABELS[k]}</li>
          ))}
        </ul>
      )}
      {attempt.scene_contradictions && attempt.scene_contradictions.length > 0 && (
        <div className="text-xs">
          <p className="font-bold text-foreground/70">Contradicts the page</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-4">
            {attempt.scene_contradictions.map((x) => <li key={x}>{x}</li>)}
          </ul>
        </div>
      )}
      {attempt.vlm_verdict?.differences_observed && (
        <p className="text-xs text-foreground/70"><span className="font-bold">Judge notes:</span> {attempt.vlm_verdict.differences_observed}</p>
      )}
      {attempt.prompt && (
        <details className="text-xs">
          <summary className="inline-flex min-h-11 cursor-pointer items-center font-bold text-primary">Prompt</summary>
          <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded-lg bg-muted/30 p-2 font-mono">{attempt.prompt}</pre>
        </details>
      )}
    </li>
  );
}

export default function Pages({
  scenes,
  characters,
  objects,
}: {
  scenes: RunScene[];
  characters: RunCharacter[];
  objects: { obj_id: string; name: string }[];
}) {
  const charName = new Map(characters.map((c) => [c.char_id, c.name]));
  const objName = new Map(objects.map((o) => [o.obj_id, o.name]));
  return (
    <section id="pages" aria-labelledby="pages-heading" className="scroll-mt-6 space-y-4">
      <h2 id="pages-heading" className="font-display text-2xl font-bold">Pages</h2>
      {scenes.length === 0 && <p className="text-sm text-foreground/60">No pages were drawn.</p>}
      {scenes.map((scene, i) => (
        <article
          key={scene.scene_id}
          aria-labelledby={`page-${i + 1}`}
          className="grid grid-cols-1 gap-5 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]"
        >
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 id={`page-${i + 1}`} className="font-display text-xl font-bold">Page {i + 1}</h3>
              <SafetyBadge status={scene.moderation_status} label="Safety" />
            </div>
            <p className="text-base leading-relaxed">{scene.text_excerpt}</p>
            {scene.visual_direction && (
              <div>
                <h4 className="text-[11px] font-bold uppercase tracking-wider text-foreground/50">Drawing direction</h4>
                <p className="text-sm text-foreground/80">{scene.visual_direction}</p>
              </div>
            )}
            {scene.characters_present.length > 0 && (
              <p className="text-sm"><span className="font-bold">Cast:</span> {scene.characters_present.map((id) => charName.get(id) ?? id).join(", ")}</p>
            )}
            {scene.objects_present.length > 0 && (
              <p className="text-sm"><span className="font-bold">Objects:</span> {scene.objects_present.map((id) => objName.get(id) ?? id).join(", ")}</p>
            )}
            <p className="text-xs text-foreground/60">
              {scene.attempts.length} {scene.attempts.length === 1 ? "attempt" : "attempts"} · {scene.regeneration_count} redraws
            </p>
          </div>
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {scene.attempts.map((a, j) => (
              <AttemptCard key={j} attempt={a} page={i + 1} index={j} shipped={scene.shipped_attempt === j} />
            ))}
          </ul>
        </article>
      ))}
    </section>
  );
}
```

- [ ] **Step 7: Run the tests and confirm they pass.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/sections"`
Expected: 2 passed.

The fixture's first attempt failed with `wrong_colour` but kept no verdict object (Plan A's test history), so it reads "Failed": a failure reason is an answer.

- [ ] **Step 8: Break it on purpose.** In `Verdict`, delete the `Not checked` branch. Run: `says Not checked` FAILS. Restore: PASS.

- [ ] **Step 9: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]/sections"
git commit -m "feat(run-detail): story, characters and pages with every attempt"
```

---

### Task 5: Safety, Run details, Raw JSON, Summary strip

**Files:**
- Create: `[jobId]/sections/Safety.tsx`, `sections/RunDetails.tsx`, `sections/RawJson.tsx`, `[jobId]/SummaryStrip.tsx`
- Test: `[jobId]/sections/sections.test.tsx` (append)

**Interfaces:**
- Consumes: Task 1 types, Task 2 `formatDuration`/`totalDurationMs`, Task 4 `SafetyBadge`, `failureLabel` and `formatJob` from `utils/metrics.ts`.
- Produces (default exports):
  - `Safety({ run }: { run: RunDetail })`, id `safety`. Input gate card reads "Input safety result not recorded" when `run.moderation?.input` is null.
  - `RunDetails({ run }: { run: RunDetail })`, id `details`.
  - `RawJson({ state }: { state: RunDetail["state"] })`, client, id `raw`. Copy writes the pretty JSON to the clipboard and says "Copied" for 2 s.
  - `SummaryStrip({ run }: { run: RunDetail })`.

- [ ] **Step 1: Write the failing test.** Append to `sections.test.tsx`:

```tsx
import { fireEvent } from "@testing-library/react";
import { vi } from "vitest";
import RawJson from "./RawJson";

describe("RawJson", () => {
  it("copies the pretty-printed state", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    const { container } = render(<RawJson state={RUN.state} />);
    container.querySelector("details")!.open = true; // what clicking the summary does

    fireEvent.click(screen.getByRole("button", { name: "Copy JSON" }));

    expect(writeText).toHaveBeenCalledWith(JSON.stringify(RUN.state, null, 2));
    expect(await screen.findByText("Copied")).toBeInTheDocument();
  });
});
```

(Merge the imports with the file's existing ones.)

- [ ] **Step 2: Run it and confirm it fails.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/sections"`
Expected: FAIL, `Failed to resolve import "./RawJson"`.

- [ ] **Step 3: Write `RawJson.tsx`.**

```tsx
"use client";

import { useState } from "react";
import { Check, Copy } from "@phosphor-icons/react";
import type { RunDetail } from "../types";

export default function RawJson({ state }: { state: RunDetail["state"] }) {
  const [copied, setCopied] = useState(false);
  const text = JSON.stringify(state, null, 2);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard refused (permissions, insecure origin). The text below is still selectable.
    }
  }

  return (
    <section id="raw" aria-labelledby="raw-heading" className="scroll-mt-6">
      <details className="rounded-3xl bg-surface neo-border neo-shadow-sm">
        <summary className="flex min-h-14 cursor-pointer items-center px-5 font-display text-lg font-bold">
          <h2 id="raw-heading">Raw state (JSON)</h2>
        </summary>
        <div className="space-y-3 border-t border-muted px-5 pb-5 pt-3">
          <p className="text-xs text-foreground/60">The checkpointed StoryMemory, with the raw story text and account ids removed.</p>
          <button
            type="button"
            aria-label="Copy JSON"
            onClick={copy}
            className="inline-flex min-h-11 items-center gap-2 rounded-xl bg-primary px-4 text-sm font-bold text-on-primary hover:bg-primary-deep focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            {copied ? <Check weight="bold" className="size-4" aria-hidden /> : <Copy weight="bold" className="size-4" aria-hidden />}
            <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
          </button>
          <pre className="max-h-[60dvh] overflow-auto rounded-xl bg-muted/30 p-3 font-mono text-xs">{text}</pre>
        </div>
      </details>
    </section>
  );
}
```

- [ ] **Step 4: Write `Safety.tsx`.**

```tsx
import type { ReactNode } from "react";
import type { RunDetail } from "../types";
import SafetyBadge from "./SafetyBadge";

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-widest text-foreground/50">{title}</h3>
      {children}
    </div>
  );
}

export default function Safety({ run }: { run: RunDetail }) {
  const input = run.moderation?.input ?? null;
  const refsPassed = run.characters.filter((c) => c.ref_moderation_status === "passed").length;
  const pagesPassed = run.scenes.filter((s) => s.moderation_status === "passed").length;
  const pagesFailed = run.scenes.flatMap((s, i) => (s.moderation_status === "failed" ? [i + 1] : []));
  return (
    <section id="safety" aria-labelledby="safety-heading" className="scroll-mt-6 space-y-3">
      <h2 id="safety-heading" className="font-display text-2xl font-bold">Safety checks</h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <Card title="Input gate">
          {input == null ? (
            <p className="text-sm font-medium text-foreground/70">Input safety result not recorded</p>
          ) : (
            <>
              <SafetyBadge status={input.passed ? "passed" : "flagged"} label="Story" />
              {input.categories.length > 0 && <p className="text-xs text-foreground/70">{input.categories.join(", ")}</p>}
            </>
          )}
        </Card>
        <Card title="Reference checks">
          <p className="text-sm font-medium">{refsPassed} of {run.characters.length} references passed</p>
          {run.cost && run.cost.ref_mod_retry_count > 0 && (
            <p className="text-xs text-foreground/70">{run.cost.ref_mod_retry_count} safety redraws</p>
          )}
        </Card>
        <Card title="Page checks">
          <p className="text-sm font-medium">{pagesPassed} of {run.scenes.length} pages passed</p>
          {pagesFailed.length > 0 && (
            <p className="text-xs font-medium text-destructive">Flagged: page {pagesFailed.join(", ")}</p>
          )}
        </Card>
      </div>
    </section>
  );
}
```

- [ ] **Step 5: Write `RunDetails.tsx`.**

```tsx
import { formatDuration } from "../format";
import type { RunDetail } from "../types";

const TIME = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC" });

export default function RunDetails({ run }: { run: RunDetail }) {
  const versions = [...new Set(run.characters.flatMap((c) => (c.ref_verdict_prompt_version == null ? [] : [c.ref_verdict_prompt_version])))];
  return (
    <section id="details" aria-labelledby="details-heading" className="scroll-mt-6 space-y-3">
      <h2 id="details-heading" className="font-display text-2xl font-bold">Run details</h2>
      <dl className="grid grid-cols-1 gap-3 rounded-2xl bg-surface p-4 text-sm neo-border sm:grid-cols-2">
        <div>
          <dt className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Prompt versions</dt>
          <dd>{versions.length > 0 ? `Reference judge prompt v${versions.join(", v")}` : "None recorded for this run"}</dd>
        </div>
        <div>
          <dt className="text-xs font-semibold uppercase tracking-widest text-foreground/50">Models</dt>
          <dd>Not recorded for this run</dd>
        </div>
      </dl>
      {run.steps.length > 0 && (
        <div className="overflow-x-auto rounded-2xl bg-surface neo-border">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">Every step the run took, in order</caption>
            <thead className="border-b border-muted bg-muted/20 text-xs font-semibold uppercase tracking-wider text-foreground/50">
              <tr>
                <th scope="col" className="px-4 py-3">#</th>
                <th scope="col" className="px-4 py-3">Step</th>
                <th scope="col" className="px-4 py-3">Started (UTC)</th>
                <th scope="col" className="px-4 py-3">Took</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-muted/40 font-mono text-xs">
              {run.steps.map((s, i) => (
                <tr key={i}>
                  <td className="px-4 py-2">{i + 1}</td>
                  <th scope="row" className="px-4 py-2 font-medium">{s.node}</th>
                  <td className="px-4 py-2">{TIME.format(new Date(s.started_at))}</td>
                  <td className="px-4 py-2">{formatDuration(s.duration_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 6: Write `SummaryStrip.tsx`.**

```tsx
import { failureLabel, formatJob } from "@/utils/metrics";
import { formatDuration, totalDurationMs } from "./format";
import type { RunDetail } from "./types";

function Item({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-2xl bg-surface p-4 neo-border neo-shadow-sm">
      <dt className="text-xs font-semibold uppercase tracking-widest text-foreground/50">{label}</dt>
      <dd className="font-display text-2xl font-bold">{value}</dd>
      {note && <dd className="text-xs text-foreground/50">{note}</dd>}
    </div>
  );
}

export default function SummaryStrip({ run }: { run: RunDetail }) {
  const { job } = run;
  const { scenesDisplay, costDisplay } = formatJob(job);
  return (
    <dl aria-label="Summary" className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <Item label="Pages passed" value={scenesDisplay} />
      <Item label="Redraws" value={String(job.regen_count ?? "—")} />
      <Item label="Reference retries" value={String(job.ref_retry_count ?? "—")} />
      <Item label="Cost" value={costDisplay} />
      <Item label="Total time" value={formatDuration(totalDurationMs(run.steps))} note="Includes time waiting for the child" />
      {job.status === "failed" && <Item label="Failure" value={job.failure_reason ? failureLabel(job.failure_reason) : "No reason recorded"} />}
    </dl>
  );
}
```

- [ ] **Step 7: Run the tests and confirm they pass.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/sections"`
Expected: 3 passed.

- [ ] **Step 8: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]"
git commit -m "feat(run-detail): safety, run details, raw JSON and summary"
```

---

### Task 6: The page and its states

**Files:**
- Create: `[jobId]/page.tsx`, `[jobId]/loading.tsx`, `[jobId]/error.tsx`
- Test: `[jobId]/page.test.tsx`
- Modify: `docs/specs/research-run-browser.md` §5.2 (add the Story item)

**Interfaces:**
- Consumes: everything above; `StatusPill` (`../StatusPill`, Plan C Task 6); `LangfuseButton` (Plan B Task 5).
- Produces: `RunPage({ params }: { params: Promise<{ jobId: string }> })`. Signed out → `redirect("/login?next=" + encodeURIComponent("/research/metrics/<jobId>"))`. Plan E inserts `<PipelineGraph steps={run.steps} endedOn={run.ended_on} summaries={summarizeNodes(run)} />` as the first child of the checkpointed branch, right after `<SummaryStrip run={run} />`.

- [ ] **Step 1: Write the failing tests.** Create `[jobId]/page.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import fixture from "./__fixtures__/run.json";
import type { RunDetail } from "./types";
import RunPage from "./page";

const RUN = fixture as unknown as RunDetail;
const JOB = RUN.job.id;
const mockLoad = vi.hoisted(() => vi.fn());
const mockRedirect = vi.hoisted(() =>
  vi.fn(() => {
    throw new Error("NEXT_REDIRECT");
  })
);

vi.mock("./loadRun", () => ({ loadRun: mockLoad }));
vi.mock("next/navigation", () => ({ redirect: mockRedirect }));

const renderPage = async () => render(await RunPage({ params: Promise.resolve({ jobId: JOB }) }));

describe("RunPage states", () => {
  beforeEach(() => mockRedirect.mockClear());

  it("sends a signed-out reader to log in and back", async () => {
    mockLoad.mockResolvedValue({ kind: "signed_out" });
    await expect(renderPage()).rejects.toThrow("NEXT_REDIRECT");
    expect(mockRedirect).toHaveBeenCalledWith(`/login?next=${encodeURIComponent(`/research/metrics/${JOB}`)}`);
  });

  it.each([
    [{ kind: "not_found" }, "Run not found"],
    [{ kind: "forbidden", reason: "not_approved" }, "Not approved yet"],
    [{ kind: "forbidden", reason: "researchers_only" }, "Researchers only"],
  ])("%j shows %s with a way back", async (result, heading) => {
    mockLoad.mockResolvedValue(result);
    await renderPage();
    expect(screen.getByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All runs" })).toBeInTheDocument();
  });

  it("a run with no checkpoint shows the row and says so", async () => {
    mockLoad.mockResolvedValue({
      kind: "ok",
      run: { ...RUN, checkpointed: false, steps: [], story: null, characters: [], scenes: [], cost: null, state: null, moderation: null },
    });
    await renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "The Red Kite" })).toBeInTheDocument();
    expect(screen.getByText("No recorded steps for this run")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pages" })).toBeNull();
  });

  it("a run blocked at the input gate says its safety result was not recorded", async () => {
    mockLoad.mockResolvedValue({
      kind: "ok",
      run: {
        ...RUN,
        job: { ...RUN.job, status: "failed", failure_reason: "child_text" },
        moderation: { input: null },
        ended_on: { node: "input_gate", kind: "failed" },
      },
    });
    await renderPage();
    expect(screen.getByText("Input safety result not recorded")).toBeInTheDocument();
    expect(screen.getByText("Content blocked")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run them and confirm they fail.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]/page.test.tsx"`
Expected: FAIL, `Failed to resolve import "./page"`.

- [ ] **Step 3: Write `page.tsx`.**

```tsx
import { redirect } from "next/navigation";
import LangfuseButton from "@/components/LangfuseButton";
import { formatJob } from "@/utils/metrics";
import StatusPill from "../StatusPill";
import BackLink from "./BackLink";
import { loadRun } from "./loadRun";
import Characters from "./sections/Characters";
import Pages from "./sections/Pages";
import RawJson from "./sections/RawJson";
import RunDetails from "./sections/RunDetails";
import Safety from "./sections/Safety";
import Story from "./sections/Story";
import SummaryStrip from "./SummaryStrip";

const MESSAGES = {
  not_found: { title: "Run not found", body: "There is no run with this id. It may have been typed or copied wrong." },
  not_approved: {
    title: "Not approved yet",
    body: "Researchers can open a run once a teacher approves its book. Failed and unapproved runs are open to the adjudicator only.",
  },
  researchers_only: { title: "Researchers only", body: "Run pages are for researcher accounts." },
} as const;

function RunMessage({ which }: { which: keyof typeof MESSAGES }) {
  const { title, body } = MESSAGES[which];
  return (
    <main className="mx-auto flex max-w-xl flex-col items-start gap-4 p-6 sm:p-10">
      <BackLink />
      <h1 className="font-display text-3xl font-extrabold">{title}</h1>
      <p className="text-base text-foreground/70">{body}</p>
    </main>
  );
}

const STILL_GOING: Record<string, string> = {
  queued: "This run is waiting to start. Reload to see new steps.",
  running: "This run is still going. The page shows what was recorded so far; reload to see more.",
  awaiting_confirm: "This run is waiting for the child to confirm the characters. The page shows what was recorded so far.",
};

export default async function RunPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = await params;
  const result = await loadRun(jobId);
  if (result.kind === "signed_out") redirect(`/login?next=${encodeURIComponent(`/research/metrics/${jobId}`)}`);
  if (result.kind === "not_found") return <RunMessage which="not_found" />;
  if (result.kind === "forbidden") return <RunMessage which={result.reason} />;

  const { run } = result;
  const { job } = run;
  const { shortId, formattedDate } = formatJob(job);
  const name = job.title ?? `Run ${shortId}`;

  return (
    <main className="mx-auto max-w-7xl space-y-8 p-4 font-sans sm:p-6 lg:space-y-10 lg:p-10">
      <header className="flex flex-col gap-3">
        <BackLink />
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-extrabold tracking-tight md:text-4xl">{name}</h1>
          <StatusPill status={job.status} />
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-foreground/60">
          <span>{job.style_preset_id ?? "No style"}</span>
          <span>{formattedDate}</span>
          <span className="font-mono text-xs">{job.id}</span>
          <LangfuseButton url={job.langfuse_trace_url} />
        </div>
      </header>

      {STILL_GOING[job.status] && (
        <p role="status" className="rounded-2xl bg-warning/15 p-4 text-sm font-medium">{STILL_GOING[job.status]}</p>
      )}

      <SummaryStrip run={run} />

      {run.checkpointed ? (
        <>
          <Story story={run.story} />
          <Characters characters={run.characters} />
          <Pages scenes={run.scenes} characters={run.characters} objects={run.state?.objects ?? []} />
          <Safety run={run} />
          <RunDetails run={run} />
          <RawJson state={run.state} />
        </>
      ) : (
        <div className="rounded-3xl bg-surface p-8 text-center neo-border neo-shadow-sm">
          <p className="font-bold">No recorded steps for this run</p>
          <p className="mt-1 text-sm text-foreground/60">
            The pipeline left no checkpoint for it, so only the totals above are known.
          </p>
        </div>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Run the tests and confirm they pass.**

Run: `pnpm exec vitest run "app/(research)/research/metrics/[jobId]"`
Expected: all PASS.

- [ ] **Step 5: Break it on purpose.** In `page.tsx`, replace `{run.checkpointed ? (` with `{true ? (`. Run: `a run with no checkpoint` FAILS. Restore: PASS.

- [ ] **Step 6: Write `loading.tsx`** (header, graph block, two page blocks; spec §5.4):

```tsx
export default function RunLoading() {
  return (
    <div aria-busy="true" aria-label="Loading run" className="mx-auto max-w-7xl animate-pulse space-y-8 p-4 sm:p-6 lg:p-10">
      <div className="space-y-3">
        <div className="h-11 w-28 rounded-xl bg-muted/60" />
        <div className="h-10 w-72 max-w-full rounded-xl bg-muted" />
        <div className="h-4 w-56 rounded-lg bg-muted/60" />
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-24 rounded-2xl bg-surface neo-border" />
        ))}
      </div>
      <div className="h-[420px] rounded-3xl bg-surface neo-border" />
      {[...Array(2)].map((_, i) => (
        <div key={i} className="h-72 rounded-3xl bg-surface neo-border" />
      ))}
    </div>
  );
}
```

- [ ] **Step 7: Write `error.tsx`.**

```tsx
"use client";

import { useEffect } from "react";
import { ArrowsClockwise, WarningCircle } from "@phosphor-icons/react";
import * as Sentry from "@sentry/nextjs";
import BackLink from "./BackLink";

export default function RunError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") Sentry.captureException(error);
    else console.error("Run page error caught:", error);
  }, [error]);

  return (
    <div role="alert" className="flex min-h-[60dvh] items-center justify-center p-6">
      <div className="flex w-full max-w-md flex-col items-center gap-4 rounded-[24px] border border-primary/15 bg-surface p-8 text-center shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
        <WarningCircle className="size-12 text-destructive" weight="duotone" aria-hidden />
        <h1 className="font-display text-2xl font-extrabold">Couldn&apos;t load this run</h1>
        <p className="text-sm text-foreground/70">The run service did not answer. Try again in a moment.</p>
        <button
          type="button"
          onClick={reset}
          className="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-primary px-5 text-sm font-bold text-on-primary hover:bg-primary-deep focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
        >
          <ArrowsClockwise className="size-5" weight="bold" aria-hidden />
          Try again
        </button>
        <BackLink />
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Add the Story item to the spec.** In `docs/specs/research-run-browser.md` §5.2, after item 3 (Pipeline graph), insert "Story. The redacted text, word count, and whether it was cut to the word limit." and renumber items 4-8 to 5-9.

- [ ] **Step 9: Full frontend checks.**

Run: `pnpm lint && pnpm test && pnpm build`
Expected: lint clean, every test file passes, build succeeds.

- [ ] **Step 10: Commit.**

```bash
git add "app/(research)/research/metrics/[jobId]" ../docs/specs/research-run-browser.md
git commit -m "feat(run-detail): run page with not-found, locked, no-checkpoint and in-progress states (#104)"
```

---

## Left to Plan E

The pipeline graph and its node panel, mounting them in this page, the ROUTE_MAP and CHANGELOG entries, and the browser check of the whole PR (list and detail, desktop and phone).
