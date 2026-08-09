# Classroom Sharing — Plan B: StudentTabBar & Navigation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bottom tab bar to the student flow (Bookshelf / Gallery / Profile), wire it into the layout with proper mobile padding, lift the write FAB above it, and move logout out of the header and into the settings page.

**Architecture:** `StudentTabBar` is a single `"use client"` component (needs `usePathname` for active state) placed in the layout. The layout (server component) passes `profileId` to it directly from `params`. Desktop nav is plain `<Link>` elements in the server layout header — no client component needed for that. Logout moves from the layout header into `settings/page.tsx`.

**Tech Stack:** Next.js 15, `next/navigation` (`usePathname`), Vitest + `@testing-library/react`

## Global Constraints

- Bottom tab bar: `md:hidden`, fixed bottom, `≥44px` tap targets, `env(safe-area-inset-bottom)`, text label beside icon (spec §5 + CC-6).
- Three tabs only: Bookshelf (`/s/[profileId]`), Gallery (`/s/[profileId]/gallery`), Profile (`/s/[profileId]/settings`) — spec §5.
- Active tab: `aria-current="page"` (spec §6 test 10).
- No `motion`, no Realtime, no new dependencies.
- `layout.tsx` `<main>` gets `pb-20 md:pb-0` so content scrolls above the bar (spec §5).
- Write FAB in `page.tsx` lifts from `bottom-6` to `bottom-24` so it clears the bar.
- Logout moves to `settings/page.tsx` — the layout header loses the logout form.
- Desktop nav: three `<Link>` elements in the layout header, `hidden md:flex`.
- No new packages. `usePathname` is already available from `next/navigation`.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `frontend/components/StudentTabBar.tsx` | `"use client"` — mobile bottom nav, `usePathname` active state |
| Create | `frontend/components/StudentTabBar.test.tsx` | Spec §6 tests 9–10 |
| Modify | `frontend/app/s/[profileId]/layout.tsx` | Add tab bar + desktop nav links, add main padding, remove logout from header |
| Modify | `frontend/app/s/[profileId]/settings/page.tsx` | Add logout button |
| Modify | `frontend/app/s/[profileId]/page.tsx` | Lift FAB from `bottom-6` to `bottom-24` |

---

### Task 1: `StudentTabBar` component

**Files:**
- Create: `frontend/components/StudentTabBar.tsx`

**Interfaces:**
- Props: `{ profileId: string }`
- Produces: named export `StudentTabBar`

- [ ] **Step 1: Write the component**

```tsx
"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  {
    label: "Bookshelf",
    icon: "📚",
    href: (id: string) => `/s/${id}`,
  },
  {
    label: "Gallery",
    icon: "🖼️",
    href: (id: string) => `/s/${id}/gallery`,
  },
  {
    label: "Profile",
    icon: "👤",
    href: (id: string) => `/s/${id}/settings`,
  },
] as const;

export function StudentTabBar({ profileId }: { profileId: string }) {
  const pathname = usePathname();

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-surface border-t border-primary/15"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="flex">
        {TABS.map(({ label, icon, href }) => {
          const path = href(profileId);
          const isActive = pathname === path;
          return (
            <Link
              key={label}
              href={path}
              aria-current={isActive ? "page" : undefined}
              className={[
                "flex flex-1 flex-col items-center gap-0.5 py-2 min-h-[44px]",
                "text-xs font-medium transition-colors",
                isActive ? "text-primary" : "text-muted-foreground",
              ].join(" ")}
            >
              <span aria-hidden="true" className="text-xl leading-none">
                {icon}
              </span>
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors referencing `StudentTabBar.tsx`.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/StudentTabBar.tsx
git commit -m "feat(nav): add StudentTabBar client component"
```

---

### Task 2: `StudentTabBar.test.tsx` (Spec §6 tests 9–10)

**Files:**
- Create: `frontend/components/StudentTabBar.test.tsx`

**Interfaces:**
- Consumes: `StudentTabBar` from `./StudentTabBar`
- Mocks: `next/navigation` (`usePathname`)

- [ ] **Step 1: Write the failing tests**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { StudentTabBar } from "./StudentTabBar";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const PROFILE_ID = "student-1";

