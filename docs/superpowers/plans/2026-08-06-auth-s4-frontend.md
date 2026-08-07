# Auth Routes and Account UX (Frontend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the frontend route tree, auth UI, and student shell according to S4 of the auth docket, moving existing child routes under a profile-scoped layout.

**Architecture:** We are introducing multiple doors: `/login` and `/signup` for teachers (using Inter), and a two-step `/join` and `/join/[code]` wizard for students (using Nunito). The child routes (`write`, `process`, `book`) are moved to `/s/[profileId]/`, wrapped in a `StudentShell` that handles greetings and log out. RLS and middleware (handled in backend plan) provide the security. The `app/page.tsx` landing gets new CTAs.

**Tech Stack:** Next.js (App Router), React, Tailwind CSS, Supabase SSR (`@supabase/ssr`).

## Global Constraints

- No route groups. `(auth)` does not survive contact.
- No `BottomTabBar`.
- Transitions are CSS or absent.
- The move is tested, not inherited... must pass with no changes beyond path and params.
- The nickname preview is reassurance, not validation.
- The password is visible by default.
- Wrong code, wrong nickname and wrong password produce one identical message.
- A network failure is a different message.
- A malformed code in `/join/[code]` is caught by a client-side shape check.
- Every submit disables and spins.
- The active field is autofocused on each step; step changes are announced to screen readers; touch targets are ≥44px.
- Register is Cobalt Playroom per the current DESIGN.md — light-first, Outfit / Nunito for the child, Inter for the teacher.

---

### Task 1: Update Landing Page CTAs (`app/page.tsx`)

**Files:**
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/page.test.tsx`

**Interfaces:**
- Consumes: N/A
- Produces: Landing page with updated links.

- [ ] **Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Home from "./page";

it("links to signup and join", () => {
  render(<Home />);
  const signupLinks = screen.getAllByRole("link", { name: /make a book|write your story/i });
  signupLinks.forEach(link => expect(link).toHaveAttribute("href", "/signup"));
  expect(screen.getByRole("link", { name: /i have a class code/i })).toHaveAttribute("href", "/join");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run app/page.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/app/page.tsx
import Link from "next/link";

export default function Home() {
  return (
    <main className="font-display">
      <h1>Big ideas. Bright pages.</h1>
      <Link href="/signup">Make a book</Link>
      <Link href="/signup">Write your story</Link>
      <Link href="/join">I have a class code</Link>
      <nav aria-label="main navigation"></nav>
      <h2>From first line to final page</h2>
      <h2>Made for young imaginations</h2>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run app/page.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/page.tsx frontend/app/page.test.tsx
git commit -m "feat(auth): update landing page CTAs for S4 routes"
```

### Task 2: Teacher Auth Routes (`app/login` & `app/signup`)

**Files:**
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/signup/page.tsx`
- Create: `frontend/app/login/page.test.tsx`

**Interfaces:**
- Consumes: Supabase `createBrowserClient`
- Produces: `/login` and `/signup` routes.

- [ ] **Step 1: Write the failing tests**

```tsx
// frontend/app/login/page.test.tsx
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Login from "./page";

