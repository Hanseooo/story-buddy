# Auth Routes — S4 Backend Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the server-side guard infrastructure S4 needs: Supabase server utilities, the `safe-redirect` validator, `middleware.ts`, and middleware tests (§9 tests 1–5). The frontend plan (`auth-s4-frontend`) depends on all of these.

**Architecture:** Three layers — (1) `utils/supabase/{server,middleware}.ts` expose `createServerClient` for server components and the middleware cookie wiring; (2) `lib/safe-redirect.ts` is a pure function with its own test file; (3) `middleware.ts` exports `guardRequest` (pure, testable without Edge runtime) and the default middleware function (thin async wrapper). The key invariant: middleware never reads `profiles.role` — path shape determines the redirect target (spec §2).

**Tech Stack:** Next.js 16.2.10 App Router, `@supabase/ssr` ^0.12.4, Vitest ^4.1.10

## Global Constraints

- `pnpm` only — `pnpm lint && pnpm test` must stay green
- All new packages are already installed — no `pnpm add`
- `getUser()` not `getSession()` in middleware — GoTrue round-trip (spec §4); upgrade path is `getClaims()` with asymmetric JWT keys, an infra change not taken here
- Fail closed on `getUser()` error — treat as unauthenticated, never as authenticated
- `?next=` is valid only when path starts with `/` and not `//`
- Never read `profiles.role` in middleware — path-shaped guard only (spec §2)
- `guardRequest` is a named export for testing; it is not part of the app's public API surface

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/utils/supabase/server.ts` | `createSupabaseServerClient()` — server components / server actions |
| Create | `frontend/utils/supabase/middleware.ts` | `createSupabaseMiddlewareClient()` — middleware cookie wiring |
| Create | `frontend/lib/safe-redirect.ts` | `safe(path)` — `?next=` open-redirect validator |
| Create | `frontend/lib/safe-redirect.test.ts` | Tests for `safe()` (§9 test 5) |
| Create | `frontend/middleware.ts` | `guardRequest` + default `middleware` export + `config` |
| Create | `frontend/middleware.test.ts` | Guard logic tests (§9 tests 1–4) |

---

## Task 1: Supabase server utilities

**Files:**
- Create: `frontend/utils/supabase/server.ts`
- Create: `frontend/utils/supabase/middleware.ts`

No direct tests — these are wiring over `@supabase/ssr`. Task 4's middleware tests mock `@supabase/ssr` and implicitly cover the paths.

**Interfaces produced** (consumed by Task 3 and the frontend plan):
```typescript
// utils/supabase/server.ts
export async function createSupabaseServerClient(): Promise<SupabaseClient>

// utils/supabase/middleware.ts
export async function createSupabaseMiddlewareClient(
  request: NextRequest
): Promise<{ supabase: SupabaseClient; response: NextResponse }>
```

- [ ] **Step 1: Create `frontend/utils/supabase/server.ts`**

```typescript
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createSupabaseServerClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          );
        },
      },
    }
  );
}
```

- [ ] **Step 2: Create `frontend/utils/supabase/middleware.ts`**

The cookie setter must write back to both the request (so the Supabase client sees fresh cookies) and the response (so the browser receives the refreshed token).

```typescript
import { createServerClient } from "@supabase/ssr";
import { NextRequest, NextResponse } from "next/server";

export async function createSupabaseMiddlewareClient(request: NextRequest) {
  let response = NextResponse.next({ request });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) =>
            request.cookies.set(name, value)
          );
          response = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  return { supabase, response };
}
```

- [ ] **Step 3: Verify lint passes**

```bash
cd frontend && pnpm lint
```
Expected: no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/utils/supabase/server.ts frontend/utils/supabase/middleware.ts
git commit -m "feat(auth-s4): supabase server + middleware client utilities"
```

---

## Task 2: `safe-redirect` utility (§9 test 5)

**Files:**
- Create: `frontend/lib/safe-redirect.ts`
- Test: `frontend/lib/safe-redirect.test.ts`

**Interfaces produced** (consumed by Task 3):
```typescript
// lib/safe-redirect.ts
export function safe(path: string): string | null
// Returns path unchanged when path.startsWith('/') && !path.startsWith('//')
// Returns null otherwise
```

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/lib/safe-redirect.test.ts
import { describe, it, expect } from "vitest";
import { safe } from "./safe-redirect";

