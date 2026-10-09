# Research Runs B — Research Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every research page one signed-in header (Runs / Annotate / Adjudicate), guard the run detail path, send "sign in" back to the run, and add the warned, flag-gated Langfuse button.

**Architecture:** A pure `ResearchViewer` type, a request-cached server loader `getResearchViewer()`, a `RESEARCH_TABS` list, and a client `ResearchHeader` that takes the viewer as a prop. Layouts load the viewer and render the header; `AnnotationClient` and `AdjudicateClient` are untouched. `LangfuseButton` wraps the existing `ConfirmDialog`.

**Tech Stack:** Next.js 16.2 App Router (read `frontend/node_modules/next/dist/docs/` before writing Next code), React 19.2, Tailwind tokens from `app/globals.css`, `@phosphor-icons/react`, vitest 4 + jsdom + Testing Library, pnpm.

**Spec:** `docs/specs/research-run-browser.md` §2, §3, §6.

**Plan set:** A (backend route built; interface in `docs/specs/research-run-browser.md` §5.1) → B (this file) → C `2026-10-09-research-runs-c-run-list.md` → D `2026-10-09-research-runs-d-run-detail.md` → E `2026-10-09-research-runs-e-graph.md`. C and D import what B produces. Branch `feat/research-run-browser`, one PR.

## Global Constraints

- `AnnotationClient.tsx` and `AdjudicateClient.tsx` are not changed. #111 relies on that.
- The header is not sticky; the annotate and adjudicate task bars below it are (`sticky top-0 z-30`).
- Tabs: **Runs** (everyone), **Annotate** (researcher, not adjudicator), **Adjudicate** (adjudicator). One list, `RESEARCH_TABS` in `(research)/_shared/constants.ts`.
- Active tab carries `aria-current="page"`. Every control is at least 44 px tall (`min-h-11`), with the repo's focus ring `focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3`.
- Log out is a form POST to `/auth/signout`. Signed out shows "Researcher sign in" linking to `/login?next=<current path>`.
- On a 360 px phone, the header fits in one row with no horizontal scroll.
- `NEXT_PUBLIC_SHOW_LANGFUSE_LINKS`: the Langfuse button renders only when it equals `"true"`. Off by default.
- Langfuse dialog copy, verbatim: title "Open the full Langfuse trace?"; description "This trace is the full raw record of the run, including the story text before redaction. Open it only when you need that detail."; buttons "Cancel" (first) and "Open in new tab", which calls `window.open(url, "_blank", "noopener,noreferrer")`.
- Never read `frontend/.env.local`. Commits carry no `Co-Authored-By` or generated-by trailer.

## Review Focus

1. **A researcher who follows "Sign in to view".** Today the login page ignores a researcher's `next` unless it is under `/annotate` or `/adjudicate`, so they land on their queue instead of the run. Expect them on the run. Pinned in Task 1.
2. **The run list stays public.** A guard written as `startsWith("/research/metrics")` would send signed-out readers of the list to login. Expect `/research/metrics` to pass and only paths under `/research/metrics/` to redirect. Pinned in Task 2.
3. **An adjudicator on `/annotate`.** Moving the layout onto `getResearchViewer()` must keep refusing adjudicators. Pinned in Task 4 (`annotate/layout.test.tsx`).
4. **Escape on the Langfuse dialog.** The browser fires `cancel`; the dialog must close and nothing opens. Pinned in Task 5.
5. **A row with no trace URL, or the flag off.** Render nothing, not an empty button. Pinned in Task 5.

---

## File map