describe("StudentTabBar", () => {
  // Test 9 — three tabs each with a text label beside its icon
  it("renders three tabs each with a visible text label", () => {
    const { usePathname } = vi.mocked(await import("next/navigation"));
    usePathname.mockReturnValue(`/s/${PROFILE_ID}`);

    render(<StudentTabBar profileId={PROFILE_ID} />);

    expect(screen.getByText("Bookshelf")).toBeInTheDocument();
    expect(screen.getByText("Gallery")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();

    // Icons are in the DOM (aria-hidden, but present)
    expect(screen.getByText("📚")).toBeInTheDocument();
    expect(screen.getByText("🖼️")).toBeInTheDocument();
    expect(screen.getByText("👤")).toBeInTheDocument();
  });

  // Test 10 — active tab marked aria-current="page"
  it("marks the tab matching the current pathname as aria-current=page", () => {
    const { usePathname } = vi.mocked(await import("next/navigation"));

    // Bookshelf active
    usePathname.mockReturnValue(`/s/${PROFILE_ID}`);
    const { rerender } = render(<StudentTabBar profileId={PROFILE_ID} />);
    expect(screen.getByText("Bookshelf").closest("a")).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Gallery").closest("a")).not.toHaveAttribute(
      "aria-current",
    );

    // Gallery active
    usePathname.mockReturnValue(`/s/${PROFILE_ID}/gallery`);
    rerender(<StudentTabBar profileId={PROFILE_ID} />);
    expect(screen.getByText("Gallery").closest("a")).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Bookshelf").closest("a")).not.toHaveAttribute(
      "aria-current",
    );
  });
});
```

**Note on async mock imports in Vitest:** The `vi.mocked(await import(...))` pattern works because `vi.mock` hoists to the top. If you get a TS error, replace with:
```ts
import * as Nav from "next/navigation";
const usePathname = vi.mocked(Nav.usePathname);
```

- [ ] **Step 2: Run — expect tests to pass (component already written in Task 1)**

```bash
cd frontend && npx vitest run components/StudentTabBar.test.tsx
```

Expected: 2 passing.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/StudentTabBar.test.tsx
git commit -m "test(nav): add spec §6 tests 9–10 for StudentTabBar"
```

---

### Task 3: Modify `layout.tsx` — wire tab bar, desktop nav, bottom padding

**Files:**
- Modify: `frontend/app/s/[profileId]/layout.tsx`

**What changes:**
1. Import `StudentTabBar`
2. Add desktop nav links (`hidden md:flex`) in the header — replaces the logout button in the header
3. Remove the logout `<form>` from the header
4. Add `pb-20 md:pb-0` to `<main>`
5. Render `<StudentTabBar profileId={profileId} />` after `<main>`

**Read the file first** before editing — the layout is ~88 lines.

- [ ] **Step 1: Read the current layout**

```bash
cat -n frontend/app/s/\[profileId\]/layout.tsx
```

Identify:
- The `<header>` block (roughly lines 52–65) — contains the greeting + logout form
- The `<main className="flex-1">` line

- [ ] **Step 2: Apply the edits**

Add this import at the top of the file (after existing imports):
```ts
import { StudentTabBar } from "@/components/StudentTabBar";
```

Replace the `<header>` interior. Current:
```tsx
<div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
  <span className="font-display text-xl font-extrabold text-primary">
    Hi, {data.display_nickname}!
  </span>
  <form action="/auth/signout" method="post">
    <button type="submit" className="min-h-11 px-4 py-2 rounded-xl border ...">
      Log out
    </button>
  </form>
</div>
```

New (logout removed, desktop nav added):
```tsx
<div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
  <span className="font-display text-xl font-extrabold text-primary">
    Hi, {data.display_nickname}!
  </span>
  <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
    <Link href={`/s/${profileId}`}>📚 Bookshelf</Link>
    <Link href={`/s/${profileId}/gallery`}>🖼️ Gallery</Link>
    <Link href={`/s/${profileId}/settings`}>👤 Profile</Link>
  </nav>
</div>
```

Replace `<main className="flex-1">` with:
```tsx
<main className="flex-1 pb-20 md:pb-0">
```

After the closing `</main>`, add:
```tsx
<StudentTabBar profileId={profileId} />
```

Make sure `Link` is imported from `"next/link"` (add if not already present).

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Run full test suite**

```bash
cd frontend && npx vitest run
```

Expected: all tests pass (layout has no test file — no regressions to catch here, but other tests should be clean).

- [ ] **Step 5: Commit**

```bash
git add frontend/app/s/\[profileId\]/layout.tsx
git commit -m "feat(nav): wire StudentTabBar into student layout, add desktop nav, move logout to settings"
```

---

### Task 4: Add logout to `settings/page.tsx`

**Files:**
- Modify: `frontend/app/s/[profileId]/settings/page.tsx`

**What changes:** The logout form (currently in the layout header) moves here. The settings page becomes a real Profile screen: password change + log out.

**Read the file first** — it's a `"use client"` password-change component.

- [ ] **Step 1: Read the current settings page**

```bash
cat -n frontend/app/s/\[profileId\]/settings/page.tsx
```

