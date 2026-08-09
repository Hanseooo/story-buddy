# Feature Spec — student-customization

**Status:** draft · **Phase:** 2 · **Owner:** `frontend/app/s/[profileId]/settings/` + `PATCH /me/avatar`
**Derived from:** MASTER_SPEC §7 (frontend rows) · **Rationale:** PRD §4, ADR-017 (auth boundary)

> Frontend row plus one FastAPI route. The template's §2/§3 are pipeline sections and do not
> apply — this module touches no LangGraph node and no Story Memory field.

## 1. Purpose

Let a child choose an avatar, so the identity they carry across the app is one they picked rather
than the first letter of a nickname their teacher typed. The avatar is the second thing a child
owns in this product (the first is their story) and the only thing they can change about
themselves.

Scope is deliberately one axis. No display-name editing (the teacher owns `display_nickname`),
no themes, no per-book customization.

## 2. What already exists (this row builds none of it)

| Layer | Where | State |
|---|---|---|
| Settings route | `/s/[profileId]/settings` | built — password + logout only |
| Letter avatar | `classroom/[classroomId]/page.tsx:212` | built — `display_nickname.charAt(0)` |
| Profile reads | `0008:89-113` five SELECT policies on `profiles` | live |
| Student auth | `get_current_user` (`backend/app/auth.py:6`) | built |
| Gallery author join | `gallery/page.tsx:29` `profiles!inner(display_nickname)` | built |

## 3. Data model

**Migration `0009`** — one column, nullable, no backfill:

```sql
alter table profiles add column avatar_id text;
```

- **Null is the default and stays meaningful:** it renders the existing letter avatar. Every
  profile that exists today is already correct, and a child who never opens settings is never in
  a broken state.
- **No policy change.** RLS policies in `0008` are column-agnostic; every role that can already
  `select` a profile row can read the new column. Teachers read their classroom's profiles
  (`0008:101`), students read their classmates' (`0008:93`).
- **No CHECK constraint.** The allowed set is expected to change as the avatar set is curated, and
  a CHECK would make every curation change a migration. Validation lives at the two boundaries in
  §6 instead.

## 4. The avatar set

24 avatars, committed as static SVGs under `frontend/public/avatars/`, generated at build time
from an explicit manifest in `frontend/scripts/generate-avatars.mjs`.

| Style | Count | License | Why |
|---|---|---|---|
| Open Peeps | 6 | CC0 1.0 | Hand-drawn humans; real 5-tone skin ladder |
| Pixel Art | 6 | CC0 1.0 | Game-sprite look; 8-tone skin ladder |
| Lorelei | 6 | CC0 1.0 | Line-art faces; distinct visual voice |
| Thumbs | 6 | CC0 1.0 | Abstract — the non-face option |

**Every style is CC0 1.0 — no attribution obligation.** DiceBear licenses per *style*, not per
library. Adding a CC BY style (`adventurer`, `big-smile`, `croodles`, `fun-emoji`, `dylan`,
`micah`, `miniavs`, `personas`, `toon-head`) requires also building an attribution surface; the
generator carries this warning in its header.

**Constraints discovered while building the generator, recorded so they are not rediscovered:**

- `@dicebear/collection` on npm is **9.4.2**. The `critters`, `sprouts`, and `moods` styles listed
  on dicebear.com are v10 and **are not installable**. The website catalog is not the menu.
- `@dicebear/core` must be pinned to `^9.0.0`. Installing `latest` pulls 10.x, which
  `collection@9` does not accept.
- **Lorelei's `skinColor` defaults to `["ffffff"]`** — it is a line style, not a filled one. Tone
  must be pinned explicitly; it does not follow from the seed.

**Generation is build-time only.** `@dicebear/*` are devDependencies and never enter the client
bundle. The manifest pins a seed plus deliberate overrides per entry — `skinColor` is pinned
rather than left to the seed, so the spread across tones is guaranteed rather than incidental.
Regeneration is deterministic: the same manifest always produces byte-identical files.

The script also emits `public/avatars/index.html`, a numbered contact sheet used to review the set
before it ships. It is a build artifact, not a route.

**The script emits `frontend/lib/avatars.ts`** — the id list, marked generated-do-not-edit. This is
what the renderer's allowlist reads, so the allowlist cannot drift from what is on disk.

> **Build state:** the generator and the 24 SVGs already exist — they were built during the design
> session so the set could be reviewed before being specced. Emitting `lib/avatars.ts` is the one
> part of §4 still to do. Everything in §3 and §5–§8 is unbuilt.

## 5. Routes

| Route | Kind | Notes |
|---|---|---|
| `PATCH /me/avatar` | FastAPI | **New.** Body `{"avatar_id": "peeps-01" \| null}`. |
| `/s/[profileId]/settings` | Client | **Changed.** Gains the avatar picker above the password form. |

`PATCH /me/avatar` mounts on the main `app`, **not** `teacher_router` — that router carries
`Depends(require_teacher)` (`auth.py:52`) and would 403 every student. It is guarded by
`get_current_user` and writes only `auth.uid()`'s own row.

`ROUTE_MAP.md` gains the route in the same change.

## 6. Behavior

### 6.1 Why a route exists at all

`0008:85` states it plainly: *"No INSERT/UPDATE/DELETE: profile creation is trigger-only; updates
go through FastAPI."* A child has no UPDATE policy on `profiles` and must not be given one — that
would be an authorization-surface change, which is S3's territory, not this row's. The route is
the cheapest way to honor the existing boundary rather than widen it.