| File | Responsibility |
|---|---|
| `frontend/app/login/page.tsx` (modify, the `allowedNext` block near line 55) | researchers may resume `/research/metrics/...` |
| `frontend/app/login/page.test.tsx` (modify) | one test |
| `frontend/middleware.ts` (modify) | guard and matcher |
| `frontend/middleware.test.ts` (modify) | three tests |
| `frontend/app/(research)/_shared/viewer.ts` (create) | `ResearchViewer` type (Plan C adds `canOpenRun` here) |
| `frontend/app/(research)/_shared/getResearchViewer.ts` (create) | server loader, request-cached |
| `frontend/app/(research)/_shared/constants.ts` (modify, append) | `RESEARCH_TABS` |
| `frontend/app/(research)/_shared/components/ResearchHeader.tsx` (create) | the header |
| `frontend/app/(research)/_shared/components/ResearchHeader.test.tsx` (create) | header by viewer |
| `frontend/app/(research)/research/metrics/layout.tsx` (create) | header above the list and detail |
| `frontend/app/(research)/research/metrics/page.tsx` (modify) | drop its own logo/back row |
| `frontend/app/(research)/annotate/layout.tsx`, `adjudicate/layout.tsx` (modify) | use the loader, render the header |
| `frontend/app/(research)/annotate/layout.test.tsx` (create), `adjudicate/layout.test.tsx` (modify) | gates and header |
| `frontend/components/LangfuseButton.tsx` (create), `LangfuseButton.test.tsx` (create) | warned link |
| `frontend/.env.local.example` (modify) | the flag |

All commands run from `frontend/`.

---

### Task 1: Login resumes a run for researchers

**Files:**
- Modify: `frontend/app/login/page.tsx` (the `profile.role === "researcher"` branch of `allowedNext`)
- Test: `frontend/app/login/page.test.tsx`

**Interfaces:**
- Produces: a researcher signing in with `next=/research/metrics` or `next=/research/metrics/<id>` is sent there.

- [ ] **Step 1: Write the failing test.** Add inside the `describe("Teacher Auth Pages", ...)` block, after `"does not let a researcher resume a student next target"`:

```tsx
  it("lets a researcher resume a run detail next target", async () => {
    const run = "/research/metrics/3f9a1c2e-0000-4000-8000-000000000001";
    mockSearchParamsGet.mockImplementation((key: string) => (key === "next" ? run : null));
    mockSignIn.mockResolvedValueOnce({ data: { user: { id: "researcher-1" } }, error: null });
    mockSingle.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: false } });
    render(<Login />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "researcher@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(run);
    });
  });
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `pnpm exec vitest run app/login/page.test.tsx -t "run detail"`
Expected: FAIL, `mockPush` called with `"/annotate"`.

- [ ] **Step 3: Implement.** Replace the researcher arm of `allowedNext`:

```tsx
            : profile.role === "researcher"
              ? isPathUnder(safeNext, "/research/metrics") ||
                (profile.is_adjudicator
                  ? isPathUnder(safeNext, "/adjudicate")
                  : isPathUnder(safeNext, "/annotate"))
              : false;
```

- [ ] **Step 4: Run the file.**

Run: `pnpm exec vitest run app/login/page.test.tsx`
Expected: all PASS, including `"does not let a researcher resume a student next target"`.

- [ ] **Step 5: Commit.**

```bash
git add app/login/page.tsx app/login/page.test.tsx
git commit -m "fix(login): researchers resume /research/metrics after sign in"
```

---

### Task 2: Middleware guards run detail, not the list

**Files:**
- Modify: `frontend/middleware.ts`
- Test: `frontend/middleware.test.ts` (append)

**Interfaces:**
- Produces: `guardRequest("/research/metrics/<id>", null) === "/login?next=/research/metrics/<id>"`; `guardRequest("/research/metrics", null) === null`.

- [ ] **Step 1: Write the failing tests.** Append to `frontend/middleware.test.ts`:

```ts
describe("guardRequest — research run browser", () => {
  it("unauthenticated run detail → /login?next=...", () => {
    expect(guardRequest(`/research/metrics/${UUID_A}`, null)).toBe(
      `/login?next=/research/metrics/${UUID_A}`
    );
  });

  it("the run list stays public", () => {
    expect(guardRequest("/research/metrics", null)).toBeNull();
  });

  it("a signed-in run detail request passes", () => {
    expect(guardRequest(`/research/metrics/${UUID_A}`, UUID_B)).toBeNull();
  });
});
```

- [ ] **Step 2: Run them and confirm the first fails.**

Run: `pnpm exec vitest run middleware.test.ts -t "research run browser"`
Expected: `unauthenticated run detail` FAILS (received `null`); the other two pass. The "stays public" test is the guard against an over-broad fix: Step 5 proves it.

- [ ] **Step 3: Implement.** In `guardRequest`, add the path to the signed-out block:

```ts
  if (
    (pathname.startsWith("/classroom") ||
      pathname === "/settings" ||
      pathname.startsWith("/annotate") ||
      pathname.startsWith("/adjudicate") ||
      pathname.startsWith("/research/metrics/")) &&
    !userId
  )
    return `/login?next=${safe(pathname) ?? ""}`;
