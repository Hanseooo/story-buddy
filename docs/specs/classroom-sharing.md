# Feature Spec — classroom-sharing

**Status:** draft · **Phase:** 2 · **Owner:** `frontend/app/s/[profileId]/gallery/` (no backend, no pipeline node)
**Derived from:** MASTER_SPEC §7 (frontend rows) · **Rationale:** ADR-021, ADR-017, PRD §11 / §4 (feature 11)

> Frontend-only row. The template's §2/§3 are pipeline sections and do not apply — this module
> touches no LangGraph node and no Story Memory field.

## 1. Purpose

The display-only classroom gallery: a grid of the approved storybooks in the child's classroom,
opening into the existing reader. It closes the end-to-end loop — teacher creates classroom →
student writes → teacher approves → peers see the book.

ADR-021 defines the whole feature surface: **the storybook is the only peer-visible artifact.**
No reflection prompt, comment, reply, or scoring surface of any kind.

## 2. What already exists (this row builds none of it)

| Layer | Where | State |
|---|---|---|
| Peer-read policy | `0008:28` `students read approved peer jobs` — `classroom_id = auth_classroom_id() and approved_at is not null` | live |
| Storage policy | `0008` §7, classroom-scoped by joining back to `jobs` | live |
| Approval | `teacher-review-and-approval.md` — `approved_at` / `rejected_at`, `POST /jobs/{id}/review` | built |
| Book shape | `jobs.pages` ordered JSONB `{scene_id, caption, image_path}` (`0004`) | built |
| Reader | `/s/[profileId]/book/[jobId]` | built |
| Route slot | `/s/[profileId]/gallery`, frozen by auth S4-2 | reserved |

**No migration. No FastAPI route. No `backend/contracts/` change. No worker involvement.**

## 3. Routes

| Route | Kind | Notes |
|---|---|---|
| `/s/[profileId]/gallery` | **Server** component | New. The grid. |
| `/s/[profileId]/gallery/loading.tsx` | — | New. Required by the every-async-segment invariant. |
| `/s/[profileId]/book/[jobId]` | Client | **Unchanged.** Already renders any row RLS lets the child read. |

`/s/[profileId]/gallery/[bookId]` is **not built** — the existing reader serves peer books at the
same URL shape a child already uses for their own. `ROUTE_MAP.md:58` and `:338` are dropped in §8.

## 4. Behavior

### 4.1 The query

```ts
supabase
  .from("jobs")
  .select("id, approved_at, pages, profile_id, profiles(display_nickname)")
  .not("approved_at", "is", null)
  .order("approved_at", { ascending: false })
  .limit(60);
```

- **The `approved_at` filter is not redundant with RLS.** `0008:24` `students read own jobs` grants
  the child *every* row they own, approved or not. Without the explicit filter, a child's own
  unapproved and rejected books appear in the gallery — the exact class of bug auth docket
  constraint **S4-4** exists to prevent. This is the assertion §6 pins down.
- **Classroom scoping comes from RLS, not from the query.** The peer policy already gates
  `classroom_id = auth_classroom_id()`. The page does not read `classroom_id` and must not
  re-derive it.
- **Own approved books are included.** No `.neq('profile_id', …)`. The gallery reads as the class's
  shelf, and the child sees their own work on it — the authentic-audience benefit ADR-021 names.
- **Ordering is `approved_at desc`, not `created_at`.** A child's book appears at the top the
  moment the teacher approves it, which is the moment that matters.
- **Cap 60, no pagination.** A classroom holds ≤60 students (`teacher-provisioning-and-shell.md`).
  Pagination arrives when a real class overflows the cap; it is the same one-line change either way.

### 4.2 Signing

One batched call, cover image only:

```ts
supabase.storage.from("storybook-images").createSignedUrls(paths, 3600);
```

⚠️ **The bucket is `storybook-images`.** `frontend/app/s/[profileId]/page.tsx:76` signs from
`"pages"`, which does not exist — see §9. Do not copy that line.

Cover = `pages[0].image_path`. A row with an empty `pages` array cannot occur (approval requires
`status='complete'`, which requires `pages`), but the card renders a neutral placeholder rather than
throwing if one does.

### 4.3 The card

