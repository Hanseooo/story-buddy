# Feature Spec — kid-flow book persistence & access

**Status:** draft · **Phase:** 2 · **Owner:** `supabase/migrations/0004_jobs_pages.sql`,
`backend/worker/run_job.py`, `frontend/app/book/[jobId]/page.tsx`
**Derived from:** `docs/specs/kid-flow-ui-docket.md` S1 · **Rationale:** ADR-006, ADR-013, ADR-017,
ADR-025, `DECISION_BACKLOG.md:228`

> Not a pipeline node. This spec covers the durable surface between the graph's terminal state and
> everything that reads a finished book, plus who may read it.

## 1. Purpose

Phase 1 generates an N-page book that nothing outside the LangGraph checkpoint blob can read:
`run_job.py` writes only `scenes[0]` into the single-scene `jobs.caption` / `jobs.image_path`
columns. This spec gives a book a durable, readable shape and names who may read it.

## 2. Contract slice

`backend/contracts/` is **unchanged**. This spec adds no field to `StoryMemory` and bumps no
`schema_version`. It defines a *projection* of the graph's terminal state into the DB job row.

- **Reads (from `StoryMemory`):** `scenes[].scene_id`, `scenes[].caption`,
  `scenes[].final_image_ref`
- **Writes (to `jobs`):** `pages jsonb`
- **Invariants:** see §5.

### The page shape

```json
{"scene_id": "s0", "caption": "The dog ran through the field.", "image_path": "job-1/s0-1.png"}
```

`pages` is an ordered JSON array of these. Three rules:

- **`image_path` is a durable Storage path, never a signed URL.** Same rule as
  `Character.canonical_ref_image` and `Scene.final_image_ref` (ADR-006). Signed URLs are minted at
  read time and never persisted — a stored URL bakes an expiry into a durable row.
- **Array order is page order.** There is deliberately **no** `page_index` field, for the reason
  `Scene` has no `order` field (`story_memory.py:127-131`): it would be a second source of truth
  beside the `upsert_scenes` ordering contract, which already guarantees segmentation order
  survives the JSON round-trip.
- **`scene_id` is carried even though the reader ignores it.** It is the join key back to
  `scenes[].attempts` and its verdicts, for `export-pdf` and for CC-5 tracing. It is not dead.

## 3. Position in the system map

```
compose (pure, returns {})  ->  run_job.py  ->  jobs.pages  ->  /book/[jobId]      (this spec)
                                                            ->  export-pdf        (later reader)
```

`compose` stays pure. It performs no I/O by design (MASTER_SPEC §6 rule 1) and continues to return
`{}`. Its terminal assertions are what make the projection total — see §4.2.

The worker is the only writer. It already owns every `jobs` write, and writing `pages` inside the
existing terminal `UPDATE` is what makes the book atomic (§5.1).

## 4. Behavior & edge cases

### 4.1 Happy path

1. `app_graph.invoke()` returns; `compose` has already asserted every scene is finalized.
2. The worker projects `result["scenes"]` into the page array, in list order.
3. One `UPDATE` sets `status='complete'`, `current_stage='compose'`, and `pages` together.

```python
pages = [
    {"scene_id": s.scene_id, "caption": s.caption, "image_path": s.final_image_ref}
    for s in result["scenes"]
]
supabase.table("jobs").update(
    {"status": "complete", "current_stage": "compose", "pages": pages}
).eq("id", job_id).execute()
```

4. The reader selects `id, status, pages`, batch-signs every path in one call, renders image +
   caption per page in array order.

```ts
const { data, error } = await supabase.storage
  .from(BUCKET)
  .createSignedUrls(job.pages.map(p => p.image_path), 3600);
```

### 4.2 A caption-less page — `compose` gains one assertion

`Scene.caption` is `Optional[str]`. `segment` sets `caption = text_excerpt` (ADR-013, verbatim), so
in practice it is always populated — but `compose` asserts only that `final_image_ref` is non-null.
Nothing structurally stops a caption-less scene reaching `pages`, and ADR-013 says a page **is** an
image plus a verbatim caption. A page with a null caption is not a page.

`compose` therefore extends its existing unfinalized-scene check to captions, failing the job by the
same route:

```python
uncaptioned = [s.scene_id for s in state.scenes if not s.caption]
if uncaptioned:
    raise ValueError(f"compose: scenes without a caption: {uncaptioned}")
```

This is a change to `compose`, and `docs/specs/compose.md` is updated in the same change. It belongs
here rather than to a `compose` revision because S1 owns "what stops an unreadable book from being
shown as complete", and the terminal gate is the only place positioned to check it.

### 4.3 A failed job never writes pages

The `except` block in `run_job.py` sets `status='failed'` and returns. `pages` keeps its `'[]'`
default. A book is never delivered partial (ADR-025) and there is no "some pages" state.

Zero scenes is the same path: `compose` raises, the job fails, `pages` stays `[]`.