```

Append to `config.matcher`, after `"/adjudicate/:path*"`. The list is in the matcher too so middleware refreshes the session cookie that `getResearchViewer()` reads; `guardRequest` lets it through.

```ts
    "/research/metrics",
    "/research/metrics/:path*",
```

- [ ] **Step 4: Run the file.**

Run: `pnpm exec vitest run middleware.test.ts`
Expected: all PASS.

- [ ] **Step 5: Break it on purpose.** Change `"/research/metrics/"` to `"/research/metrics"` in `guardRequest`. Run the file: `the run list stays public` FAILS. Restore and re-run: PASS.

- [ ] **Step 6: Commit.**

```bash
git add middleware.ts middleware.test.ts
git commit -m "feat(middleware): run detail pages need a session; the run list stays public"
```

---

### Task 3: Viewer, tabs and `ResearchHeader`

**Files:**
- Create: `frontend/app/(research)/_shared/viewer.ts`
- Create: `frontend/app/(research)/_shared/getResearchViewer.ts`
- Modify: `frontend/app/(research)/_shared/constants.ts` (append)
- Create: `frontend/app/(research)/_shared/components/ResearchHeader.tsx`
- Test: `frontend/app/(research)/_shared/components/ResearchHeader.test.tsx`

**Interfaces:**
- Produces:
  - `type ResearchViewer = { id: string; role: string | null; isAdjudicator: boolean; displayName: string | null }`; signed out is `null`. In `viewer.ts`, which imports nothing server-side, so client components may import it.
  - `getResearchViewer(): Promise<ResearchViewer | null>` in `getResearchViewer.ts` (server only; wrapped in React `cache()` so a layout and page in one request share one profile read).
  - `RESEARCH_TABS: { label: string; href: string; visibleTo: (viewer: ResearchViewer | null) => boolean }[]`.
  - `ResearchHeader({ viewer }: { viewer: ResearchViewer | null })`, default export, client component.

- [ ] **Step 1: Write the failing test.** Create `ResearchHeader.test.tsx`:

```tsx
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ResearchHeader from "./ResearchHeader";
import type { ResearchViewer } from "../viewer";

vi.mock("next/navigation", () => ({ usePathname: () => "/research/metrics" }));

const annotator: ResearchViewer = { id: "r-1", role: "researcher", isAdjudicator: false, displayName: "Ana" };
const adjudicator: ResearchViewer = { id: "r-2", role: "researcher", isAdjudicator: true, displayName: "Owner" };

function tabNames() {
  const nav = screen.getByRole("navigation", { name: "Research" });
  return within(nav).getAllByRole("link").map((link) => link.textContent);
}