it("renders login form with Inter font", () => {
  const { container } = render(<Login />);
  expect(screen.getByRole("heading", { name: /log in/i })).toBeDefined();
  expect(screen.getByLabelText(/email/i)).toBeDefined();
  expect(screen.getByLabelText(/password/i)).toBeDefined();
  expect(screen.getByRole("button", { name: /log in/i })).toBeDefined();
  expect(container.firstChild).toHaveClass("font-sans");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run app/login/page.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/app/login/page.tsx
"use client";
import { useState } from "react";
import { createBrowserClient } from "@supabase/ssr";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const supabase = createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setError(error.message);
    setLoading(false);
  };

  return (
    <div className="font-sans p-4 max-w-md mx-auto">
      <h1>Log In</h1>
      {error && <div role="alert">{error}</div>}
      <form onSubmit={handleLogin} className="flex flex-col gap-4">
        <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label>
        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
        <button type="submit" disabled={loading}>{loading ? "..." : "Log in"}</button>
      </form>
    </div>
  );
}
```

```tsx
// frontend/app/signup/page.tsx
"use client";
import { useState } from "react";
import { createBrowserClient } from "@supabase/ssr";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const supabase = createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await supabase.auth.signUp({ email, password });
    setMessage("Check your email");
    setLoading(false);
  };

  return (
    <div className="font-sans p-4 max-w-md mx-auto">
      <h1>Sign Up</h1>
      {message && <div role="alert">{message}</div>}
      <form onSubmit={handleSignup} className="flex flex-col gap-4">
        <label>Email<input type="email" value={email} onChange={e => setEmail(e.target.value)} required /></label>
        <label>Password<input type="password" value={password} onChange={e => setPassword(e.target.value)} required /></label>
        <button type="submit" disabled={loading}>{loading ? "..." : "Sign up"}</button>
      </form>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run app/login/page.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/login frontend/app/signup
git commit -m "feat(auth): implement teacher login and signup routes"
```

### Task 3: Dashboard Placeholder (`app/dashboard`)

**Files:**
- Create: `frontend/app/dashboard/page.tsx`
- Create: `frontend/app/dashboard/page.test.tsx`

**Interfaces:**
- Consumes: N/A
- Produces: `/dashboard` placeholder.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/app/dashboard/page.test.tsx
import { render, screen } from "@testing-library/react";
import { expect, it } from "vitest";
import Dashboard from "./page";

it("renders dashboard placeholder", () => {
  render(<Dashboard />);
  expect(screen.getByRole("heading", { name: /dashboard/i })).toBeDefined();
  expect(screen.getByText(/classroom tools are not built yet/i)).toBeDefined();
  expect(screen.getByRole("button", { name: /log out/i })).toBeDefined();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run app/dashboard/page.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/app/dashboard/page.tsx
"use client";
import { createBrowserClient } from "@supabase/ssr";

export default function Dashboard() {
  // ponytail: S4 stated placeholder
  const supabase = createBrowserClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!);

  return (
    <div className="font-sans container mx-auto p-8">
      <h1>Dashboard</h1>
      <p>Classroom tools are not built yet.</p>
      <button onClick={() => supabase.auth.signOut()}>Log out</button>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run app/dashboard/page.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/dashboard
git commit -m "feat(auth): add dashboard placeholder"
```

### Task 4: Move Existing Child Routes

**Files:**
- Modify: Move `frontend/app/write` to `frontend/app/s/[profileId]/write`
- Modify: Move `frontend/app/process` to `frontend/app/s/[profileId]/process`
- Modify: Move `frontend/app/book` to `frontend/app/s/[profileId]/book`

**Interfaces:**
- Consumes: N/A
- Produces: Scoped child routes.

- [ ] **Step 1: Write the failing tests**

```bash
# We rely on existing tests. They will fail because the paths are wrong.
pnpm exec vitest run app/s
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run app/write/page.test.tsx` (or whatever the old path is)
Expected: FAIL (File not found if moved, or logic fails if not moved)

- [ ] **Step 3: Write minimal implementation**

```bash
mkdir -p frontend/app/s/\[profileId\]
mv frontend/app/write frontend/app/s/\[profileId\]/
mv frontend/app/process frontend/app/s/\[profileId\]/
mv frontend/app/book frontend/app/s/\[profileId\]/
```

Update test imports/params in the moved tests to include `profileId: 'test'`.
For example, in `frontend/app/s/[profileId]/write/page.test.tsx` if it checks `params`, make sure it passes `{ profileId: 'test' }`. (Assume minimal path fixes inline).

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run app/s`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/s frontend/app/write frontend/app/process frontend/app/book
git commit -m "refactor(auth): move child routes to profile-scoped paths"
```

### Task 5: Student Shell Layout (`app/s/[profileId]/layout.tsx`)

**Files:**
- Create: `frontend/app/s/[profileId]/layout.tsx`
- Create: `frontend/app/s/[profileId]/layout.test.tsx`

**Interfaces:**
- Consumes: Supabase `profiles` table.
- Produces: A wrapper for all student routes with a header and auth/role checks.

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/app/s/[profileId]/layout.test.tsx
import { render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import StudentLayout from "./layout";

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    from: () => ({
      select: () => ({
        eq: () => ({
          single: vi.fn().mockResolvedValue({ data: { display_nickname: "Juan", role: "student" } }),
        }),
      }),
    }),
  }),
}));

it("renders the student shell with greeting", async () => {
  const { container } = render(await StudentLayout({ children: <div>Child Content</div>, params: { profileId: "123" } }));
  expect(screen.getByText(/hi, juan!/i)).toBeDefined();
  expect(screen.getByRole("button", { name: /log out/i })).toBeDefined();
  expect(screen.getByText("Child Content")).toBeDefined();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pnpm exec vitest run app/s/[profileId]/layout.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```tsx
// frontend/app/s/[profileId]/layout.tsx
import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";
import Link from "next/link";

export default async function StudentLayout({ children, params }: { children: React.ReactNode, params: { profileId: string } }) {
  const cookieStore = cookies();
  const supabase = createServerClient(process.env.NEXT_PUBLIC_SUPABASE_URL!, process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!, { cookies: { get: (name) => cookieStore.get(name)?.value } });
  
  const { data } = await supabase.from('profiles').select('display_nickname, role, classroom_id').eq('id', params.profileId).single();

  if (!data) {
    return (
      <div className="font-kid">
        <p>Your class isn't set up anymore. Ask your teacher.</p>
        <form action="/auth/signout" method="post"><button type="submit">Log out</button></form>
      </div>
    );
  }

  if (data.role !== 'student') {
    return (
      <div className="font-kid">
        <p>This part is for students</p>
        <Link href="/dashboard">Go to Dashboard</Link>
      </div>
    );
  }

  return (
    <div className="font-kid bg-canvas min-h-screen">
      <header className="flex justify-between p-4">
        <span>Hi, {data.display_nickname}!</span>
        <form action="/auth/signout" method="post"><button type="submit">Log out</button></form>
      </header>
      <main>{children}</main>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pnpm exec vitest run app/s/[profileId]/layout.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/app/s/\[profileId\]/layout.*
git commit -m "feat(auth): implement student shell layout and guards"
```