Cover image + **`by {display_nickname}`**. Nothing else.

**`jobs.input_text` is never selected on this surface.** It is the raw, pre-Presidio column — a child
who wrote *"my tita Rosa in Purok 3"* has that text on a classmate's screen if it is used as a title.
The bookshelf uses it as a title for the child's *own* book, which is their own writing; the gallery
is the first surface where it would cross a child boundary, and it does not.

Captions were considered as a title source and rejected: ADR-013 froze `caption = text_excerpt`, so a
caption is a scene line, not a book name.

### 4.4 Rendering

`page.tsx` is an async server component using `createServerClient` from `@supabase/ssr`, matching
`app/s/[profileId]/layout.tsx`. Cards are plain server JSX wrapping `<Link>`. Consequences:

- **No client component, no `useEffect`, no Realtime subscription.** Freshness is per navigation —
  tapping the Gallery tab re-renders. A teacher-paced surface does not need liveness.
- **No `motion`.** Transitions are CSS or absent (`auth-routes-and-account-ux.md:97`).
- This follows the AGENTS.md server-fetch invariant rather than the bookshelf's client-fetch drift
  (§9).

### 4.5 Empty state

> *"Your class's books will show up here."*

**Bound by `teacher-review-and-approval.md` §4.10 — this row adds no rejection signal.** The copy
carries no approval vocabulary ("waiting", "pending", "not approved yet"), no per-author slot, no
"why isn't mine here" affordance. A child whose book was rejected sees an absence with no verdict
attached to it, and still sees every book they made on their bookshelf. Changing this requires
amending that spec, not this one.

### 4.6 Un-approval during a session

A teacher un-approving a book the child is currently reading does not interrupt them: the signed URL
is already issued and lasts an hour. On the next navigation the row is gone from the gallery, and the
reader falls to `useJob`'s `not-found` bucket. No new state, no notification — consistent with §4.5.

## 5. Navigation

`components/StudentTabBar.tsx` — client component (`usePathname` for active state).

| Tab | Route | Icon + text label |
|---|---|---|
| Bookshelf | `/s/[profileId]` | 📚 |
| Gallery | `/s/[profileId]/gallery` | 🖼️ |
| Profile | `/s/[profileId]/settings` | 👤 |

`MOBILE_GUIDELINES.md:30` mandates a Bottom Tab Bar for the kid flow below 768px, max 3 items,
icon **and** text, and forbids mixed patterns. So:

- Fixed bottom, `md:hidden`, ≥44px targets, respects `env(safe-area-inset-bottom)`.
- The same three as links in the existing header at `md:` and up.
- **Log out moves from the layout header into `/settings`**, so the header carries identity and
  desktop nav only — one job per surface, per the no-mixed-patterns rule. `/settings` becomes a real
  Profile screen (password change + log out) rather than a link nothing points at.
- **The bookshelf's mobile write button lifts clear of the bar.** `app/s/[profileId]/page.tsx:153`
  is `fixed bottom-6` and would sit underneath it. Writing stays one thumb-tap away — it is the
  app's primary action.

This is the tab bar `auth-routes-and-account-ux.md:93` deferred by name: *"the tab bar arrives with
the gallery."*

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

`app/s/[profileId]/gallery/page.test.tsx`, Supabase client mocked:

1. Renders one card per approved row, each labelled with its author's `display_nickname`.
2. **A row with `approved_at: null` is excluded.** Unit tests do not exercise RLS, so this is the
   only place the §4.1 explicit filter is proven. Its absence is S4-4's failure mode.
3. Rows are ordered `approved_at` descending.
4. The query requests `limit(60)`.
5. A card links to `/s/{profileId}/book/{jobId}`.
6. Signed URLs are requested from bucket `storybook-images`.
7. `input_text` is not among the selected columns.
8. With zero rows, the empty state renders and contains none of `approved`, `pending`, `waiting`,
   `rejected`, `teacher`.

`components/StudentTabBar.test.tsx`:

9. Three tabs render, each with a text label beside its icon.
10. The tab matching the current pathname is marked `aria-current="page"`.

Backend: **no new tests.** This row adds no Python.

## 7. Eval / quality checks

