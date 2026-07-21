# StoryBuddy — Route Map & Navigation Architecture

**Status:** draft · **Phase:** 2 · **Owner:** `frontend/app/`
**Derived from:** MASTER_SPEC §4 (rendering strategy), PRD §7 (user flow), USER_FLOW.md (nav patterns), DESIGN.md (layout/theme)
**Companion:** `docs/specs/USER_FLOW.md` (UX decisions & interaction patterns)

> This spec defines every URL in the app, which layout shells wrap them, which nav
> components appear at each breakpoint, how routes are protected, and what loading/transition
> behavior each route uses. It is the single source of truth for frontend routing decisions.
>
> **Rule:** Never use modals for primary navigation flows (USER_FLOW §2). Full-screen flows
> (write, process, book reader) hide all chrome — the user is "inside" the experience.

---

## 1. Route Tree

All routes are Next.js App Router filesystem routes under `frontend/app/`.

### Public routes (no auth required)

| URL pattern | Page | Rendering | Notes |
|---|---|---|---|
| `/` | Landing page | **SSR** (SEO) | Teacher-facing pitch, sign up / log in CTAs |
| `/login` | Auth — login | Client | Supabase Auth UI (teacher / BEED student) |
| `/signup` | Auth — signup | Client | Teacher / BEED-student account creation |
| `/join` | Student login | Client | Public — no Supabase auth. Classroom code entry, then nickname + password (teacher-issued) |
| `/join/[code]` | Direct join via link | Client | Pre-fills the classroom code; still requires nickname + password. Teacher shares this URL |

### Teacher routes (require Supabase Auth session)

| URL pattern | Page | Rendering | Notes |
|---|---|---|---|
| `/dashboard` | Teacher home | Client | Grid of classroom cards + "Create Classroom" CTA |
| `/classroom/[classroomId]` | Classroom detail | Client | Student list, classroom code, settings |
| `/classroom/[classroomId]/students` | Student management | Client | Add/edit/remove student profiles |
| `/classroom/[classroomId]/library` | Story library | Client | All stories in this classroom. Status badges (Needs Review / Approved) |
| `/classroom/[classroomId]/library/[bookId]` | Story review | Client | Full-screen overlay — teacher reads & approves |
| `/classroom/[classroomId]/gallery` | Classroom gallery (teacher view) | Client | Same gallery students see, but with moderation controls |
| `/classroom/[classroomId]/settings` | Classroom settings | Client | Rename, danger zone (delete). No review-gate toggle — teacher approval is always manual (auto-approve deferred to Future Work, ADR-017) |
| `/settings` | Teacher account settings | Client | Profile, password, account deletion |

### Student routes (require a valid student login — not Supabase Auth)

All student routes are prefixed with `/s/[profileId]/`. `profileId` identifies the child's own
teacher-issued account and is validated against Supabase via RLS — it must belong to a classroom the
teacher added it to. Auth is a real login (classroom code + nickname + password set by the teacher, changeable
by the child), just not the Supabase Auth session teachers use — session is established on successful login.

| URL pattern | Page | Rendering | Notes |
|---|---|---|---|
| `/s/[profileId]` | Student home (Bookshelf) | Client | Past stories as book covers + "Write a New Story!" CTA |
| `/s/[profileId]/write` | Story editor | Client | **Full-screen wizard** — nav hidden. Large textarea, live word count |
| `/s/[profileId]/write/style` | Style preset picker | Client | Part of the write wizard flow. 3 large tappable image cards |
| `/s/[profileId]/process/[jobId]` | Processing view | Client | **Full-screen** — no nav. Staged progress via Supabase Realtime |
| `/s/[profileId]/process/[jobId]/reveal` | Character reveal | Client | Shows moderated canonical character ref(s). Confirm / "try again" |
| `/s/[profileId]/book/[bookId]` | Storybook reader | Client | **Immersive full-screen**. Image + caption + narration. Next/prev |
| `/s/[profileId]/gallery` | Classroom gallery | Client | Browse & read classmates' approved books. Display-only — no reflection surface |
| `/s/[profileId]/gallery/[bookId]` | Peer book reader | Client | Same reader component, but for a classmate's book. Read-only |
| `/s/[profileId]/settings` | Student account settings | Client | Change password. No email, no self-serve recovery — reset otherwise is teacher-initiated |

