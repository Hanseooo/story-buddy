# Feature Spec — Image loading UX (bookshelf, reader, picture endpoint)

**Status:** approved (OD-01 decided 2026-11-24) · **Phase:** Post technical defense · **Owner:**
`frontend/lib/signedUrls.ts`, `frontend/app/s/[profileId]/page.tsx`,
`frontend/app/s/[profileId]/book/[jobId]/page.tsx`, `backend/app/auth.py`,
`backend/app/moderation_hold.py` (`job_image` only)
**Derived from:** performance audit and grill, 2026-11-23 (this conversation; no ticket yet) ·
**Constrained by:** [ADR-080](../product/adr/ADR-080-teacher-held-moderation-and-exact-content-clearance.md)
§72-75 (no-store delivery, re-check before response, no signed links to children),
[ADR-025](../product/adr/ADR-025-provider-resilience-failure-mode-policy-d-c.md) (never a partial
book), ADR-033 (worker checkpointer connection), [`kid-flow-book-persistence.md`](kid-flow-book-persistence.md)
§4.4, [`kid-flow-reader-and-wait-states.md`](kid-flow-reader-and-wait-states.md) §4.3, §4.5

## 1. Purpose and scope

Opening the bookshelf and opening a book feel slow. The owner's goal is the child's experience of
loading, not a measured speed target. Success is judged by the owner's own observation.

Since 2026-11-21 new books are `teacher_review_v1` by default. Their pictures cannot use signed links
(ADR-080), so the browser downloads each one from `GET /jobs/{job_id}/images/{asset_id}`. Today:

- `signPaths` downloads those pictures **one after another** and reads the session once per picture
  (`frontend/lib/signedUrls.ts:63-89`).
- The bookshelf shows no card until every cover has downloaded (`app/s/[profileId]/page.tsx:105-118`).
  While it waits it shows only the heading, so the route skeleton (`loading.tsx`) is replaced by an
  empty shelf before the books appear.
- The reader waits for every page. If one page fails, the automatic retry downloads **every** page
  again (`book/[jobId]/page.tsx:764-787`).
- `get_current_user` is `async` but calls the blocking Supabase client (`backend/app/auth.py:6-34`).
  The web service is one uvicorn process (`Procfile:1`), so every other request waits during that
  call. Parallel picture requests would make this worse.
- `job_image` opens a new direct Postgres connection twice per picture (`moderation_hold.py:662,
  926,931`).

**Included:** US-01 to US-04 below.

**Excluded:**
- **Browser caching of protected pictures and signed links for them.** ADR-080 forbids both.
- **A batch "all covers" endpoint.** It would change the API, and US-04 already removes most of the
  per-request cost.
- **Cover thumbnails or WebP covers.** They would change pipeline assets.
- **`getClaims()` in the middleware, and the duplicate profile read in the student layout.** These
  are auth changes.
- **Loading the book state once in `job_image`.** Deferred to OD-02.
- **Lazy-loading covers below the fold.**
- **Changes to the teacher books page beyond what it inherits from `signPaths` (SH-01).**

**Acceptance journeys:**
1. A child with 12 books, 8 of them teacher-review, opens the bookshelf:
   - The skeleton shows until the book list arrives.
   - All 12 cards then appear with title and status.
   - Each cover pulses and then fades in as it arrives.
   - The child can tap any card before its cover arrives.
2. A child opens an 8-page teacher-review book. The pages download in parallel and the book appears
   once every page is ready. If one page fails, only that page is fetched again. If it fails again,
   the existing read-failure screen appears.

## 2. User stories and acceptance criteria

### US-01 — The shelf appears without a blank flash

As a child, I want to see my books as soon as the list is known, so that I can pick one without
waiting for every picture.

Applies: SH-01, SH-02, SH-03, SH-04

- **AC-01** — While the book list is loading, the bookshelf shows the same skeleton as the route
  loading file (`app/s/[profileId]/loading.tsx`). It never shows the heading over an empty grid.
- **AC-02** — Once the list arrives, every card renders right away with its title, status badge and
  link (SH-04), before any cover has finished.
- **AC-03** — A `terminal-success` card whose cover is still loading shows a pulsing placeholder in
  the cover area. When the cover arrives, the image fades in. Covers arrive in any order, and each
  card updates on its own.
