# Classroom Sharing — Plan A: Gallery Page

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/s/[profileId]/gallery` server-rendered page that shows the classroom's approved storybooks as a grid of cards, each linking to the existing reader.

**Architecture:** Async server component (`page.tsx`) using `createServerClient` from `@supabase/ssr` — same pattern as `app/s/[profileId]/layout.tsx`. One Supabase query returns approved, non-removed-author jobs; one batched `createSignedUrls` call signs the cover images. Cards are plain server JSX wrapping `<Link>`. No client state, no Realtime, no `motion`.

**Tech Stack:** Next.js 15 (async server components, async `params`/`cookies`), `@supabase/ssr` (server client), Vitest + `@testing-library/react` (tests)

## Global Constraints

- Bucket name is `storybook-images` — not `"pages"` (that was the bug fixed in `c98b57c`).
- `profiles!inner` is required in the select — a left join would make the `.is("profiles.removed_at", null)` filter a no-op.
- `input_text` must never be selected on this surface (PII — spec §4.3).
- Empty state copy: exactly `"Your class's books will show up here."` — no approval vocabulary (`approved`, `pending`, `waiting`, `rejected`, `teacher`).
- `createServerClient` cookie handler: `get` only, no `set`/`remove` — matches layout.tsx pattern.
- No `motion`, no `useEffect`, no client component — spec §4.4.
- Cover placeholder (no signed URL) renders a neutral `div` — does not throw.
- Signed URL TTL: 3600 seconds.
- Query limit: 200. Order: `approved_at` descending.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `frontend/app/s/[profileId]/gallery/loading.tsx` | Loading spinner — required by every-async-segment invariant |
| Create | `frontend/app/s/[profileId]/gallery/page.tsx` | Async server component: query → sign → render grid / empty state |
| Create | `frontend/app/s/[profileId]/gallery/page.test.tsx` | Spec §6 tests 1–8 (query assertions + render assertions) |

---

### Task 1: Gallery `loading.tsx`

**Files:**
- Create: `frontend/app/s/[profileId]/gallery/loading.tsx`

**Interfaces:**
- Produces: default export `Loading` — a React component with no props

**Why this first:** The AGENTS.md invariant requires every async route segment to ship a `loading.tsx`. Add it before `page.tsx` so the segment is complete the moment `page.tsx` lands.

- [ ] **Step 1: Write the file** — copy the spinner pattern from the parent `loading.tsx` at `frontend/app/s/[profileId]/loading.tsx`:

```tsx
export default function Loading() {
  return (
    <div className="font-kid min-h-screen bg-background flex items-center justify-center">
      <div className="w-8 h-8 rounded-full border-4 border-primary/30 border-t-primary animate-spin" />
    </div>
  );
}
```

- [ ] **Step 2: Verify the file exists**

```bash
ls frontend/app/s/\[profileId\]/gallery/
```
Expected: `loading.tsx` listed.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/s/\[profileId\]/gallery/loading.tsx
git commit -m "feat(gallery): add loading.tsx for gallery route segment"
```

---

### Task 2: Gallery `page.tsx`

**Files:**
- Create: `frontend/app/s/[profileId]/gallery/page.tsx`

**Interfaces:**
- Consumes: `createServerClient` from `@supabase/ssr` (already installed — check with `grep -r "supabase/ssr" frontend/package.json`)
- Produces: default export `GalleryPage({ params })` — async React component

**Reference:** `frontend/app/s/[profileId]/layout.tsx` — the authoritative example of how to build a `createServerClient` with read-only cookies in this project.

- [ ] **Step 1: Write the failing test first** — see Task 3 (write test file before implementing). Come back here after Task 3 Step 1.

- [ ] **Step 2: Implement `page.tsx`**