### 6.2 Two-layer validation

`avatar_id` reaches a URL path segment, so an unvalidated column is arbitrary-path injection on a
child-facing page. Both layers are required:

1. **At the endpoint** — reject anything not matching `^(peeps|pixel|lorelei|thumbs)-\d{2}$` with a
   422. Closed enough to kill traversal, `javascript:`, and protocol-relative URLs.
2. **At render** — index `AVATAR_IDS` from `lib/avatars.ts`. A value that passes the regex but has
   no file (`peeps-99`) falls back to the letter avatar rather than emitting a broken image.

The regex-plus-allowlist split is deliberate: it keeps the id set out of the backend entirely, so
curating the avatar set never requires a backend change or a cross-project generated file that can
drift. The cost is that a forged-but-well-formed id is caught at render rather than at write — an
outcome whose worst case is the child seeing their letter avatar.

### 6.3 The picker

The settings page stops being a single password form. Order: **avatar section, password section,
logout.** The avatar is what the child came for; the password is what the teacher tells them to
change.

- 4×6 grid of avatars, grouped by style with no visible style labels — a child picks a picture,
  not a library.
- Current selection carries a visible ring, not just color, and is the checked radio.
- Tapping writes optimistically and fires `PATCH /me/avatar`. On failure, revert and show the
  existing inline message pattern.
- "Use my letter instead" clears back to null. Reachable, not prominent.

### 6.4 Render surfaces

One shared component, `components/Avatar.tsx`, takes `avatarId` and `displayNickname` and renders
either the SVG or the existing letter circle. The fallback exists in exactly one place.

| Surface | File | Change |
|---|---|---|
| Student's own header | `s/[profileId]/layout.tsx:75` | Add avatar beside "Hi, {name}!"; `select` gains `avatar_id` |
| Gallery author byline | `gallery/page.tsx:65` | Embed gains `avatar_id`; the `!inner` join is unchanged |
| Teacher roster rows | `classroom/[classroomId]/page.tsx:212` | Replaces the inline letter circle |
| Teacher BookCard | `components/BookCard.tsx:11` | Beside the author name |
| Teacher ReviewDialog | `components/BookReviewDialog.tsx:38` | Beside the author name |

Every one of these already selects from `profiles`; each adds one column to an existing query. **No
new round trips** — the server-layout-owns-its-data invariant applies unchanged.

## 7. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-4 Security** — no new RLS policy; write path is the existing FastAPI boundary; two-layer
      id validation (§6.2) because the value becomes a URL segment.
- [x] **CC-6 Accessibility** — picker is a radio group, not a div grid; each option ≥44px with an
      accessible name ("Avatar 3 of 24"); selection is ringed, never color-only. Avatar images are
      `alt=""` on every surface — the name is always adjacent, so alt text would double-announce.
- [x] **CC-8 Kid vs parent design** — the picker is the child surface (pictures, no labels, no
      jargon); the teacher surfaces are read-only.
- [x] **CC-9 Failure states = success states** — a failed PATCH reverts visibly and explains; an
      unknown id degrades to the letter avatar rather than a broken image.
- [ ] CC-1, CC-2, CC-3, CC-5, CC-7, CC-10 — N/A. No model call, no generated content, no user text,
      no pipeline state.

## 8. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

**Backend (`pytest`, Supabase client mocked):**
1. `PATCH /me/avatar` with a valid id → 200, updates only the caller's row.
2. Invalid ids → 422: `../../etc/passwd`, `peeps-1` (one digit), `PEEPS-01`, `javascript:alert(1)`,
   `//evil.com/x`, empty string.
3. `{"avatar_id": null}` → 200, clears the column.
4. No `Authorization` header → 401.
5. The write targets `auth.uid()` — a body carrying another profile's id cannot redirect the write.

**Frontend (`vitest`):**
6. `Avatar` with `avatarId={null}` renders the letter circle.
7. `Avatar` with an id absent from `AVATAR_IDS` renders the letter circle, not an `<img>`.
8. `Avatar` with a valid id renders `<img src="/avatars/{id}.svg">` and `alt=""`.
9. Settings renders 24 options as a radio group with the current one checked.
10. Tapping an option fires `PATCH /me/avatar` with a bearer token — the assertion that would have
    caught the `/write` bug this row's session uncovered.
11. A failed PATCH reverts the selection and surfaces a message.
12. **Manifest integrity:** every id in `AVATAR_IDS` has a matching file in `public/avatars/`, and
    the counts match. Catches a manifest edit that was never regenerated.

## 9. Eval / quality checks

N/A. No generated content, no model call, nothing fuzzy to measure.

## 10. Linked decisions & open questions

- Depends on `0008`'s policy surface (SELECT-only on `profiles`) and its stated update path.
- Next free migration is **`0009`** per AGENTS.md; this row claims it.
- **Open — not blocking:** no animal or plant avatars are available under CC0 in the installable
  package. If the set should include animals, the options are the DiceBear HTTP API (rejected here:
  third-party request from a child-facing page) or drawing them. Deferred until a real classroom
  asks.
- **Out of scope, noted during exploration:** `POST /storybooks` accepts `style_preset_id` and
  `docs/specs/style-presets.md` exists, but `write/page.tsx` never sends one. That surface is
  unbuilt and belongs to its own row.