describe("safe — §9 test 5", () => {
  it("accepts a normal path", () => expect(safe("/s/x/write")).toBe("/s/x/write"));
  it("accepts bare /", () => expect(safe("/")).toBe("/"));
  it("rejects a full URL", () => expect(safe("https://evil.com")).toBeNull());
  it("rejects a protocol-relative URL (open-redirect)", () =>
    expect(safe("//evil.com")).toBeNull());
  it("rejects an empty string", () => expect(safe("")).toBeNull());
  it("rejects a relative path with no leading slash", () =>
    expect(safe("evil.com")).toBeNull());
});
```

- [ ] **Step 2: Run the failing test**

```bash
cd frontend && pnpm exec vitest run lib/safe-redirect.test.ts
```
Expected: FAIL — `Cannot find module './safe-redirect'`

- [ ] **Step 3: Implement `frontend/lib/safe-redirect.ts`**

```typescript
export function safe(path: string): string | null {
  if (!path.startsWith("/") || path.startsWith("//")) return null;
  return path;
}
```

- [ ] **Step 4: Run the passing test**

```bash
cd frontend && pnpm exec vitest run lib/safe-redirect.test.ts
```
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/safe-redirect.ts frontend/lib/safe-redirect.test.ts
git commit -m "feat(auth-s4): safe-redirect validator + tests (§9 test 5)"
```

---

## Task 3: `middleware.ts`

**Files:**
- Create: `frontend/middleware.ts`

The guard logic lives in `guardRequest` (pure function, exported for testing). The async `middleware` export is the thin wrapper that wires in the Supabase user and returns a `NextResponse`.

**Interfaces produced** (consumed by Task 4 tests, and implicitly by Next.js):
```typescript
// middleware.ts
export function guardRequest(pathname: string, userId: string | null): string | null
// Returns redirect URL string, or null if no redirect needed.

export async function middleware(request: NextRequest): Promise<Response>

export const config: { matcher: string[] }
```

**The three guard rules from spec §4:**
1. Student tree (`/s/...`): no session → `/join?next=<path>`; session with wrong profileId → `/s/<sub>`
2. Teacher tree (`/dashboard/...`): no session → `/login?next=<path>`
3. Already-signed-in on a door (`/join`, `/login`, `/signup`): redirect away

- [ ] **Step 1: Create `frontend/middleware.ts`**

```typescript
import { NextRequest, NextResponse } from "next/server";
import { createSupabaseMiddlewareClient } from "@/utils/supabase/middleware";
import { safe } from "@/lib/safe-redirect";

// ponytail: exported for unit tests — avoids Edge runtime in jsdom
export function guardRequest(
  pathname: string,
  userId: string | null
): string | null {
  if (pathname.startsWith("/s/")) {
    if (!userId) return `/join?next=${safe(pathname) ?? ""}`;
    const profileId = pathname.split("/")[2];
    if (profileId !== userId) return `/s/${userId}`;
  }
  if (pathname.startsWith("/dashboard") && !userId)
    return `/login?next=${safe(pathname) ?? ""}`;
  if (userId && pathname.startsWith("/join")) return `/s/${userId}`;
  if (userId && (pathname === "/login" || pathname === "/signup"))
    return "/dashboard";
  return null;
}

export async function middleware(request: NextRequest) {
  const { supabase, response } = await createSupabaseMiddlewareClient(request);
  // ponytail: getUser() not getSession() — verifies token with GoTrue (spec §4)
  // upgrade path: getClaims() + asymmetric JWT signing keys removes this round-trip (spec §4, open)
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  // Fail closed: error or missing user → treat as unauthenticated (spec §4)
  const userId = error || !user ? null : user.id;
  const redir = guardRequest(request.nextUrl.pathname, userId);
  if (redir) return NextResponse.redirect(new URL(redir, request.url));
  return response;
}

export const config = {
  matcher: [
    "/s/:path*",
    "/dashboard/:path*",
    "/login",
    "/signup",
    "/join",
    "/join/:path*",
  ],
};
```

- [ ] **Step 2: Verify lint**

```bash
cd frontend && pnpm lint
```
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/middleware.ts
git commit -m "feat(auth-s4): middleware — path-shaped guard, fails closed (spec §4)"
```

---

## Task 4: Middleware tests (§9 tests 1–4)

**Files:**
- Test: `frontend/middleware.test.ts`

Tests target `guardRequest` directly — no mocking of Next.js server APIs needed in jsdom. §9 test 5 (`?next=` validation) is in `safe-redirect.test.ts` (Task 2).

**Coverage map:**

| §9 test | What it checks | Test group |
|---------|---------------|------------|
| 1 | Unauthenticated `/s/<uuid>` → `/join`; `/dashboard` → `/login` | "unauthenticated protected routes" |
| 2 | Authenticated, segment ≠ sub → `/s/<sub>` | "profile mismatch" |
| 3 | Authenticated on `/join`, `/join/[code]` → `/s/<sub>`; on `/login` → `/dashboard` | "signed-in on a door" |
| 4 | Correct session on own `/s/<sub>` routes → no redirect | "pass-through" |
| 5 | `?next=` validation | `safe-redirect.test.ts` (Task 2) |

- [ ] **Step 1: Write the failing tests**

```typescript
// frontend/middleware.test.ts
import { describe, it, expect } from "vitest";
import { guardRequest } from "./middleware";