---

## 2. Layout Nesting

Next.js App Router nested layouts. Each layout is a `layout.tsx` that wraps its children.

```
app/
├── layout.tsx                          # RootLayout — html/body, fonts (Outfit, Nunito, Inter),
│                                       # theme provider, Supabase client init, Sentry
├── (marketing)/
│   ├── layout.tsx                      # MarketingLayout — minimal header + footer, SSR-safe
│   └── page.tsx                        # Landing page (/)
│
├── (auth)/
│   ├── layout.tsx                      # AuthLayout — centered card, no nav chrome
│   ├── login/page.tsx                  # /login
│   ├── signup/page.tsx                 # /signup
│   └── join/
│       ├── page.tsx                    # /join
│       └── [code]/page.tsx            # /join/[code]
│
├── (teacher)/
│   ├── layout.tsx                      # TeacherShell — sidebar (desktop) / bottom-sheet nav (mobile)
│   │                                   # + breadcrumbs (desktop) + top app bar (mobile)
│   ├── dashboard/page.tsx              # /dashboard
│   ├── settings/page.tsx               # /settings
│   └── classroom/[classroomId]/
│       ├── layout.tsx                  # ClassroomLayout — adds breadcrumb segment
│       ├── page.tsx                    # /classroom/[classroomId]
│       ├── students/page.tsx
│       ├── library/
│       │   ├── page.tsx
│       │   └── [bookId]/page.tsx       # Full-screen overlay (breaks out of TeacherShell)
│       ├── gallery/page.tsx
│       └── settings/page.tsx
│
├── (student)/
│   └── s/[profileId]/
│       ├── layout.tsx                  # StudentShell — bottom tab bar (mobile) / top navbar (desktop)
│       ├── page.tsx                    # /s/[profileId] (Bookshelf/Home)
│       ├── settings/page.tsx           # /s/[profileId]/settings (password change)
│       ├── gallery/
│       │   ├── page.tsx                # /s/[profileId]/gallery
│       │   └── [bookId]/page.tsx       # Peer reader (uses ImmersiveLayout) — read-only
│       │
│       ├── (immersive)/
│       │   ├── layout.tsx              # ImmersiveLayout — NO nav chrome, full-screen
│       │   ├── write/
│       │   │   ├── page.tsx            # /s/[profileId]/write
│       │   │   └── style/page.tsx      # /s/[profileId]/write/style
│       │   ├── process/[jobId]/
│       │   │   ├── page.tsx            # /s/[profileId]/process/[jobId]
│       │   │   └── reveal/page.tsx     # /s/[profileId]/process/[jobId]/reveal
│       │   └── book/[bookId]/
│       │       └── page.tsx            # /s/[profileId]/book/[bookId]
│       │
│       └── (immersive)/layout.tsx      # (same as above — listed for clarity)
```

### Layout responsibilities

| Layout | Responsibility | Mounts nav? |
|---|---|---|
| `RootLayout` | `<html>`, fonts, theme provider, Supabase client, Sentry, `<Toaster>` | No |
| `MarketingLayout` | Minimal marketing header (logo + CTA) + footer | Yes (static) |
| `AuthLayout` | Centered card container, no nav | No |
| `TeacherShell` | Auth guard, sidebar/bottom-sheet nav, breadcrumbs, teacher-density typography | Yes |
| `ClassroomLayout` | Pushes classroom name into breadcrumbs; no extra nav | No (inherits) |
| `StudentShell` | Profile guard, bottom tab bar / top navbar, kid-density typography (Nunito 18/20px) | Yes |
| `ImmersiveLayout` | Strips all nav chrome. Optional top-left back button (ghost). Full viewport | No |