### 4.4 A page whose image will not sign

`createSignedUrls` reports failures **per path** — a missing or unreadable object yields an error
entry and a null URL rather than rejecting the batch. Rendering the rest would produce a book with a
hole, which ADR-025 forbids.

**Rule: if any page fails to sign, the read fails as a whole.** The reader shows an error, never a
book missing a page. What that error *looks like* is S4's; that it is an error and not a gap is S1's.

### 4.5 Signed-URL expiry mid-read

URLs are signed for 3600s. A book left open longer than an hour will show broken images. For a
book of at most `MAX_SCENES` pages this is a generous ceiling, and no refresh is built here.
Re-signing on failure is a reader-behavior decision and belongs to S4.

### 4.6 Re-running a completed job

The write is a full overwrite of `pages` keyed on `job_id`, derived purely from terminal state, so
re-running the same `thread_id` is idempotent. S2 introduces a resume path; the terminal write stays
the only writer of `pages` regardless of how many times the graph is entered.

### 4.7 Existing rows

The migration does **not** backfill. Dropping `caption` / `image_path` destroys the only page data
old `complete` rows had, so they become unreadable books. This is acceptable and deliberate: ADR-017
means no self-serve signup, nothing is deployed, and no real child data has entered the system —
every existing row is a disposable dev row.

## 5. Invariants

1. **`pages` is written exactly once, atomically with `status='complete'`.** One `UPDATE`, one
   statement. There is no code path that writes one without the other.
2. **Non-empty `pages` ⟺ a complete book exists.** The reader treats `status !== 'complete'` or
   `pages.length === 0` as *not ready*, never as an empty book. This is a claim about the row, not
   about the read: a complete row can still fail to render if its images will not sign, which is a
   separate whole-book failure (§4.4).
3. **Progress writes may touch `current_stage`; they may never touch `pages`.** This keeps the door
   open for S4 to make `current_stage` move during a run without touching this surface.
4. **Every `image_path` is a durable path.** No signed URL is ever stored.

Enforced by **atomicity, not a `CHECK` constraint**. A constraint such as
`check (status <> 'complete' or jsonb_array_length(pages) > 0)` would guard against a second writer
that does not exist, and would have to be reconciled against existing dev rows. It is named in a
`ponytail:` comment in the migration as the upgrade path if a second writer ever appears. One
deterministic test asserts the projection (§7).

## 6. Access & the trust boundary

Both surfaces sit on the capability-link model already in force: **the job UUID is the capability.**

### 6.1 `jobs.pages`

A column on `jobs`, so it inherits the existing policy at `0001_jobs_table.sql:18-21`
(`for select to anon using (true)`). **No new `jobs` policy is added** — this spec deliberately
creates nothing extra for `auth-and-classroom` to find and fix.

### 6.2 `storage.objects` — a gap this spec closes

The `storybook-images` bucket is private and **no `storage.objects` policy exists anywhere in
`supabase/migrations/`**. The backend signs with the service-role key (`app/db.py`), but
`/book/[jobId]` signs from the browser with the anon key — that call cannot succeed against a real
Supabase. The single-image reader is already broken; it passes CI only because `page.test.tsx`
mocks the storage call.

The migration adds the missing half of the existing model:

```sql
create policy "anon can sign storybook images"
  on storage.objects for select to anon
  using (bucket_id = 'storybook-images');
```

This is not a new grant of trust — it is the same capability link the `jobs` policy already extends,
applied to the assets those rows point at. Storage paths are `{job_uuid}/{scene_id}-{n}.png`, so the
job UUID remains the capability. It carries the same `ponytail:` marker as `0001:22-23`.

### 6.3 Realtime

`jobs` is in the `supabase_realtime` publication, so the completion `UPDATE` now carries `pages` in
the payload to any anon subscriber. This is the same `using(true)` exposure that already applies to
every other column on the row, not a new hole, and it closes by the same migration named below.

### 6.4 The named boundary

**`auth-and-classroom` replaces both policies** — the `jobs` policy and the `storage.objects` policy
— in one migration, with profile-scoped RLS on an auth'd role.

This spec does **not** issue accounts, establish sessions, scope classrooms, or add
`profile_id` / `classroom_id` columns to `jobs`. It names where that work attaches and stops.

## 7. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Backend (`backend/tests/test_run_job.py`, models mocked):

- The terminal `UPDATE` contains `pages` with one entry per scene, in `result["scenes"]` order.
- Each entry is exactly `{scene_id, caption, image_path}`, with `image_path == final_image_ref`.
- `status='complete'` and `pages` appear in the **same** update dict (invariant 5.1).
- A raising graph produces `status='failed'` and no `pages` key.
- The two existing assertions on `final_update["image_path"]` (`:50`, `:90`) are replaced.

Backend (`backend/tests/test_compose_node.py`, models mocked):

- A scene with `caption=None` raises `ValueError` (§4.2).

Frontend (`frontend/app/book/[jobId]/page.test.tsx`):