- **AC-04** — The list arrives empty → the existing empty state ("Your shelf is empty!"), unchanged.
- **AC-05** — A card that becomes `terminal-success` through the Realtime UPDATE while the shelf is
  open starts loading its cover from the updated row. It shows the placeholder (AC-03) instead of
  today's "?" tile.
- **AC-06** — The book list read fails → the shelf shows "We couldn't open your bookshelf" with a
  "Try again" button that shows the skeleton and reads the list again. An empty list still shows
  the empty state (AC-04). Decided in OD-01.

### US-02 — A missing cover never looks like an error

As a child, I want a book whose picture will not load to still look like a book, so that I am not
shown an error for something that does not stop me reading.

Applies: SH-01, SH-03, SH-04

- **AC-07** — A cover whose download or signing fails is retried **once**, automatically, with no
  button. The retry covers only the failed covers, in one `signPaths` call, after the first round
  has finished.
- **AC-08** — A cover that fails its retry shows the book-icon placeholder (Phosphor `Books`,
  duotone, same tile styling as the other status graphics). It shows no error text and no retry
  button.
- **AC-09** — A `terminal-success` card with no first page image shows the same book-icon
  placeholder. This replaces today's "?" tile (`page.tsx:304-308`), so a missing cover and a failed
  cover look the same.
- **AC-10** — A cover URL that was issued but whose `<img>` fires `error` goes straight to the
  placeholder (AC-08), with no retry. A retry would return the same cached URL (§5.4).
- **AC-11** — A card in any cover state (loading, ready or failed) stays a single link to its
  bucket's route. No interactive element is added inside the card.

### US-03 — A book opens once its pages are ready, without re-downloading the good ones

As a child, I want a book to open as soon as all its pages are ready, and a hiccup on one page not
to restart the whole download.

Applies: SH-01, SH-02, SH-05

- **AC-12** — The reader downloads a teacher-review book's pages in parallel (SH-01). It renders the
  book once **every** page is ready, as today (ADR-025, `kid-flow-book-persistence.md` §4.4).
- **AC-13** — Pages that fail on the first attempt are retried once automatically. The retry fetches
  **only** the failed pages and reuses the pages that already loaded. A non-teacher-review book still
  signs in one `createSignedUrls` batch, and its retry signs only the paths missing from the first
  result.
- **AC-14** — If any page is still missing after the retry, the reader shows the existing read-failure
  screen (`FailureScreen kind="read-failed"`). The chain counter is unchanged (`kid-flow-reader-and-
  wait-states.md` §4.5).
- **AC-15** — The read-failure screen's own re-sign action fetches only the pages still missing,
  while the child is still on the reader. Leaving the reader discards everything it loaded.
- **AC-16** — The book appears with every page present, or not at all. No page is ever shown as a
  placeholder, a gap or a per-page "try again" (SH-05).

### US-04 — The server handles parallel picture requests without stalling

As any user, I want one person's picture requests not to hold up everyone else's, so that parallel
downloads speed things up instead of queueing behind each other.

Applies: SH-02

- **AC-17** — `get_current_user` no longer blocks the event loop. It runs as a sync dependency,
  which FastAPI runs in its threadpool. Its checks and error codes are unchanged: 401 missing or
  invalid token, 403 `account_unavailable`, 503 `onboarding_unavailable`, 403
  `password_change_required`, and the `/me/password` / `/me/onboarding` exemption.
- **AC-18** — `job_image` takes its two connections from a small shared pool instead of opening a new
  direct connection each time. Every other `connect()` caller is unchanged (§5.5).
- **AC-19** — When the pool cannot hand out a connection within its timeout, `job_image` responds
  `503 image_unavailable` with the `PRIVATE` headers. The frontend treats this like any other failed
  picture (AC-07, AC-13).
- **AC-20** — `job_image`'s authorization is unchanged. It still runs `authorized_asset` before the
  download and again after it, and responds 404 if the second result differs (SH-02).

## 3. Shared behaviour