N/A. The gallery generates no content. ADR-021: *"the gallery is a product feature, not a
measurement instrument"* — no evaluation leg depends on it.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-4 Security (RLS + signed URLs)** — reads ride `0008`'s peer policy; the query adds the
  `approved_at` filter RLS cannot express for a per-child list (S4-4); covers are signed, 1h, from a
  private bucket. No public surface, no link-based access (ADR-017).
- [x] **CC-2 PII redaction** — satisfied by omission: `input_text` is never selected (§4.3). Page
  images and captions already passed `input_gate`, `output_mod` and Presidio.
- [x] **CC-6 Accessibility** — ≥44px tab targets, text labels beside icons (not icon-only),
  `aria-current` on the active tab, alt text on covers.
- [x] **CC-8 Kid vs parent design** — kid surface: bottom tab bar, no approval vocabulary anywhere.
- [x] **CC-9 Failure states = success states** — the empty state is designed copy, not a blank grid
  (§4.5).
- [ ] CC-1, CC-3, CC-5, CC-7, CC-10 — not touched. No model calls, no cost, no job lifecycle.

## 9. Doc propagation (same change)

| File | Change |
|---|---|
| `docs/specs/ROUTE_MAP.md:39` | **Drop** `/classroom/[classroomId]/gallery`. `/classroom/[classroomId]/books` already covers it — classroom-scoped (`page.tsx:46` + the teacher RLS policy), full book contents readable before deciding (`BookReviewDialog` signs and renders every page), and its Approved tab *is* the gallery set. No second teacher surface. |
| `docs/specs/ROUTE_MAP.md:58`, `:338` | **Drop** `/s/[profileId]/gallery/[bookId]` — reader reused (§3). |
| `docs/specs/ROUTE_MAP.md:154`–`155` | Mark the tab bar built; correct the tab set to Bookshelf / Gallery / Profile. |
| `docs/specs/USER_FLOW.md:34` | Same correction — it says Home / Bookshelf / Gallery; `/s/[profileId]` *is* both home and bookshelf. |
| `docs/MASTER_SPEC.md:347` | `classroom-sharing` row → built. |
| `docs/product/DECISION_BACKLOG.md:268` | Tick the row; drop it from the priority stack. |
| `AGENTS.md` *Validation Notes* | One entry, in the existing style. |

## 10. Flagged, not fixed

Out of this row's scope (AGENTS.md *Surgical Changes*), surfaced rather than silently carried:

1. **`app/s/[profileId]/page.tsx:76` signs from bucket `"pages"`.** No such bucket —
   `storybook-images` everywhere else (`0001:28`, `providers.py:147`, the reader, the process page,
   teacher `/books`). Bookshelf covers fail to sign silently today; every card falls through to the
   emoji placeholder.
2. **`app/s/[profileId]/page.tsx:7` imports `motion/react`**, contradicting
   `auth-routes-and-account-ux.md:97` ("kid-flow rejected `motion` under AGENTS.md §2; transitions
   are CSS or absent"). Either the record or the code is wrong.
3. **`AGENTS.md` says the next free migration is `0009`.** `0009`–`0012` all exist. Next free is
   **`0013`**.
4. **The bookshelf is a client component fetching in `useEffect`**, against the AGENTS.md invariant
   that a server layout owns the data. This spec does not propagate the pattern; it does not fix it
   either.

## 11. Linked decisions & open questions

- **ADR-021** — display-only gallery; no reflection, comment, or scoring surface. Frozen.
- **ADR-017** — classroom-scoped, teacher-gated, manual approval only. No public or link-based access.
- **ADR-013** — `caption = text_excerpt`, which is why captions are not titles (§4.3).
- **auth S4-2** — route tree frozen; `classroom-sharing` extends under `/s/[profileId]/gallery`.
- **auth S4-4** — RLS does not scope a per-child list; the query must (§4.1).
- **`teacher-review-and-approval.md` §4.10** — no rejection signal, no absence badge, no
  "why isn't mine here" (§4.5). Binding.
- **`narration`** — the gallery reader ships without a play button. TTS is that row's deliverable.
- **Open:** none. Pagination past 60 and any peer-reader chrome are deliberate deferrals, not
  unresolved questions.