- N pages render N images and N captions, in array order.
- `createSignedUrls` is called **once**, with every path.
- A per-path signing error renders the error state, not a partial book (§4.4).
- `status='running'` or `pages: []` renders the not-ready state, not an empty book.

## 8. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-4 Security (RLS + signed URLs)** — closes the missing `storage.objects` policy; keeps
  durable paths, signs at read time; adds no second policy surface; names `auth-and-classroom` as
  the owner of scoping (§6).
- [x] **CC-9 Failure states = success states** — a book that cannot be fully read fails as a whole
  rather than rendering with a hole (§4.4); not-ready is a distinct state from empty (§5.2).
- [x] **CC-10 Checkpointing / resumability** — the terminal write is idempotent and derived purely
  from terminal state (§4.6).
- [ ] CC-1 Moderation ordering — N/A (persistence layer; every image in `pages` already passed
  `output_mod` upstream).
- [ ] CC-2 PII redaction — N/A (captions are already-redacted `text_excerpt`s; this spec copies,
  never re-derives).
- [ ] CC-3 Cost control — N/A
- [ ] CC-5 Observability — N/A (`compose` already emits the one per-book record).
- [ ] CC-6 Accessibility — S4's (reader rendering).
- [ ] CC-7 Reproducibility — N/A
- [ ] CC-8 Kid vs teacher design — S4's.

## 9. Eval / quality checks

N/A. This spec produces no content; it copies content another node already produced.

## 10. Blast radius — changed in the same change

| File | Change |
|---|---|
| `supabase/migrations/0004_jobs_pages.sql` | new — add `pages`, drop `caption` / `image_path`, add the storage policy |
| `backend/worker/run_job.py` | `:49-62` — write `pages`, drop the two single-scene keys and their comment |
| `backend/pipeline/compose.py` | the caption assertion (§4.2) |
| `backend/tests/test_run_job.py` | `:50`, `:90` — replaced per §7 |
| `frontend/app/book/[jobId]/page.tsx` | select and render `pages` |
| `frontend/app/book/[jobId]/page.test.tsx` | per §7 |
| `docs/specs/compose.md` | `:181` — the flagged gap is closed; record the caption assertion |
| `docs/specs/ROUTE_MAP.md` | §1 — note the flat routes are intended sequencing (§11) |
| `docs/product/DECISION_BACKLOG.md` | `:236` — `job-failure-reason` renumbered `0004` → `0005` |
| `AGENTS.md` | Safety non-negotiables — the storage policy joins the RLS gap paragraph |

**Not touched:** `MASTER_SPEC.md` §7 and `DECISION_BACKLOG.md`'s `kid-flow-ui` roster rows. The
docket updates those once **all four** sessions are done, not per session, or the index points at
files that do not exist.

**Also not touched:** `docs/specs/story-memory-contract.md:338,367-384` mentions `caption` /
`image_path`, but as *graph-state* keys in a historical account of a completed migration. It is
already correct and is not blast radius.

## 11. Routes

The kid routes **stay flat** — `/write`, `/process/[jobId]`, `/book/[jobId]` — until
`auth-and-classroom`. Moving to ROUTE_MAP §1's `/s/[profileId]/…` tree now would put
`settings.dev_profile_id` in a URL: a sentinel as a route segment, guarding nothing, easily mistaken
for a guard. The later move is a directory rename plus a middleware entry; the components S4 builds
are unaffected.

`ROUTE_MAP.md` §1 gets a status note recording this as intended sequencing. That closes the docket's
`Found & parked` entry of 2026-08-02.

## 12. Second reader

`export-pdf` reads the same `pages` column server-side with the service-role key — no signing
policy, no different shape, no per-page query. Designed for two readers, built for one.

## 13. Linked decisions & open questions

**Depends on:** ADR-006 (RLS + signed URLs, durable paths), ADR-013 (a page is an image plus a
verbatim caption), ADR-017 (no self-serve signup — why §4.7 is safe), ADR-025 (never partial),
ADR-023 (`story_id = job_id`).

**No ADR is written for the storage shape.** The docket's ⚠️ asks whether a `jobs.pages jsonb`
choice is hard enough to reverse to need one. It is not: one column, one writer, one reader, and
jsonb → a `pages` table is a mechanical backfill. AGENTS.md §2's "architectural decisions get their
own session" is satisfied — this is that session, and `DECISION_BACKLOG.md:228` already assigns the
gap to `kid-flow-ui`.

**Handed to later sessions:**
- **S2** — the terminal write stays the only writer of `pages` across the pause lifecycle (§4.6).
- **S4** — what the not-ready state, the whole-book read failure (§4.4), and expiry re-signing
  (§4.5) look like; and whether the worker moves to `stream()` so `current_stage` actually advances.
  Both are reader-behavior decisions with no schema, so S4 can take them without an amendment.
- **`auth-and-classroom`** — the two policies in §6.4.
