# Feature Spec — auth: routes, guards & account UX

**Status:** draft · **Phase:** 2 · **Owner:** `frontend/middleware.ts`, `frontend/app/`
**Derived from:** `docs/specs/auth-and-classroom-docket.md` S4 · **Rationale:** ADR-006, ADR-017,
ADR-021, MASTER_SPEC §6 (CC-4, CC-6, CC-8, CC-9)

> The last session of the docket. Every URL and every screen the identity layer adds or moves.
> This spec re-opens **no** schema (S1), **no** session mechanism (S2), and **no** policy (S3).
> The gallery (`classroom-sharing`), the teacher dashboard (`teacher-dashboard`) and the
> `(research)/` routes (`annotation-surface`) are out.

## 1. Purpose

S1 gave every actor a row, S2 gave every actor a session, S3 gave every row a policy. Nothing
routes to any of it: the kid routes are still flat (`/write`, `/process/[jobId]`, `/book/[jobId]`),
`frontend/middleware.ts` does not exist, and there is no screen on which a child logs in.

This spec closes that. When it is done, every route in the tree has a stated auth level, a stated
redirect on failure, and a chosen rendering for the states nobody wants.

## 2. The finding that shapes the session

**`middleware.ts` cannot know a user's role.**

S1-2 puts the role in `profiles.role`, read through `auth_role()` — deliberately not a JWT claim, so
that a revoked role takes effect on the next query rather than the next token refresh.
`ROUTE_MAP.md:196` forbids server-side data fetching in middleware. Middleware can therefore see
*that* a session exists and *whose* it is (`sub` is in the token), but not *what role* it is.

Every "student expiry → `/join`, teacher expiry → `/login`" line in `ROUTE_MAP.md` §4 and in S2-6
assumes knowledge middleware does not have.

**Resolution: the guard is path-shaped, and the role is never consulted.** The URL says which door
was knocked on, and that is enough to pick a redirect target. Authorization is not being decided
here — RLS decides it. Middleware only picks where to send someone who has no business being on a
path, and being wrong is a cosmetic cost (an empty page instead of a tidy redirect), never a
disclosure.

Two rejected alternatives, recorded so no later session re-litigates them:

- *A non-authoritative `sb-role` cookie*, written at login and read by middleware for routing only.
  Gives exact redirects for every wrong-role case, at the cost of a second cookie that can disagree
  with `profiles.role` and a permanent comment explaining that it is a hint, not a guard.
- *Amending `ROUTE_MAP.md:196` to query `profiles` in middleware.* Always correct; costs a database
  round-trip on every navigation and puts a latency floor on kid routes that have none today.

Reading the role **client-side** is not affected by any of this — §7 does exactly that. The
constraint is on middleware alone.

## 3. Route tree

```
frontend/app/
├── layout.tsx                        unchanged
├── page.tsx                          /            landing — two doors (§6.1)
├── login/page.tsx                    /login       teacher · Inter register
├── signup/page.tsx                   /signup      teacher · Inter register
├── join/
│   ├── page.tsx                      /join        child · Nunito register · step 1
│   └── [code]/page.tsx               /join/[code] child · steps 2–3
├── dashboard/page.tsx                /dashboard   stated placeholder (§6.3)
└── s/[profileId]/
    ├── layout.tsx                    StudentShell
    ├── page.tsx                      bookshelf
    ├── settings/page.tsx             child's own password change
    ├── write/page.tsx                ← moved from app/write/
    ├── process/[jobId]/page.tsx      ← moved from app/process/
    └── book/[jobId]/page.tsx         ← moved from app/book/
```

### 3.1 Auth level per route

| Route | Auth level | Redirect on failure |
|---|---|---|
| `/` | Public | — |
| `/login`, `/signup` | Public | Authenticated → `/dashboard` |
| `/join`, `/join/[code]` | Public | Authenticated → `/s/<sub>` |
| `/dashboard` | Session required | → `/login?next=…` |
| `/s/[profileId]/**` | Session required **and** `profileId === sub` | No session → `/join?next=…` · mismatch → `/s/<sub>` |

There is no separate "classroom-scoped" middleware level. `ROUTE_MAP.md` §4 lists one; S3 already
enforces it in the database (`auth_classroom_id()`, S3-11), and expressing it in middleware would
require the data fetch §2 rules out.