- **SH-01 — Parallel protected fetch in `signPaths`.**
  - Teacher-review pictures are downloaded with at most **4** requests in flight per `signPaths` call.
  - The session is read once per call. No session means every protected path is left out of the
    result, as today.
  - A failed or non-OK response leaves that path out of the result, and the other paths are
    unaffected.
  - The result maps the same paths to the same kind of URL as the sequential version.
  - Non-teacher-review paths keep their sessionStorage cache and single `createSignedUrls` batch.
  - Every caller inherits this: bookshelf, reader, process page, teacher books page and `GuardedCover`.
- **SH-02 — ADR-080 delivery is untouched.**
  - Protected responses stay `Cache-Control: private, no-store`.
  - No signed Storage link reaches the child.
  - Protected pictures never enter the sessionStorage cache.
  - Blob URLs are revoked when the caller's signal aborts. This includes a blob created after the
    abort; it is never handed out.
  - The after-download re-check in `job_image` keeps the full `authorized_asset` call.
- **SH-03 — Loading visuals reuse existing tokens.**
  - Skeleton and cover placeholders use `animate-pulse bg-muted/50` (the `loading.tsx` pattern).
  - The cover fade-in is opacity only.
  - The skeleton is `aria-hidden`. A visually hidden polite status reads "Loading your bookshelf"
    while the list loads.
  - Cover images keep `alt=""`. The title in the card names the link.
- **SH-04 — Card links do not depend on cover state.** Each card's route comes from its bucket
  only (`BookCard` `href` map). Badges and the teacher-note line are unchanged.
- **SH-05 — Never a partial book.** The reader's all-or-nothing rule
  (`kid-flow-book-persistence.md` §4.4, ADR-025) holds. US-03 changes how pages are fetched, never
  what is shown.

## 4. Edge cases

| Case | Expected behaviour | Home |
|---|---|---|
| Shelf with 0 books | Existing empty state | AC-04 |
| Shelf with 1 book | One card, cover placeholder then fade-in | AC-02, AC-03 |
| Shelf with many books (e.g. 50) | All cards at once. Covers load at most 4 at a time per call (lazy below-the-fold loading is out of scope) | AC-02, SH-01 |
| Mix of baseline and teacher-review books | Baseline covers come from cache or one signed batch. Teacher-review covers are fetched in parallel. Both feed the same per-card states | SH-01, AC-03 |
| Book list read fails | Error state with "Try again", which repeats the list read | AC-06, OD-01 |
| Child leaves the shelf while covers load | All in-flight requests abort, blobs are revoked, no state is set after unmount | SH-02 |
| Child taps a card before its cover arrives | Navigates normally | AC-11, SH-04 |
| Cover fetch fails once (blip, 503 pool timeout) | One automatic retry for the failed covers only | AC-07, AC-19 |
| Cover fails twice | Book-icon placeholder, no text, card still a link | AC-08 |
| Book with no first-page image | Book-icon placeholder | AC-09 |
| Issued URL fails in `<img>` (expired, broken bytes) | Placeholder, no retry | AC-10 |
| Teacher-review book under an open review (`book_review_open`) | Endpoint returns 404, so retry once, then placeholder. The card links by bucket as today | AC-07, AC-08 |
| Session missing or expired mid-load | Protected covers are left out, then retried once, then placeholder. Middleware handles the next navigation | SH-01, AC-08 |
| Password reset during a session (endpoint 403) | Treated as a failed cover or page | AC-08, AC-14 |
| Book finishes while the shelf is open (Realtime) | Card switches to `terminal-success` and its cover loads | AC-05 |
| Realtime update arrives before the first list load completes | Handled as today. The list load sets the cards, and later updates map over them | AC-05 |
| Several Realtime updates for one card | Only the latest cover request for that card can set its cover. Earlier ones are aborted | AC-05, SH-02 |
| Cover arrives after its card moved out of `terminal-success` | Not shown. Covers render only for `terminal-success` (existing rule, `page.tsx:278`) | AC-03 |
| Reader: one-page book | One fetch. Failure path as for any book | AC-12–AC-14 |
| Reader: one page fails once | Only that page is refetched. The book renders when it arrives | AC-13 |
| Reader: a page fails twice | Read-failure screen, counter unchanged | AC-14 |
| Reader: read-failure re-sign | Fetches only the still-missing pages | AC-15 |
| Reader: child leaves mid-download | Aborts, revokes blobs | SH-02, AC-15 |
| Reader: baseline book, one path fails to sign | Retry signs only that path. The cache serves the rest | AC-13 |
| Reader: book open longer than the signed-URL TTL | Unchanged existing behaviour (`kid-flow-book-persistence.md` §4.5) | Out of scope |
| Teacher books page dialog switched mid-load | Existing abort per dialog, now with parallel fetch | SH-01 |
| Two `signPaths` calls at once (e.g. shelf and a cover retry) | Each has its own limit of 4. No shared queue | SH-01 |
| Pool exhausted under load | `503 image_unavailable` after the pool timeout | AC-19 |
| Pooled connection dropped by Supabase while idle | Checked before reuse and replaced, never handed out broken | §5.5 |
| Tests switch `settings.supabase_db_url` per test | The pool is created lazily for the current URL and recreated if the URL changes | §5.5 |
| Authorization changes during a picture download | Second full `authorized_asset` → 404 | AC-20 |
| `get_current_user` called by `require_teacher` / `require_researcher` / `owned_*` | Unchanged results. These are sync dependencies already | AC-17 |
| Test overrides of `get_current_user` | Keep working. The override key is the same function object | AC-17 |