```tsx
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import Link from "next/link";

type Job = {
  id: string;
  approved_at: string;
  pages: { scene_id: string; caption: string; image_path: string }[] | null;
  profile_id: string;
  profiles: { display_nickname: string } | null;
};

export default async function GalleryPage({
  params,
}: {
  params: Promise<{ profileId: string }>;
}) {
  const { profileId } = await params;
  const cookieStore = await cookies();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    { cookies: { get: (name) => cookieStore.get(name)?.value } },
  );

  const { data } = await supabase
    .from("jobs")
    .select("id, approved_at, pages, profile_id, profiles!inner(display_nickname)")
    .not("approved_at", "is", null)
    .is("profiles.removed_at", null)
    .order("approved_at", { ascending: false })
    .limit(200);

  const jobs: Job[] = data ?? [];

  const paths = jobs.flatMap((j) =>
    j.pages?.[0]?.image_path ? [j.pages[0].image_path] : [],
  );
  const signedMap: Record<string, string> = {};
  if (paths.length > 0) {
    const { data: signed } = await supabase.storage
      .from("storybook-images")
      .createSignedUrls(paths, 3600);
    for (const s of signed ?? []) {
      if (s.signedUrl) signedMap[s.path] = s.signedUrl;
    }
  }

  if (jobs.length === 0) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center px-6">
        <p className="text-center text-muted-foreground">
          Your class&apos;s books will show up here.
        </p>
      </div>
    );
  }

  return (
    <ul className="grid grid-cols-2 gap-4 p-6 sm:grid-cols-3 md:grid-cols-4">
      {jobs.map((job) => {
        const coverPath = job.pages?.[0]?.image_path;
        const coverUrl = coverPath ? signedMap[coverPath] : undefined;
        const nickname = job.profiles?.display_nickname ?? "Unknown";
        return (
          <li key={job.id}>
            <Link
              href={`/s/${profileId}/book/${job.id}`}
              className="block overflow-hidden rounded-xl"
            >
              {coverUrl ? (
                <img
                  src={coverUrl}
                  alt={`Cover of book by ${nickname}`}
                  className="aspect-[3/4] w-full object-cover"
                />
              ) : (
                <div className="aspect-[3/4] w-full rounded-xl bg-muted/20" />
              )}
              <p className="mt-2 text-sm font-semibold">by {nickname}</p>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
```

- [ ] **Step 3: Run all gallery tests and verify they pass** (see Task 3 for the test run command).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/s/\[profileId\]/gallery/page.tsx
git commit -m "feat(gallery): add classroom gallery server component"
```

---

### Task 3: Gallery `page.test.tsx` (Spec §6 tests 1–8)

**Files:**
- Create: `frontend/app/s/[profileId]/gallery/page.test.tsx`

**Interfaces:**
- Consumes: default export `GalleryPage` from `./page`
- Mocks: `@supabase/ssr` (`createServerClient`), `next/headers` (`cookies`), `next/link`

**Important — test philosophy (spec §6):** Tests 2–5 assert against the **query builder call args**, not the returned rows. A mocked client returns whatever you hand it, so "an unapproved row does not appear" would pass vacuously against a page that never filtered. The filter itself is what must be proven.

**Test runner:** Vitest (not Jest). Config at `frontend/vitest.config.ts`. Run from `frontend/` dir.

- [ ] **Step 1: Write the test file**

```tsx
import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// vi.hoisted lifts these into the module-mock factory scope
const {
  mockLimit,
  mockOrder,
  mockIs,
  mockNot,
  mockSelect,
  mockFrom,
  mockCreateSignedUrls,
  mockStorageFrom,
} = vi.hoisted(() => {
  const mockLimit = vi.fn();
  const mockOrder = vi.fn(() => ({ limit: mockLimit }));
  const mockIs = vi.fn(() => ({ order: mockOrder }));
  const mockNot = vi.fn(() => ({ is: mockIs }));
  const mockSelect = vi.fn(() => ({ not: mockNot }));
  const mockFrom = vi.fn(() => ({ select: mockSelect }));
  const mockCreateSignedUrls = vi.fn();
  const mockStorageFrom = vi.fn(() => ({ createSignedUrls: mockCreateSignedUrls }));
  return {
    mockLimit,
    mockOrder,
    mockIs,
    mockNot,
    mockSelect,
    mockFrom,
    mockCreateSignedUrls,
    mockStorageFrom,
  };
});

vi.mock("@supabase/ssr", () => ({
  createServerClient: vi.fn(() => ({
    from: mockFrom,
    storage: { from: mockStorageFrom },
  })),
}));

vi.mock("next/headers", () => ({
  cookies: vi.fn().mockResolvedValue({ get: vi.fn().mockReturnValue(undefined) }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
  }: {
    href: string;
    children: React.ReactNode;
  }) => <a href={href}>{children}</a>,
}));

const PROFILE_ID = "profile-abc";
const params = Promise.resolve({ profileId: PROFILE_ID });