describe("ResearchHeader", () => {
  it("signed out: Runs only, marked current, with a sign-in link back here", () => {
    render(<ResearchHeader viewer={null} />);

    expect(tabNames()).toEqual(["Runs"]);
    expect(screen.getByRole("link", { name: "Runs" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Researcher sign in" })).toHaveAttribute(
      "href",
      "/login?next=/research/metrics"
    );
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
  });

  it("annotator: Runs and Annotate, Annotator chip, Log out", () => {
    render(<ResearchHeader viewer={annotator} />);

    expect(tabNames()).toEqual(["Runs", "Annotate"]);
    expect(screen.getByText("Annotator")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log out" })).toBeInTheDocument();
  });

  it("adjudicator: Runs and Adjudicate, Adjudicator chip", () => {
    render(<ResearchHeader viewer={adjudicator} />);

    expect(tabNames()).toEqual(["Runs", "Adjudicate"]);
    expect(screen.getByText("Adjudicator")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `pnpm exec vitest run "app/(research)/_shared/components/ResearchHeader.test.tsx"`
Expected: FAIL, `Failed to resolve import "./ResearchHeader"`.

- [ ] **Step 3: Implement the type and loader.** Create `viewer.ts`:

```ts
// Who is looking at a research page. `null` means signed out. Pure: safe to import from client code.
export type ResearchViewer = {
  id: string;
  role: string | null;
  isAdjudicator: boolean;
  displayName: string | null;
};
```

Create `getResearchViewer.ts`:

```ts
import { cache } from "react";
import { createSupabaseServerClient } from "@/utils/supabase/server";
import type { ResearchViewer } from "./viewer";

// cache(): the metrics layout and its page both ask in one request; one profile read serves both.
export const getResearchViewer = cache(async (): Promise<ResearchViewer | null> => {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: profile } = await supabase
    .from("profiles")
    .select("role, is_adjudicator, display_name")
    .eq("id", user.id)
    .single();

  return {
    id: user.id,
    role: profile?.role ?? null,
    isAdjudicator: profile?.is_adjudicator === true,
    displayName: profile?.display_name ?? null,
  };
});
```

Append to `constants.ts`:

```ts
import type { ResearchViewer } from "./viewer";

// The research header's tabs. A future page (#106 Dataset, #105 Docs) is one entry here.
export const RESEARCH_TABS: {
  label: string;
  href: string;
  visibleTo: (viewer: ResearchViewer | null) => boolean;
}[] = [
  { label: "Runs", href: "/research/metrics", visibleTo: () => true },
  {
    label: "Annotate",
    href: "/annotate",
    visibleTo: (viewer) => viewer?.role === "researcher" && !viewer.isAdjudicator,
  },
  {
    label: "Adjudicate",
    href: "/adjudicate",
    visibleTo: (viewer) => viewer?.role === "researcher" && viewer.isAdjudicator,
  },
];
```

Move the `import type` line to the top of `constants.ts`.

- [ ] **Step 4: Implement the header.** Create `ResearchHeader.tsx`:

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SignOut } from "@phosphor-icons/react";
import { RESEARCH_TABS } from "../constants";
import type { ResearchViewer } from "../viewer";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// Not sticky: the annotate and adjudicate task bars below it already stick to the top.
export default function ResearchHeader({ viewer }: { viewer: ResearchViewer | null }) {
  const pathname = usePathname() ?? "/research/metrics";
  const tabs = RESEARCH_TABS.filter((tab) => tab.visibleTo(viewer));
  const roleChip =
    viewer?.role === "researcher" ? (viewer.isAdjudicator ? "Adjudicator" : "Annotator") : null;

  return (
    <header className="border-b border-primary/10 bg-background">
      <div className="mx-auto flex max-w-7xl items-center gap-2 px-4 py-2 sm:gap-4 sm:px-6">
        <Link
          href="/research"
          aria-label="StoryBuddy research home"
          className={`flex shrink-0 items-center gap-2 rounded-lg ${FOCUS}`}
        >
          <span className="grid size-8 place-items-center overflow-hidden rounded-[9px_9px_9px_3px] bg-surface shadow-sm">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="" className="h-full w-full scale-[1.35] object-contain" />
          </span>
          <span className="hidden font-display text-lg font-extrabold tracking-tight text-primary lg:block">
            StoryBuddy
          </span>
        </Link>

        <nav aria-label="Research" className="flex min-w-0 flex-1 gap-1">
          {tabs.map((tab) => {
            const active = pathname === tab.href || pathname.startsWith(`${tab.href}/`);
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={active ? "page" : undefined}
                className={`inline-flex min-h-11 items-center rounded-xl px-2.5 text-sm font-bold transition-colors sm:px-3 ${FOCUS} ${
                  active ? "bg-primary text-on-primary" : "text-foreground/70 hover:bg-muted/50"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>

        {viewer ? (
          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
            {viewer.displayName && (
              <span className="hidden max-w-[16ch] truncate text-sm font-medium text-foreground/70 md:block">
                {viewer.displayName}
              </span>
            )}
            {roleChip && (
              <span className="rounded-full bg-admin/10 px-2.5 py-1 text-xs font-bold text-admin">{roleChip}</span>
            )}
            <form action="/auth/signout" method="post">
              <button
                type="submit"
                aria-label="Log out"
                className={`inline-flex min-h-11 min-w-11 items-center justify-center gap-1.5 rounded-xl px-2 text-sm font-bold text-foreground/70 hover:bg-muted/50 ${FOCUS}`}
              >
                <SignOut weight="bold" className="size-4" aria-hidden />
                <span className="hidden sm:inline">Log out</span>
              </button>
            </form>
          </div>
        ) : (
          <Link
            href={`/login?next=${pathname}`}
            className={`inline-flex min-h-11 shrink-0 items-center rounded-xl border border-primary/20 px-3 text-sm font-bold text-primary hover:bg-primary/5 ${FOCUS}`}
          >
            Researcher sign in
          </Link>
        )}
      </div>
    </header>
  );
}
```

- [ ] **Step 5: Run it and confirm it passes.**

Run: `pnpm exec vitest run "app/(research)/_shared/components/ResearchHeader.test.tsx"`
Expected: 3 passed.

- [ ] **Step 6: Break it on purpose.** In `RESEARCH_TABS`, drop `&& !viewer.isAdjudicator` from Annotate. Run the test: `adjudicator: Runs and Adjudicate` FAILS. Restore: PASS.

- [ ] **Step 7: Commit.**

```bash
git add "app/(research)/_shared"
git commit -m "feat(research): shared header with role-aware tabs"
```

---

### Task 4: Layouts render the header

**Files:**
- Create: `frontend/app/(research)/research/metrics/layout.tsx`
- Modify: `frontend/app/(research)/research/metrics/page.tsx` (remove its top logo/back row)
- Modify: `frontend/app/(research)/annotate/layout.tsx`, `frontend/app/(research)/adjudicate/layout.tsx`
- Create: `frontend/app/(research)/annotate/layout.test.tsx`
- Modify: `frontend/app/(research)/adjudicate/layout.test.tsx`

**Interfaces:**
- Consumes: `getResearchViewer`, `ResearchHeader` from Task 3.
- Produces: every page under `/research/metrics`, `/annotate` and `/adjudicate` renders `ResearchHeader` above its content. Gates unchanged: annotate needs `role === "researcher"` and not adjudicator; adjudicate needs `role === "researcher"`; both `throw new Error("Unauthorized")` otherwise.

- [ ] **Step 1: Write the failing tests.** In `adjudicate/layout.test.tsx`, add `usePathname` to the existing `next/navigation` mock:

```tsx
vi.mock("next/navigation", () => ({
  redirect: vi.fn((url: string) => {
    throw new Error(`REDIRECT:${url}`);
  }),
  usePathname: () => "/adjudicate",
}));
```

and in `"renders children for authorized adjudicator ..."`, after the existing `expect`, add:

```tsx
    expect(screen.getByRole("navigation", { name: "Research" })).toBeInTheDocument();
```

Create `annotate/layout.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AnnotateLayout from "./layout";

const mockGetUser = vi.fn();
const mockSingle = vi.fn();

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: vi.fn(() => ({
    auth: { getUser: mockGetUser },
    from: vi.fn(() => ({ select: vi.fn(() => ({ eq: vi.fn(() => ({ single: mockSingle })) })) })),
  })),
}));

vi.mock("next/navigation", () => ({ usePathname: () => "/annotate" }));

describe("AnnotateLayout", () => {
  beforeEach(() => vi.clearAllMocks());

  it("refuses the adjudicator", async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: "r-2" } } });
    mockSingle.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: true } });

    await expect(AnnotateLayout({ children: <div>Queue</div> })).rejects.toThrow("Unauthorized");
  });

  it("renders the research header above an annotator's queue", async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: "r-1" } } });
    mockSingle.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: false, display_name: "Ana" } });

    render(await AnnotateLayout({ children: <div>Queue</div> }));

    expect(screen.getByRole("navigation", { name: "Research" })).toBeInTheDocument();
    expect(screen.getByText("Queue")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run them and confirm the header assertions fail.**

Run: `pnpm exec vitest run "app/(research)/annotate/layout.test.tsx" "app/(research)/adjudicate/layout.test.tsx"`
Expected: the two header assertions FAIL (`Unable to find role="navigation"`); the gate tests pass.

- [ ] **Step 3: Implement the annotate and adjudicate layouts.** Replace `annotate/layout.tsx`:

```tsx
import ResearchHeader from "../_shared/components/ResearchHeader";
import { getResearchViewer } from "../_shared/getResearchViewer";

export default async function AnnotateLayout({ children }: { children: React.ReactNode }) {
  const viewer = await getResearchViewer();

  if (viewer?.role !== "researcher" || viewer.isAdjudicator) {
    throw new Error("Unauthorized");
  }

  return (
    <div className="min-h-[100dvh] bg-background text-foreground flex flex-col selection:bg-primary/20">
      <ResearchHeader viewer={viewer} />
      {children}
    </div>
  );
}
```

Replace `adjudicate/layout.tsx`:

```tsx
import ResearchHeader from "../_shared/components/ResearchHeader";
import { getResearchViewer } from "../_shared/getResearchViewer";

export default async function AdjudicateLayout({ children }: { children: React.ReactNode }) {
  const viewer = await getResearchViewer();

  if (viewer?.role !== "researcher") {
    throw new Error("Unauthorized");
  }

  return (
    <div className="min-h-[100dvh] bg-background text-foreground flex flex-col selection:bg-primary/20">
      <ResearchHeader viewer={viewer} />
      {children}
    </div>
  );
}
```

- [ ] **Step 4: Implement the metrics layout.** Create `research/metrics/layout.tsx`:

```tsx
import ResearchHeader from "../../_shared/components/ResearchHeader";
import { getResearchViewer } from "../../_shared/getResearchViewer";

export default async function MetricsLayout({ children }: { children: React.ReactNode }) {
  const viewer = await getResearchViewer();

  return (
    <div className="min-h-[100dvh] bg-background text-foreground">
      <ResearchHeader viewer={viewer} />
      {children}
    </div>
  );
}
```

In `research/metrics/page.tsx`, delete the `<div className="flex items-center justify-between border-b border-primary/10 pb-4">` block (the "Back to Methodology" link and the logo); the header now holds both. Remove `ArrowLeft` from the icon import. Plan C rewrites the rest of this page.

- [ ] **Step 5: Run the research tests and lint.**

Run: `pnpm exec vitest run "app/(research)" && pnpm lint`
Expected: all PASS, lint clean.

- [ ] **Step 6: Commit.**

```bash
git add "app/(research)"
git commit -m "feat(research): header on metrics, annotate and adjudicate layouts"
```

---

### Task 5: `LangfuseButton` behind its flag

**Files:**
- Create: `frontend/components/LangfuseButton.tsx`
- Test: `frontend/components/LangfuseButton.test.tsx`
- Modify: `frontend/.env.local.example`

**Interfaces:**
- Consumes: `ConfirmDialog` (`components/ConfirmDialog.tsx`: props `open, onConfirm, onCancel, title, description, confirmLabel, confirmClass`).
- Produces: `LangfuseButton({ url, label }: { url: string | null | undefined; label?: string })`, default export, client component. `label` is the accessible name (default `"Open Langfuse trace"`); list rows pass `"Open Langfuse trace for <run name>"`. Renders `null` when the flag is not `"true"` or `url` is empty. Has `relative z-10` so it sits above a row's stretched link (Plan C).

- [ ] **Step 1: Write the failing test.** Create `components/LangfuseButton.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import LangfuseButton from "./LangfuseButton";

const TRACE = "https://cloud.langfuse.com/project/p/traces/abc";

beforeAll(() => {
  // jsdom has <dialog> but not its modal methods. These do to `open` what the browser does.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("LangfuseButton", () => {
  it("renders nothing with the flag off, or with no trace", () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "");
    const off = render(<LangfuseButton url={TRACE} />);
    expect(off.container).toBeEmptyDOMElement();
    off.unmount();

    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "true");
    const noTrace = render(<LangfuseButton url={null} />);
    expect(noTrace.container).toBeEmptyDOMElement();
  });

  it("warns first; Cancel and Escape close it without opening", () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "true");
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    render(<LangfuseButton url={TRACE} />);

    fireEvent.click(screen.getByRole("button", { name: "Open Langfuse trace" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("open");
    expect(dialog).toHaveTextContent("including the story text before redaction");

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(dialog).not.toHaveAttribute("open");

    fireEvent.click(screen.getByRole("button", { name: "Open Langfuse trace" }));
    fireEvent(dialog, new Event("cancel")); // what the browser fires on Escape
    expect(dialog).not.toHaveAttribute("open");
    expect(open).not.toHaveBeenCalled();
  });

  it("Open in new tab opens the trace with no opener", () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "true");
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    render(<LangfuseButton url={TRACE} />);

    fireEvent.click(screen.getByRole("button", { name: "Open Langfuse trace" }));
    fireEvent.click(screen.getByRole("button", { name: "Open in new tab" }));

    expect(open).toHaveBeenCalledWith(TRACE, "_blank", "noopener,noreferrer");
  });
});
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `pnpm exec vitest run components/LangfuseButton.test.tsx`
Expected: FAIL, `Failed to resolve import "./LangfuseButton"`.

- [ ] **Step 3: Implement.** Create `components/LangfuseButton.tsx`:

```tsx
"use client";

import { useState } from "react";
import { ArrowSquareOut } from "@phosphor-icons/react";
import ConfirmDialog from "@/components/ConfirmDialog";

// #103. A trace holds the story before redaction, so the link is off unless the deploy opts in,
// and it asks first. Read inside the component: Next inlines NEXT_PUBLIC_ values at build either way.
export default function LangfuseButton({
  url,
  label = "Open Langfuse trace",
}: {
  url: string | null | undefined;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  if (process.env.NEXT_PUBLIC_SHOW_LANGFUSE_LINKS !== "true" || !url) return null;

  return (
    <>
      <button
        type="button"
        aria-label={label}
        onClick={() => setOpen(true)}
        className="relative z-10 inline-flex min-h-11 items-center gap-1.5 rounded-xl px-3 text-sm font-bold text-primary hover:bg-primary/10 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
      >
        Langfuse
        <ArrowSquareOut weight="bold" className="size-4" aria-hidden />
      </button>
      <ConfirmDialog
        open={open}
        title="Open the full Langfuse trace?"
        description="This trace is the full raw record of the run, including the story text before redaction. Open it only when you need that detail."
        confirmLabel="Open in new tab"
        confirmClass="bg-primary text-on-primary"
        onCancel={() => setOpen(false)}
        onConfirm={() => {
          window.open(url, "_blank", "noopener,noreferrer");
          setOpen(false);
        }}
      />
    </>
  );
}
```

Append to `frontend/.env.local.example`:

```
NEXT_PUBLIC_SHOW_LANGFUSE_LINKS=false
```

- [ ] **Step 4: Run it and confirm it passes.**

Run: `pnpm exec vitest run components/LangfuseButton.test.tsx`
Expected: 3 passed.

- [ ] **Step 5: Break it on purpose.** Change the flag check from `!== "true"` to `=== "false"` (an unset flag would then show the button). Run the test: `renders nothing with the flag off` FAILS. Restore: PASS.

- [ ] **Step 6: Commit.**

```bash
git add components/LangfuseButton.tsx components/LangfuseButton.test.tsx .env.local.example
git commit -m "feat(research): Langfuse button behind a warning and NEXT_PUBLIC_SHOW_LANGFUSE_LINKS (#103)"
```

---

## Hand-off to C and D

- Import paths from `app/(research)/research/metrics/`: `../../_shared/viewer`, `../../_shared/getResearchViewer`, `../../_shared/components/ResearchHeader`; `@/components/LangfuseButton`.
- The production flag value is set by the owner in the deploy's environment; this plan only documents it.