### 3.2 Reconciliations against `ROUTE_MAP.md`

`ROUTE_MAP.md` is `status: draft` and was written before the kid-flow docket. Per the docket it is
input to reconcile, not decisions to re-derive. Four of its commitments shrink:

- **No route groups.** `(auth)` does not survive contact — `/join` is the kid register and
  `/login`/`/signup` are the teacher register, so they share no layout. `(immersive)` exists to
  strip nav chrome, and there is no nav chrome to strip yet.
- **No `BottomTabBar`.** §3 specifies three tabs (Home / Gallery / Profile); Gallery is
  `classroom-sharing`'s. A three-tab bar with one live tab is scaffolding for later. `StudentShell`
  carries the header, the greeting and log out; the tab bar arrives with the gallery.
- **No `/write/style`.** The style picker is a pre-job authoring step. kid-flow S4 placed it outside
  its scope and nothing has claimed it since.
- **§5's animation table is not implemented.** kid-flow rejected `motion` under AGENTS.md §2 and
  nothing in S4 changes that argument. Transitions are CSS or absent.

`ROUTE_MAP.md` §7's "no query params for navigation state" stands, with the `?next=` exception its
own §4 already established at line 173.

### 3.3 The move is tested, not inherited

kid-flow constraint 5 and `ROUTE_MAP.md:61-65` both describe the flat → `/s/[profileId]` move as "a
directory rename plus a middleware entry". `/book/[jobId]` and `/process/[jobId]` carry four-bucket
render logic and a Realtime subscription, so the claim is worth checking rather than assuming.

**The test is the existing test files.** `write/page.test.tsx`, `process/[jobId]/page.test.tsx` and
`book/[jobId]/page.test.tsx` move with their pages and must pass with **no changes beyond path and
params**. If any of them needs a logic edit, the claim was false and this spec is amended to say so.

## 4. `middleware.ts`

```ts
// matcher: /s/:path*, /dashboard/:path*, /login, /signup, /join/:path*
const { data: { user } } = await supabase.auth.getUser()   // createServerClient — S2-6

// 1. student tree
if (path.startsWith('/s/')) {
  if (!user)                              return redirect(`/join?next=${safe(path)}`)
  if (path.split('/')[2] !== user.id)     return redirect(`/s/${user.id}`)
}
// 2. teacher tree
if (path.startsWith('/dashboard') && !user) return redirect(`/login?next=${safe(path)}`)

// 3. already signed in, sitting on a door
if (user && path.startsWith('/join'))                    return redirect(`/s/${user.id}`)
if (user && (path === '/login' || path === '/signup'))   return redirect('/dashboard')
```

**`getUser()`, not `getSession()`.** `getSession()` trusts the cookie without verifying it.
`getUser()` costs one GoTrue round-trip per protected navigation — the same cost S2 §5.1 weighed
explicitly and accepted as noise at N ≤ 15. Local verification via `getClaims()` is faster but
requires migrating the project to asymmetric JWT signing keys, which is infra under AGENTS.md §2 and
§7. That is the named upgrade path and carries a `ponytail:` comment; it is not taken here.

**Rule 3 exists for the returning child.** The refresh token lives 60 days (S2-7). Without it, a
child opening a bookmarked `/join` the next morning is asked to log in for nothing. It infers the
intended role from which door was knocked on; a teacher who lands on `/join` is bounced to a
bookshelf that RLS renders empty, which is rare, harmless, and not a security event.

**Mismatch redirects, it does not 404.** The only realistic cause is a stale bookmark on a shared
classroom device — the previous child's URL. A ten-year-old gets their own bookshelf, not an error
page. The security boundary is RLS (S3), not this comparison.

**`?next=` is validated.** Accepted only when it starts with `/` and not `//`. Otherwise
`/join?next=https://evil.com` is a phishing hop off a child's login screen.

**`getUser()` failing fails closed** — redirect to the login door. Failing open on an auth guard is
not acceptable. The cost is bounded: a running job continues server-side (S2 §3.2) and the child
returns to it after logging back in.

## 5. `/join` — three steps across two routes

Step 1 lives at `/join`. Submitting it does `router.push('/join/' + code)`. Steps 2 and 3 are local
state inside `/join/[code]`. The wizard therefore needs no query params and no store: the segment
`ROUTE_MAP.md` already committed **is** the state.