const UUID_A = "00000000-0000-0000-0000-000000000001";
const UUID_B = "00000000-0000-0000-0000-000000000002";

// §9 test 1
describe("guardRequest — unauthenticated protected routes", () => {
  it("unauthenticated /s/<uuid> → /join?next=...", () => {
    expect(guardRequest(`/s/${UUID_A}`, null)).toBe(`/join?next=/s/${UUID_A}`);
  });

  it("unauthenticated /s/<uuid>/write → /join?next=...", () => {
    expect(guardRequest(`/s/${UUID_A}/write`, null)).toBe(
      `/join?next=/s/${UUID_A}/write`
    );
  });

  it("unauthenticated /dashboard → /login?next=/dashboard", () => {
    expect(guardRequest("/dashboard", null)).toBe("/login?next=/dashboard");
  });

  it("unauthenticated /dashboard/settings → /login?next=...", () => {
    expect(guardRequest("/dashboard/settings", null)).toBe(
      "/login?next=/dashboard/settings"
    );
  });
});

// §9 test 2
describe("guardRequest — profile mismatch", () => {
  it("authenticated, profileId ≠ sub → /s/<sub>", () => {
    expect(guardRequest(`/s/${UUID_A}`, UUID_B)).toBe(`/s/${UUID_B}`);
  });

  it("authenticated, profileId ≠ sub on nested route → /s/<sub>", () => {
    expect(guardRequest(`/s/${UUID_A}/write`, UUID_B)).toBe(`/s/${UUID_B}`);
  });
});

// §9 test 3
describe("guardRequest — signed-in on a door", () => {
  it("authenticated on /join → /s/<sub>", () => {
    expect(guardRequest("/join", UUID_A)).toBe(`/s/${UUID_A}`);
  });

  it("authenticated on /join/[code] → /s/<sub>", () => {
    expect(guardRequest("/join/abc123", UUID_A)).toBe(`/s/${UUID_A}`);
  });

  it("authenticated on /login → /dashboard", () => {
    expect(guardRequest("/login", UUID_A)).toBe("/dashboard");
  });

  it("authenticated on /signup → /dashboard", () => {
    expect(guardRequest("/signup", UUID_A)).toBe("/dashboard");
  });
});

// §9 test 4 — pass-through cases
describe("guardRequest — no redirect", () => {
  it("authenticated on own /s/<sub> → null", () => {
    expect(guardRequest(`/s/${UUID_A}`, UUID_A)).toBeNull();
  });

  it("authenticated on own /s/<sub>/write → null", () => {
    expect(guardRequest(`/s/${UUID_A}/write`, UUID_A)).toBeNull();
  });

  it("unauthenticated / → null (public)", () => {
    expect(guardRequest("/", null)).toBeNull();
  });

  it("unauthenticated /login → null (public)", () => {
    expect(guardRequest("/login", null)).toBeNull();
  });

  it("unauthenticated /join → null (public)", () => {
    expect(guardRequest("/join", null)).toBeNull();
  });
});
```

- [ ] **Step 2: Run the tests**

At this point `middleware.ts` already exists from Task 3, so these should pass immediately.

```bash
cd frontend && pnpm exec vitest run middleware.test.ts
```
Expected: 15 tests PASS

- [ ] **Step 3: Run the full suite**

```bash
cd frontend && pnpm lint && pnpm test
```
Expected: all tests PASS (lint clean, full vitest run green)

- [ ] **Step 4: Commit**

```bash
git add frontend/middleware.test.ts
git commit -m "test(auth-s4): middleware guard tests — §9 tests 1–4"
```

---

## Out of Scope (Frontend Plan owns these)

The following S4 deliverables are intentionally excluded and will be built in `auth-s4-frontend`:

- Route tree moves: `write/`, `process/[jobId]/`, `book/[jobId]/` → `s/[profileId]/`
- `s/[profileId]/layout.tsx` — `StudentShell` (greeting, logout)
- `s/[profileId]/page.tsx` — bookshelf with Realtime channel + `classify`
- `s/[profileId]/settings/page.tsx` — password change
- `/join/page.tsx` + `/join/[code]/page.tsx` — three-step wizard
- `/login/page.tsx` + `/signup/page.tsx` — teacher auth
- `/dashboard/page.tsx` — stated placeholder
- Landing page `/` — two-door update (CTAs to `/signup` + `/join`)
- `loading.tsx` + `error.tsx` for student tree and auth pages
- §9 tests 6–13 (`/join` wizard, bookshelf, `StudentShell` states)

The frontend plan should import from:
- `@/utils/supabase/server` → `createSupabaseServerClient` (for server components)
- `@/lib/safe-redirect` → `safe` (for the `/join` page's `?next=` consumption)
- `@/lib/useJob` → `classify` (verbatim, no changes — spec §7.2)