## 5. Design decisions and rationale

1. **Approach B (grill Q1).** Frontend render-first plus parallel fetch, plus cheaper backend
   requests. Parallel requests without AC-17 would make the single-process server slower for
   everyone, which is why the backend part is included even though speed is not the goal.
2. **The reader stays all-or-nothing (grill Q5, reopened).** The first agreement (show the book on the
   first page, per-page retry) contradicted ADR-025 and `kid-flow-book-persistence.md` §4.4. The owner
   chose to keep the rule. Parallel fetching makes the wait about as long as the slowest page rather
   than the sum of all pages.
3. **No caching of protected pictures.** ADR-080 §72-75 requires no-store delivery and forbids signed
   links to children. Changing that needs a new ADR.
4. **Cover retry rules.** A sign or fetch failure gets one retry because it is usually transient. An
   `<img>` error does not, because `signPaths` would return the same sessionStorage URL for a
   baseline cover (*inferred rationale*; no cache bypass exists and adding one is out of scope).
5. **The pool covers `job_image` only.** `connect()` has 39 call sites in `moderation_hold.py`. Many
   are transactions with `for update` on critical safety paths. Pooling them all is a wider change
   that nobody asked for.
   - **Pool library:** `psycopg_pool.ConnectionPool`. It is already in `backend/uv.lock`, so this is
     not a new dependency.
   - **Connection settings:** `autocommit=True` and `row_factory=dict_row`, matching `connect()`.
   - **Size and timeout:** `max_size` about 5 and a short `timeout`, for example 5 s (*assumed
     values*, adjustable).
   - **Health check:** connections are checked before reuse (`check=ConnectionPool.check_connection`).
   - **Creation:** lazy, keyed on `settings.supabase_db_url`, because `test_teacher_hold.py`
     monkeypatches the URL per test.
   - **Shutdown:** the app has no lifespan hook, so the pool closes when the process exits.
   - **Connection type:** this is the web service, separate from the worker's ADR-033 checkpointer
     connection. The sizing assumes the Supabase direct-connection limit has room for about 5 more
     (*inferred*, not checked).
6. **Concurrency of 4 per call** (*assumed value*). It keeps a 50-book shelf from opening 50
   simultaneous backend requests, which would each take a pool connection and threadpool worker.
7. **The skeleton is reused, not copied.** The page renders the route's `loading.tsx` component while
   loading, so there is one source of truth for the skeleton.
8. **Leaner bookshelf query.** It drops `reveal`, `current_stage` and `failure_reason`, which the
   shelf never reads (`classify` uses `status` and `pages`, and `displayTitle` uses `title` and
   `input_text`). `pages` stays: `classify` needs its length and `signPaths` needs page 0's
   `scene_id`. The `.eq("profile_id", …)` filter stays (classmate leak, spec §9.11).
9. **Per-card cover state** (loading / ready / failed) lives in the bookshelf page, keyed by job id.
   Cards follow the existing `BookCard` pattern. No new shared component.

## 6. Verification

**Confirmed seams (owner, 2026-11-23):**

1. `signPaths`, `frontend/lib/signedUrls.test.ts`. Pattern: "feature pictures use authenticated
   bytes and revoke their blob on exit".