Each step advance pushes a history entry, so browser back and the Android back gesture move
3 → 2 → 1 naturally. Without it, back jumps out of the wizard and discards the nickname.

### 5.1 The three fields

| Step | Field | Behavior |
|---|---|---|
| 1 | Classroom code | Six boxes, auto-advance, paste-aware, lowercased on entry |
| 2 | Nickname | Single field, live preview of the normalized form |
| 3 | Password | Show/hide toggle, **shown by default** |

**The code field ignores excluded characters.** S1-3's 31-symbol alphabet omits `0 O 1 I l`
precisely because they are ambiguous, so there is no valid character to map them to. The field
ignores the keystroke and, only after an ignored one, reveals: *"That letter isn't used in class
codes."* Specific, kind, and it leaks nothing.

**The nickname preview is reassurance, not validation.** It renders *"we'll look for:
`juan-dela-cruz`"*. `normalizeNickname` already forgives case, spacing, accents and stray hyphens,
which is most of what the age band gets wrong. If it **throws** at login it is caught and becomes
the generic failure of §5.2 — never a field-level error. S1 §5 puts nickname rejection on the
teacher's screen; a field-level error here would confirm to an attacker that their nickname guess
was well-formed.

**The password is visible by default.** Hidden entry is a leading mistype source for this age band
and there is no threat model on a classroom device that justifies the friction. The toggle hides it.

### 5.2 Submission and failure

On submit: normalize the nickname, compose `{nickname}@{code}.students.storybuddy.invalid` (S2-2),
call `signInWithPassword`.

**Wrong code, wrong nickname and wrong password produce one identical message** (S1 §6.1). Failure
returns to **step 1 of the current route** — the code screen on `/join`, the nickname screen on
`/join/[code]` — with every field preserved. One rule, correct in both cases: a child who followed
the teacher's link is never sent back to re-type a code they never typed.

**A network failure is a different message.** *"We can't reach StoryBuddy right now. Try again in a
moment."* Rendering "check your details" for dropped wifi sends a child re-typing correct
credentials indefinitely. This does not breach the anti-oracle rule — a transport error reveals
nothing about credentials.

**A malformed code in `/join/[code]`** (teacher mistyped the link, child truncated it) is caught by
a client-side shape check — six characters, all in-alphabet — which drops to step 1 with the code
shown for correction. No server contact, so no oracle.

**Rate limiting is Supabase Auth's**, not ours to build.

## 6. Teacher surfaces

### 6.1 `/` gets two doors

The landing is a teacher pitch and today CTAs to `/write` three times — routes that cease to exist,
so fixing them is in scope. They become `/signup`. Alongside them, an equally weighted child-shaped
entry: **"I have a class code"** → `/join`. Without it, a child who types the bare domain finds
nothing addressed to them. Retheming the landing is not in scope.

### 6.2 `/login` and `/signup`

Inter, centered card, unremarkable. `signInWithPassword` and `signUp` with email confirmation —
ADR-017 permits self-serve teacher signup and no further gate is added.

**Signup with an existing email always renders "check your email".** Supabase deliberately does not
disclose account existence; the UI must not undo that.

**The confirmation email redirects to `/login`**, which renders a "your email is confirmed — log in"
state. Unset, the link goes nowhere sensible.

### 6.3 `/dashboard` is a stated placeholder

A `ponytail:`-commented page carrying a heading, honest copy and log out, naming `teacher-dashboard`
as its successor. It exists so that signup is not a dead end and middleware rule 2 has a target.

It says in plain language that classroom tools are not built yet. A teacher who signs up today has
no classroom and no way to create one — an empty shell would read as broken.

### 6.4 Provisioning in the interim

`teacher-dashboard` owns `/classroom/[classroomId]/students`, so S4 ships a login flow with nothing
to create accounts. Until that row lands, **classrooms and student accounts are created by SQL or
the Supabase dashboard** — exactly how S1 §6.2 already provisions researchers. S4's tests run
end-to-end against hand-seeded rows.

**The teacher-initiated password reset screen moves to `teacher-dashboard`.** The docket's S4
cluster names it, but a reset screen needs a student picker, which is the roster list, which is most
of the student-management screen this session excludes. It belongs beside the create screen. Filed
as a docket amendment, not decided silently.

## 7. Student surfaces