---

## 3. Navigation Components by Breakpoint

### Teacher routes (inside `TeacherShell`)

| Breakpoint | Nav component | Position | Items |
|---|---|---|---|
| Mobile (<768px) | `TopAppBar` + `BottomSheetDrawer` | Top fixed + sheet overlay | Page title in bar; hamburger opens drawer with: Dashboard, Classrooms, Settings, Log out |
| Tablet (768–1023px) | `CollapsibleSidebar` | Left, icon-only by default | Same items as mobile drawer; expands on hover/click |
| Desktop (≥1024px) | `PersistentSidebar` + `Breadcrumbs` | Left fixed (240px) + top header | Sidebar: Dashboard, Classrooms, Settings, Log out. Breadcrumbs in header: `Dashboard > Grade 5 > Library` |

### Student routes (inside `StudentShell`)

| Breakpoint | Nav component | Position | Items |
|---|---|---|---|
| Mobile (<768px) | `BottomTabBar` | Bottom fixed (56px) | 3 tabs: Home (📚), Gallery (🖼️), Profile (👤). Icons + text labels |
| Desktop (≥768px) | `TopNavbar` | Top fixed (64px) | Logo left, nav links center (Home, Gallery), profile avatar + nickname right |

### Immersive routes (inside `ImmersiveLayout`)

| Breakpoint | Nav component | Position | Items |
|---|---|---|---|
| All | `GhostBackButton` (conditional) | Top-left, absolute, semi-transparent | Single ← button. Only shown on write and process pages. Hidden on book reader (uses in-content controls) |
| All (book reader only) | `ReaderControls` | Overlay on tap / bottom fixed | Next/prev tap zones (left/right 30%), page indicator, play/pause narration, close (×) |

---

## 4. Protected vs Public Routes

### Auth levels

| Level | Mechanism | Redirect on failure |
|---|---|---|
| **Public** | None | — |
| **Auth (teacher)** | Supabase Auth session cookie | → `/login?next=<current>` |
| **Profile (student)** | Successful classroom-code + nickname + password login; valid `profileId` in a classroom (checked via Supabase RLS) | → `/join` |
| **Classroom-scoped** | Teacher must own the classroom; student account must belong to it | → `/dashboard` (teacher) or `/join` (student) |

### Route protection matrix

| Route pattern | Auth level | Additional guard |
|---|---|---|
| `/` | Public | — |
| `/login`, `/signup` | Public | Redirect to `/dashboard` if already authenticated |
| `/join`, `/join/[code]` | Public | — |
| `/dashboard` | Auth (teacher) | — |
| `/classroom/[classroomId]/**` | Auth (teacher) | Classroom-scoped: teacher must own this classroom |
| `/settings` | Auth (teacher) | — |
| `/s/[profileId]/**` | Profile (student) | Profile session must be active (stored in sessionStorage or cookie). Profile must exist and belong to an active classroom |
| `/s/[profileId]/gallery/[bookId]/**` | Profile (student) | `bookId` must be in the same classroom as `profileId` AND `teacher_approved = true` |
| `/s/[profileId]/book/[bookId]/**` | Profile (student) | `bookId` must belong to `profileId` (own book) |

### Middleware strategy

A single `middleware.ts` at `frontend/middleware.ts`:
1. **Teacher auth check** — for `/dashboard`, `/classroom/**`, `/settings`: verify Supabase session; redirect to `/login` if absent.
2. **Student profile check** — for `/s/[profileId]/**`: verify profile session exists; redirect to `/join` if absent.
3. **No server-side data fetching in middleware** — only session/cookie validation. RLS handles data-level authorization.

---

## 5. Route Transition Animations

Use `motion` (Framer Motion) for page transitions. Respect `prefers-reduced-motion`.

### Direction conventions