function makeJob(overrides: Record<string, unknown> = {}) {
  return {
    id: "job-1",
    approved_at: "2026-01-01T00:00:00Z",
    pages: [
      {
        scene_id: "s1",
        caption: "Once upon a time",
        image_path: "covers/job-1.jpg",
      },
    ],
    profile_id: "author-1",
    profiles: { display_nickname: "Kai" },
    ...overrides,
  };
}

describe("GalleryPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLimit.mockResolvedValue({ data: [] });
    mockCreateSignedUrls.mockResolvedValue({ data: [] });
  });

  // Test 1 — renders one card per row, each labelled with author's display_nickname
  it("renders one card per returned row with the author display_nickname", async () => {
    const jobs = [
      makeJob({ id: "job-1", profiles: { display_nickname: "Kai" } }),
      makeJob({ id: "job-2", profiles: { display_nickname: "Sam" } }),
    ];
    mockLimit.mockResolvedValue({ data: jobs });

    const { default: GalleryPage } = await import("./page");
    const jsx = await GalleryPage({ params });
    const { getByText } = render(jsx);

    getByText("by Kai");
    getByText("by Sam");
  });

  // Test 2 — .not called with ("approved_at", "is", null)
  it("filters out unapproved rows with .not('approved_at', 'is', null)", async () => {
    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });
    expect(mockNot).toHaveBeenCalledWith("approved_at", "is", null);
  });

  // Test 3 — .is called with ("profiles.removed_at", null) AND select has profiles!inner
  it("filters removed authors and uses profiles!inner embed", async () => {
    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });
    expect(mockIs).toHaveBeenCalledWith("profiles.removed_at", null);
    const selectArg: string = mockSelect.mock.calls[0][0];
    expect(selectArg).toContain("profiles!inner");
  });

  // Test 4 — order approved_at desc, limit 200
  it("orders by approved_at descending and limits to 200", async () => {
    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });
    expect(mockOrder).toHaveBeenCalledWith("approved_at", { ascending: false });
    expect(mockLimit).toHaveBeenCalledWith(200);
  });

  // Test 5 — input_text not selected
  it("does not select input_text", async () => {
    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });
    const selectArg: string = mockSelect.mock.calls[0][0];
    expect(selectArg).not.toContain("input_text");
  });

  // Test 6 — card links to /s/{profileId}/book/{jobId}
  it("links each card to the book reader at the correct URL", async () => {
    mockLimit.mockResolvedValue({ data: [makeJob({ id: "job-xyz" })] });

    const { default: GalleryPage } = await import("./page");
    const jsx = await GalleryPage({ params });
    const { getAllByRole } = render(jsx);

    const links = getAllByRole("link");
    expect(links[0]).toHaveAttribute("href", `/s/${PROFILE_ID}/book/job-xyz`);
  });

  // Test 7 — signed URLs from bucket storybook-images
  it("requests signed URLs from bucket storybook-images", async () => {
    mockLimit.mockResolvedValue({ data: [makeJob()] });

    const { default: GalleryPage } = await import("./page");
    await GalleryPage({ params });

    expect(mockStorageFrom).toHaveBeenCalledWith("storybook-images");
  });

  // Test 8 — empty state: no approval vocabulary
  it("empty state renders without any approval vocabulary", async () => {
    const { default: GalleryPage } = await import("./page");
    const jsx = await GalleryPage({ params });
    const { container } = render(jsx);

    const text = container.textContent?.toLowerCase() ?? "";
    for (const forbidden of [
      "approved",
      "pending",
      "waiting",
      "rejected",
      "teacher",
    ]) {
      expect(text, `found forbidden word: ${forbidden}`).not.toContain(forbidden);
    }
  });
});
```

- [ ] **Step 2: Run the tests — expect them to FAIL (page.tsx doesn't exist yet)**

```bash
cd frontend && npx vitest run app/s/\\[profileId\\]/gallery/page.test.tsx
```

Expected: errors about missing `./page` module.

- [ ] **Step 3: Implement `page.tsx`** — go complete Task 2 Steps 2–4 now.

- [ ] **Step 4: Run the tests again — expect all 8 to pass**

```bash
cd frontend && npx vitest run app/s/\\[profileId\\]/gallery/page.test.tsx
```

Expected: 8 passing.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
cd frontend && npx vitest run
```

Expected: all previously passing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/s/\[profileId\]/gallery/page.test.tsx
git commit -m "test(gallery): add spec §6 tests 1–8 for classroom gallery page"
```