### 7.1 `StudentShell`

One query on mount: `profiles` for `{display_nickname, role, classroom_id}`. It pays for itself
three times.

- **Greeting.** *"Hi, Juan!"* — on a shared classroom device this is the fastest confirmation that
  you are you.
- **Log out, first-class.** In the shell header and on settings. This is the shared-device product:
  without a visible "I'm done", the next child inherits the session, which is exactly the stale
  bookmark §4's redirect exists to clean up after. Better not to create it.
- **Two error states resolved instead of rendering empty** — §7.4.

### 7.2 Bookshelf — `/s/[profileId]`

> **RLS does not scope this query.** S3 §4.1 grants students **two** SELECT policies on `jobs`: own
> jobs *and* classmates' approved jobs. A bare `select * from jobs` puts peer books on a child's own
> shelf. The query carries `.eq('profile_id', profileId)` explicitly, and that gets a named test
> (§9.8). This is the one place in S4 where relying on the policy surface alone ships a silent bug.

Ordered newest first. Every one of `classify`'s four buckets gets a card — no **status** filter, and
no child is stranded: closing the tab mid-generation still leaves a route back to `/process`.

| Bucket | Card | Destination |
|---|---|---|
| `terminal-success` | Cover image | `/s/[pid]/book/[jobId]` |
| `in-flight` | "Still making it…" | `/s/[pid]/process/[jobId]` |
| `paused` | "Come meet your cast!" | `/s/[pid]/process/[jobId]` |
| `terminal-failure` | "This one didn't finish" | `/s/[pid]/write` (a new job — kid-flow S3) |

The accepted cost of showing all four: a failed job is permanent debris, because kid-flow S3 makes a
terminal job immutable and recovery is always a new job.

- **Covers** are `pages[0].image_path`, signed at read time (kid-flow constraint), via **one batched
  `createSignedUrls`** call, not one per card.
- **Titles** come from the first line of `input_text`, truncated. There is no title column and the
  schema is frozen; S4 does not add one.
- **One Realtime channel** for the whole shelf, filtered `profile_id=eq.<pid>` on UPDATE, so an
  in-flight card flips to ready without a refresh. `useJob.ts` is untouched — it stays the per-job
  hook for `/process` and `/book`. `classify` is reused verbatim, not reimplemented per card.

### 7.3 `/s/[profileId]/settings`

New password + confirm, show/hide, `auth.updateUser({ password })`. No current-password field — the
live session is the proof, and S1 §6.1 already defines this as the child's own operation.

Success confirms **inline** and stays on the page. Copy states the consequence plainly: *"If you
forget it, ask your teacher."* There is no inbox to recover to, by construction (S1 §3.1).

### 7.4 The states nobody wants

| State | Rendering |
|---|---|
| Session expires mid-write | → `/join?next=…`. Draft already lost on navigation (`ROUTE_MAP.md:246`); the existing confirm dialog covers deliberate exits |
| Session expires mid-process | → `/join?next=/s/[pid]/process/[jobId]`. Job continues server-side (S2 §3.2); re-login returns to the live stepper |
| Wrong code / nickname / password | One identical message (§5.2), back to step 1 of the current route, fields preserved |
| Network failure at login | Distinct message (§5.2) |
| Stale bookmark, another child's URL | → own bookshelf, silently (§4) |
| Job UUID belonging to another child | RLS returns no row → `classify(null)` = `not-found` → kid-flow's **already-built** not-found screen |
| Classroom deleted while the child is logged in | Bounded to ≤1h. S1's `on_profile_deleted` trigger removes the `auth.users` row, so *new* logins fail generically — but a live access token survives its hour with no `profiles` row, and RLS then returns empty everything. Shell's profile query returns nothing → *"Your class isn't set up anymore. Ask your teacher."* + log out |
| Teacher or researcher on a student route | Passes the guard on their own id. Shell reads `role !== 'student'` → *"This part is for students"* + link to `/dashboard`, instead of a silently empty bookshelf |

Six of these need no new component: they reuse what kid-flow S4 already shipped.

### 7.5 Loading, errors, accessibility

- **Every submit disables and spins** — `/join` steps, login, signup, password save.
  `signInWithPassword` takes roughly half a second and a ten-year-old will double-tap it
  (`ROUTE_MAP.md` §8 rule 5).