| Transition type | Animation | Duration | Easing |
|---|---|---|---|
| **Forward** (deeper in hierarchy) | Slide left + fade in | 250ms | `ease-out` (spring for kid routes) |
| **Backward** (shallower) | Slide right + fade in | 250ms | `ease-out` |
| **Lateral** (sibling tab switch) | Cross-fade only | 200ms | `ease-in-out` |
| **Immersive entry** (→ write/process/book) | Scale up from center + fade | 300ms | Spring `{ stiffness: 300, damping: 30 }` |
| **Immersive exit** (← back to shell) | Scale down to center + fade | 250ms | `ease-in` |
| **Full-screen overlay** (teacher story review) | Slide up from bottom | 300ms | Spring |

### Shared-element transitions (stretch — implement if time allows)

| Element | From → To | Behavior |
|---|---|---|
| Book cover thumbnail | Bookshelf → Book reader | Thumbnail expands to fill reader viewport |
| Character ref image | Reveal → Book reader page 1 | Morphs into the first scene containing that character |
| Gallery card | Gallery grid → Peer reader | Card expands to reader |

> **Implementation note:** Use `layoutId` from Framer Motion for shared-element transitions.
> If browser support for View Transitions API is sufficient at build time, prefer it instead.

---

## 6. Back Button Behavior Matrix

"Back" = browser back button, Android back gesture, or the in-app ghost back button.

| Screen | Back destination | State preserved? | Confirmation dialog? | Notes |
|---|---|---|---|---|
| `/` (landing) | Browser history | N/A | No | — |
| `/login` | `/` | No | No | — |
| `/signup` | `/login` | No | No | — |
| `/join` | `/` | No | No | — |
| `/dashboard` | `/` | Yes (cached) | No | — |
| `/classroom/[id]` | `/dashboard` | Yes | No | — |
| `/classroom/[id]/library` | `/classroom/[id]` | Yes | No | — |
| `/classroom/[id]/library/[bookId]` | `/classroom/[id]/library` | Yes | No | Closes full-screen overlay |
| `/classroom/[id]/students` | `/classroom/[id]` | Yes | No | — |
| `/classroom/[id]/settings` | `/classroom/[id]` | Yes | No | Unsaved changes → confirm dialog |
| `/settings` | `/dashboard` | Yes | No | Unsaved changes → confirm dialog |
| `/s/[pid]` (bookshelf) | `/join` | No | **Yes** — "Leave classroom?" | Ends profile session |
| `/s/[pid]/write` | `/s/[pid]` | **No** — draft lost | **Yes** — "Your story isn't saved yet" | Critical: prevent accidental loss |
| `/s/[pid]/write/style` | `/s/[pid]/write` | Yes (story text kept) | No | — |
| `/s/[pid]/process/[jobId]` | `/s/[pid]` | N/A (job continues) | **Yes** — "Your book is still being made!" | Job runs regardless; user can return later |
| `/s/[pid]/process/[jobId]/reveal` | `/s/[pid]/process/[jobId]` | Yes | No | Can go back to re-see progress |
| `/s/[pid]/book/[bookId]` | `/s/[pid]` | Yes (page position) | No | Returns to bookshelf |
| `/s/[pid]/gallery` | `/s/[pid]` (via tab) | Yes | No | Lateral tab switch |
| `/s/[pid]/gallery/[bookId]` | `/s/[pid]/gallery` | Yes | No | Read-only, display-only |
| `/s/[pid]/settings` | `/s/[pid]` | No | Unsaved changes → confirm dialog | Password change |

---

## 7. Deep Linking Requirements

Which routes must be shareable/bookmarkable (copy-paste URL into another tab and it works):