Identify: the wrapping `<main>` and the bottom of the form/button area.

- [ ] **Step 2: Add the logout section**

After the existing password-change form (but still inside `<main>`), add:

```tsx
<div className="mt-8 border-t border-border pt-6">
  <form action="/auth/signout" method="post">
    <button
      type="submit"
      className="min-h-11 w-full rounded-xl border border-destructive/40 px-4 py-2 text-sm text-destructive hover:bg-destructive/5 transition-colors"
    >
      Log out
    </button>
  </form>
</div>
```

Use the same `<form action="/auth/signout" method="post">` mechanism as the layout — it's a Next.js route handler, no client-side Supabase call needed.

- [ ] **Step 3: Run the settings tests**

```bash
cd frontend && npx vitest run app/s/\\[profileId\\]/settings/
```

Expected: all settings tests still pass (we only added JSX, didn't touch the password logic).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/s/\[profileId\]/settings/page.tsx
git commit -m "feat(settings): add logout button to Profile/settings page"
```

---

### Task 5: Lift write FAB + doc propagation

**Files:**
- Modify: `frontend/app/s/[profileId]/page.tsx` (one-line change)
- Modify: `docs/specs/ROUTE_MAP.md`
- Modify: `docs/specs/USER_FLOW.md`
- Modify: `docs/MASTER_SPEC.md`
- Modify: `docs/product/DECISION_BACKLOG.md`
- Modify: `AGENTS.md`

#### Part A — Lift the FAB

The write FAB in `frontend/app/s/[profileId]/page.tsx` is `fixed bottom-6`. With the tab bar at `fixed bottom-0` (~56px + safe area), the FAB lands underneath it on xs screens.

- [ ] **Step 1: Find the FAB div**

```bash
grep -n "bottom-6" frontend/app/s/\[profileId\]/page.tsx
```

Expected: one line containing `sm:hidden fixed bottom-6 left-1/2`.

- [ ] **Step 2: Change `bottom-6` to `bottom-24`**

`bottom-24` = 6rem = 96px from the bottom, which clears a ~56px tab bar with comfortable margin.

Find:
```tsx
<div className="sm:hidden fixed bottom-6 left-1/2 -translate-x-1/2 w-[calc(100%-48px)] z-20">
```

Replace with:
```tsx
<div className="sm:hidden fixed bottom-24 left-1/2 -translate-x-1/2 w-[calc(100%-48px)] z-20">
```

- [ ] **Step 3: Run bookshelf tests**

```bash
cd frontend && npx vitest run app/s/\\[profileId\\]/page.
```

Expected: all pass.

#### Part B — Doc propagation (spec §9)

- [ ] **Step 4: Update `docs/specs/ROUTE_MAP.md`**

  - Drop `/classroom/[classroomId]/gallery` (line ~39) — already covered by `/classroom/[classroomId]/books`.
  - Drop `/s/[profileId]/gallery/[bookId]` (lines ~58 and ~338) — reader reused (spec §3).
  - Lines ~154–155: mark the tab bar as built; correct the tab set to `Bookshelf / Gallery / Profile`.

- [ ] **Step 5: Update `docs/specs/USER_FLOW.md`**

  Line ~34: it currently says `Home / Bookshelf / Gallery`. Correct to `Bookshelf / Gallery / Profile`. (`/s/[profileId]` is both home and bookshelf — there is no separate Home tab.)

- [ ] **Step 6: Update `docs/MASTER_SPEC.md`**

  Line ~347: change `classroom-sharing` row status from `planned` / `draft` to `built`.

- [ ] **Step 7: Update `docs/product/DECISION_BACKLOG.md`**

  Line ~268: tick the `classroom-sharing` row. Drop it from the priority stack.

- [ ] **Step 8: Update `AGENTS.md` Validation Notes**

  Add one line in the existing Validation Notes style:
  ```
  - classroom-sharing (2026-08-09): gallery page + StudentTabBar built; `/s/[profileId]/gallery` live; tab bar covers Bookshelf / Gallery / Profile; logout moved to settings.
  ```

- [ ] **Step 9: Run full test suite one last time**

```bash
cd frontend && npx vitest run
```

Expected: all tests pass.

- [ ] **Step 10: Commit everything**

```bash
git add frontend/app/s/\[profileId\]/page.tsx \
        docs/specs/ROUTE_MAP.md \
        docs/specs/USER_FLOW.md \
        docs/MASTER_SPEC.md \
        docs/product/DECISION_BACKLOG.md \
        AGENTS.md
git commit -m "feat(classroom-sharing): lift write FAB above tab bar; propagate docs per spec §9"
```