2. Bookshelf page, `frontend/app/s/[profileId]/page.test.tsx`.
3. Reader page, `frontend/app/s/[profileId]/book/[jobId]/page.test.tsx`. The existing tests at :301,
   :474 and :486 stay and must pass unchanged.
4. `job_image` over the FastAPI test client, `backend/tests/test_teacher_hold.py`. It needs
   `TEST_MODERATION_DB_URL` (a disposable migrated Postgres) and is otherwise skipped. A skipped run
   is **inconclusive**, not a pass.

**Required new tests (each goes red first for the intended reason):**

- SH-01:
  - With 6 protected paths and fetch promises held open, more than 1 and at most 4 requests are in
    flight together.
  - `auth.getSession` is called once.
  - One path returning 500 is left out while the others return.
- AC-01–AC-03:
  - The skeleton renders while the jobs query is pending.
  - The cards (titles) render while `signPaths` is still pending.
  - A cover appears once its fetch resolves.
- AC-07, AC-08: a cover failing twice ends as the book-icon placeholder, with the card's link intact.
  `signPaths` is called a second time with only the failed path.
- AC-13: a teacher-review book whose first round misses one page retries with exactly that page.
- AC-17: existing auth tests (`test_main.py`, `test_onboarding.py`, `test_avatar.py`) stay green. A
  new test is optional, since no clean public seam exists for "does not block the loop".
- AC-18–AC-20: the existing `test_teacher_hold.py` picture tests stay green. Add one test for pool
  timeout → 503 with `PRIVATE` headers.

**Pre-merge commands** (`AGENTS.md`):
- `frontend/`: `pnpm lint && pnpm build && pnpm test`
- `backend/`: `uv run ruff check . && uv run pytest`

**Acceptance evidence:**
- The owner observes journeys 1 and 2 in a real browser. DevTools "Slow 4G" throttling makes the
  skeleton, placeholder and fade-in states visible.
- The console is clean.

**Results:** not run. This spec establishes no passing behaviour.

## 7. Open decisions and readiness

- **OD-01 — The bookshelf list read fails. Decided 2026-11-24:** show the shelf error state with a
  "Try again" button that repeats the list read, in the `error.tsx` copy tone. The empty state told a
  child with books that they had none. Throwing to `error.tsx` was rejected: it logs to the console
  and offers "Back to Bookshelf", a link to the page that just failed.
- **OD-02 — Load the book state once in `job_image`** (not blocking, deferred). The grill agreed on
  it, but a lighter re-check is safe only if every input that can change the selected path also
  changes a cheaper fingerprint. Those inputs include checkpoint state, `job_picture_records`,
  reviews and profile state, and ADR-080 requires the re-check. This is unproven, so the double full
  check stays. To revisit it, first list those inputs and show the fingerprint covers each one.
- **Assumed values:** concurrency 4, pool `max_size` about 5, pool timeout about 5 s.

**Readiness:** Ready. OD-01 decided 2026-11-24.

## 8. Sources and coverage

| Source requirement | Home |
|---|---|
| Grill Q1 B: frontend render-first + parallel + backend non-blocking auth + pool | US-01, SH-01, AC-17, AC-18 |
| Grill Q1 B: load state once | OD-02 (deferred, reason given) |
| Grill Q2: owner's observation is the baseline | §1, §6 acceptance evidence |
| Grill Q3 A: cards first, pulsing cover, fade-in, no blank flash | AC-01–AC-03, SH-03 |
| Grill Q4 A: one silent retry, then book-icon placeholder, card tappable | AC-07–AC-11 |
| Grill Q5 A (reopened): parallel, retry only failed, all-or-nothing | AC-12–AC-16, SH-05 |
| Audit #7: leaner shelf query | §5.8 |
| Seams 1–4 confirmed | §6 |
| ADR-080: no-store, re-check, no signed links | SH-02, AC-20, §5.3 |
| ADR-025 / book-persistence §4.4: never partial | SH-05, AC-16 |
| Reader spec §4.3 / §4.5: read-failed screen, counter | AC-14, AC-15 |
| Exclusions: caching, batch endpoint, thumbnails, getClaims, lazy covers | §1 Excluded |
| "Consider the edge cases" (owner) | §4 |