- `loading.tsx` for the student tree and the auth pages; `error.tsx` in ROUTE_MAP §8's two registers
  (kid: friendly, Nunito; teacher: clean, Inter).
- The active field is autofocused on each step; step changes are announced to screen readers; touch
  targets are ≥44px (DESIGN.md §1.6).
- Register is **Cobalt Playroom** per the current `DESIGN.md` — light-first, Outfit / Nunito for the
  child, Inter for the teacher. The docket's summary of `DESIGN.md` as "cartoon-pop for kids" is
  stale; this spec follows the file.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-4 Security** — every route has a stated auth level and redirect; `?next=` is validated
  against open redirect; the guard fails closed; the bookshelf query does not rely on RLS alone.
- [x] **CC-6 Accessibility** — 44px targets, autofocus per step, screen-reader step announcements,
  visible password by default.
- [x] **CC-8 Kid vs teacher design** — two registers, no shared auth layout, separate `error.tsx`.
- [x] **CC-9 Failure states = success states** — §7.4 renders eight of them, six with existing
  components.
- [x] **CC-2 PII** — no PII in URLs; `profileId` is a UUID. No new PII collected.
- [ ] CC-1, CC-3, CC-5, CC-7, CC-10 — not touched by this spec.

## 9. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

**The move (§3.3):**

1. `write`, `process/[jobId]` and `book/[jobId]` pass their **existing** test files with no changes
   beyond path and params.

**Middleware:**

2. Unauthenticated `/s/<uuid>` → `/join`; unauthenticated `/dashboard` → `/login`.
3. Authenticated, URL segment ≠ `sub` → redirect to `/s/<sub>`.
4. Authenticated on `/join` **and** on `/join/[code]` → `/s/<sub>`; authenticated on `/login` →
   `/dashboard`.
5. `?next=https://evil.com` and `?next=//evil.com` are rejected; `?next=/s/x/write` is honored.

**`/join`:**

6. Wrong code, wrong nickname and wrong password produce the **identical** message — asserted as
   string equality across all three, not as three separate matches.
7. A network rejection produces the network message, not the credentials message.
8. Failed login returns to step 1 of the current route with all fields preserved; `/join` returns to
   the code step, `/join/[code]` to the nickname step.
9. The code field ignores `0 O 1 I l` and surfaces the hint after an ignored keystroke.
10. A malformed `/join/[code]` segment drops to step 1 with the code shown.

**Bookshelf:**

11. **A classmate's approved job does not appear on the shelf** — the `.eq('profile_id')` leak test.
12. Each of `classify`'s four buckets renders its card with the correct `href`.
13. Absent `profiles` row → the "class isn't set up" screen; `role = 'teacher'` → the
    "this part is for students" screen.

Nickname normalization needs no new vectors — S1 §5.1's fourteen are already bound in
`frontend/lib/nickname.test.ts`.

## 10. Eval / quality checks

N/A. Nothing in this spec produces content whose quality is subjective.

## 11. Linked decisions & open questions

**Depends on:** S1 (`profiles` shape, nickname normalization, the deletion trigger), S2 (cookie
session via `@supabase/ssr`, `createServerClient` for middleware), S3 (the policy surface the
bookshelf and reader read through).

**Resolves:** `ROUTE_MAP.md` §Appendix C's student-session-persistence open question — decided in
S2 (cookie), routed here.

### Amendments proposed to the docket

1. **Teacher-initiated password reset moves from S4 to `teacher-dashboard`** (§6.4). It needs the
   roster picker that lives on the student-management screen S4 excludes.

### Open

- **Classrooms and students are hand-provisioned** until `teacher-dashboard` lands (§6.4). The login
  flow S4 ships is complete but unreachable without a seeded row.
- **The `sb-role` cookie remains the named upgrade path** if the wrong-role empty states prove
  confusing in classroom testing (§2). It is additive and reversible.
- **`getClaims()` with asymmetric JWT signing keys** removes middleware's per-navigation round-trip
  (§4). It is an infra change under AGENTS.md §2 and §7, and needs its own decision.
- **`ROUTE_MAP.md` is `status: draft` and now diverges from this spec in four places** (§3.2).
  Whether it survives as a spec or is absorbed into the specs it describes is a doc-hygiene question
  no session in this docket owns — it stays on the docket's parked list.