| Route | Deep-linkable? | Who shares it? | Notes |
|---|---|---|---|
| `/` | ✅ Yes | Anyone | Marketing page |
| `/join/[code]` | ✅ Yes | Teacher → students | Teacher shares this link (or the code) so students can join |
| `/dashboard` | ✅ Yes | — | Redirects to login if unauthenticated |
| `/classroom/[id]` | ✅ Yes | Teacher bookmarks | — |
| `/classroom/[id]/library` | ✅ Yes | Teacher bookmarks | — |
| `/classroom/[id]/library/[bookId]` | ✅ Yes | Teacher bookmarks | — |
| `/s/[profileId]` | ⚠️ Partial | — | Works only if profile session is active; otherwise → `/join` |
| `/s/[pid]/book/[bookId]` | ⚠️ Partial | — | Same — requires active session. **Not shareable outside the app** (by design: no public sharing, ADR-017) |
| `/s/[pid]/write` | ❌ No | — | Wizard state is ephemeral |
| `/s/[pid]/process/[jobId]` | ⚠️ Partial | — | Can return to a running/completed job if session is active |

### URL design rules
- **No PII in URLs.** `profileId` is a UUID, not a name. Classroom codes are random alphanumeric.
- **Stable IDs.** `bookId`, `jobId`, `classroomId` are Supabase UUIDs — immutable and collision-free.
- **No query params for navigation state.** Use URL segments. Query params are reserved for filters (`?status=needs_review`) and pagination (`?page=2`).

---

## 8. Loading States per Route

Every route group gets a `loading.tsx` that renders before the page component hydrates / fetches data.

### Skeleton conventions

| Route group | Skeleton shape | Animation | Typography |
|---|---|---|---|
| **Landing** (`/`) | Full page — hero image placeholder + CTA button skeletons | Subtle shimmer (left-to-right gradient) | — |
| **Auth** (`/login`, `/signup`, `/join`) | Centered card with input field placeholders | Pulse opacity | — |
| **Teacher Dashboard** | 2×2 grid of classroom card skeletons (rounded-xl, neo-shadow) | Shimmer | Inter |
| **Classroom detail** | Header skeleton + student list (6 row placeholders) | Shimmer | Inter |
| **Story library** | Header + 3 story card skeletons with status badge placeholder | Shimmer | Inter |
| **Story review** (teacher) | Full-screen: image placeholder (60% height) + text block (40%) | Shimmer | Inter |
| **Student Bookshelf** | Horizontal carousel of 3 book-cover skeletons (aspect 3:4) + bottom CTA skeleton | Shimmer + subtle bounce on covers | Nunito |
| **Student Write** | Full-screen: large textarea skeleton + floating button skeleton | Pulse | Nunito |
| **Processing** | Full-screen: centered Lottie animation (book pages flipping). No skeleton — the Lottie *is* the loading state | Lottie loop | Nunito, large |
| **Character Reveal** | Centered card skeleton with image placeholder (1:1 aspect) + 2 button skeletons below | Shimmer | Nunito |
| **Book Reader** | Full-screen: image placeholder (top 60%) + 2 text-line skeletons (bottom) + page indicator dot | Fade in | — |
| **Gallery** | Masonry grid (desktop) / vertical stack (mobile) of 4 book-card skeletons | Shimmer | Nunito |

### Loading state rules
1. **Skeletons match content shape** — reserve exact layout space to prevent CLS (DESIGN.md §5).
2. **Kid routes use Lottie micro-narratives** inside skeletons when appropriate (pencil scribbling, wand spinning).
3. **Teacher routes use shimmer** — clean, fast, no distraction.
4. **Never show a blank white page** — every route group must have a `loading.tsx`.
5. **Buttons disable + show spinner** during async operations (form submissions, approvals).
6. **Processing route is special** — it's the *only* route where the loading state *is* the page content (Supabase Realtime drives the progress stepper; the user watches it animate to completion).

### Error boundaries

Each route group also gets an `error.tsx`:

| Route group | Error behavior | Design |
|---|---|---|
| Teacher routes | "Something went wrong" card + "Try again" button + link to dashboard | Clean, Inter, Comic Red left-border (DESIGN.md) |
| Student routes | Friendly confused mascot + "Oops! Let's go back and try again" + big button | Cartoon-pop, Nunito, warm, non-scary |
| Immersive routes | Overlay error card + "Go to Bookshelf" button | Transparent backdrop, centered card |

---

## Appendix A: URL Quick Reference (alphabetical)

```
/                                           Landing (SSR, public)
/classroom/[classroomId]                    Classroom detail (teacher)
/classroom/[classroomId]/gallery            Classroom gallery — teacher view (teacher)
/classroom/[classroomId]/library            Story library (teacher)
/classroom/[classroomId]/library/[bookId]   Story review (teacher)
/classroom/[classroomId]/settings           Classroom settings (teacher)
/classroom/[classroomId]/students           Student management (teacher)
/dashboard                                  Teacher home (teacher)
/join                                       Student login — classroom code + nickname + password (public)
/join/[code]                                Direct join link, code pre-filled (public)
/login                                      Login (public, teacher/BEED student)
/s/[profileId]                              Student bookshelf (student)
/s/[profileId]/book/[bookId]                Storybook reader (student)
/s/[profileId]/gallery                      Classroom gallery (student)
/s/[profileId]/gallery/[bookId]             Peer book reader, read-only (student)
/s/[profileId]/process/[jobId]              Processing view (student)
/s/[profileId]/process/[jobId]/reveal       Character reveal (student)
/s/[profileId]/settings                     Password change (student)
/s/[profileId]/write                        Story editor (student)
/s/[profileId]/write/style                  Style preset picker (student)
/settings                                   Teacher account settings (teacher)
/signup                                     Signup (public, teacher/BEED student)
```

---

## Appendix B: Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-4 Security (RLS + signed URLs)** — Every student route is profile-scoped via RLS. Gallery reads are classroom-scoped + teacher-approved only. No book leaves the container except as a PDF export (ADR-017).
- [x] **CC-6 Accessibility** — Large touch targets (44×44px min) in student nav. Text labels on all tab bar icons. Narration play button prominently placed in reader controls.
- [x] **CC-8 Kid vs teacher design language** — Two distinct layout shells with different typography (Nunito vs Inter), density, and component libraries.
- [x] **CC-9 Failure states = success states** — Every route group has a designed `error.tsx` with age-appropriate messaging. Processing stalls get a friendly checkpoint message, not a raw error.
- [ ] CC-1 Moderation ordering — N/A (routing layer; moderation is pipeline-side)
- [ ] CC-2 PII redaction — N/A (no PII in URLs; `profileId` is a UUID)
- [ ] CC-3 Cost control — N/A
- [ ] CC-5 Observability — N/A (handled at Sentry/LangSmith level)
- [ ] CC-7 Reproducibility — N/A
- [ ] CC-10 Checkpointing — N/A (process route *displays* checkpoint state but doesn't own it)

---

## Appendix C: Linked decisions & open questions

### Linked ADRs / PRD sections
- **ADR-005** — Job checkpointing drives the `/process/[jobId]` route's resume behavior
- **ADR-006, ADR-017** — RLS + classroom scoping drives the protection matrix
- **ADR-021** — Display-only gallery routing; no reflection surface
- **PRD §7** — User flow steps 1–14 map to routes 1:1
- **PRD §9** — Divergent design registers (kid vs teacher)
- **MASTER_SPEC §4** — Rendering strategy (SSR landing, client everything else)

### Open questions
- ⚠️ **Shared-element transitions** — feasibility depends on View Transitions API support in target browsers (Chrome 111+, Safari 18+). If unsupported, fall back to scale/fade transitions.
- ⚠️ **Student session persistence** — `sessionStorage` (tab-scoped, dies on close) vs a short-lived cookie (survives refresh). Cookie is better UX but raises the question of session expiry policy. Decision needed before `auth-and-classroom` spec.
- ⚠️ **Landscape lock on mobile book reader** — `screen.orientation.lock('landscape')` requires a fullscreen context and is not supported on iOS Safari. May need to show a "rotate your device" prompt instead. Verify at build time.
