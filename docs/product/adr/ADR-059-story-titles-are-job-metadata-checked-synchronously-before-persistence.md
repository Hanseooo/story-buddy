# ADR-059 — Story titles are job metadata, checked synchronously before persistence, never entering `StoryMemory`

**Status:** Accepted (2026-09-09) · resolves the gate opened by `docs/specs/story-titles.md` §2 ·
no `StoryMemory`/`contracts/` schema change · no new moderation model · amends nothing, extends
ADR-011 mechanism 1/2 and ADR-045 to a second text surface

**Context:**

`docs/specs/story-titles.md` requires a required, 1–80 char, safety/privacy-checked, immutable
title, displayed consistently across existing surfaces, and explicitly forbids treating its own
proposed schema and checking sequence as accepted. It also flags the one pattern not to copy:
`create_storybook` currently writes `input_text` to `jobs` *before* `input_gate` (the async worker
node) redacts or moderates it — the raw story sits in Postgres, in the RQ payload, and in every log
line between submission and the worker picking up the job. That ordering is why `redacted_text` and
`raw_text` are separate fields on `Input` (`contracts/story_memory.py:139-140`) — the ordering
conflict is a known, contained thing for story text. A title has no such containment: the spec
requires the checked title to be *shown back to the child before they commit*, which the async
path cannot do (the worker runs after the HTTP response is already sent).

Three things are already built and must be reused, not reimplemented:

- `providers.classify_text_primary` / `classify_text_backstop` — the two-classifier, two-vendor
  text moderation ADR-011 mandates. `input_gate.py:18,52` calls them on `state.input.raw_text`.
- `providers.redact_pii` — unconditional structured-identifier redaction, optional person
  pseudonymization gated by `settings.pii_pseudonymize_persons` (ADR-045). `input_gate.py:19` calls
  it on the same text.
- `_log.info("story truncated: %d words → %d words", ...)` in `main.py:101` — the existing pattern
  for logging counts/deltas about user text without logging the text itself (CC-5, ADR-025 D5).

None of the three is text-shaped in a way that cares whether the string is a title or a story body.
The open questions are ordering (sync vs. async) and where the checked result lives, not what does
the checking.

**Decision:**

1. **Schema.** `jobs.title` — nullable `text` column. Existing rows stay `NULL`; no backfill.
   `CreateStorybookRequest.title: str`, required, validated by a `field_validator` mirroring
   `validate_min_length`'s existing pattern: trim, reject embedded `\n`/`\r`, require
   `1 <= len(unicodedata-aware codepoint count) <= MAX_TITLE_CHARS`. `MAX_TITLE_CHARS = 80` is added
   to `backend/app/config.py` beside the other named constants (`MIN_STORY_WORDS`, etc.).

2. **Title is job metadata, not pipeline input.** `title` is **not** added to `contracts/story_memory.py`.
   It is written to and read from the `jobs` row only, exactly like `style_preset_id` and
   `truncated` are today — never constructed into a `StoryMemory`/`Input`, never passed to
   `analyze`, `segment`, `build_prompt`, any judge, or any caption. This is what spec §4 ("title and
   story remain separate... never prepend the title to narrative text") requires structurally, not
   just by convention: a field that doesn't exist on `Input` cannot leak into a prompt built from
   `Input`. `backend/contracts/` is untouched — the cross-node contract rule in the spec's §2 doesn't
   apply, because the title crosses no LangGraph node boundary. No `schema_version` bump.

3. **Checking is synchronous, in `create_storybook`, before the `jobs` insert — not in `input_gate`.**
   `create_storybook` calls `classify_text_primary`, and on a primary pass or error calls
   `classify_text_backstop` — the same primary-then-backstop sequence `input_gate.py:44-62` already
   implements — and separately calls `redact_pii`, all on `payload.title`, all before constructing
   the insert dict. This duplicates ~15 lines of sequencing already in `input_gate.py`, not the
   classifiers themselves; extracting a shared `check_text(text) -> (safe, categories, redacted)`
   helper into `providers.py` is in-scope for whoever implements this ADR, not a second moderation
   stack. The story body's async, post-write ordering (§ Context) is unchanged by this ADR — that
   remains a separate, already-flagged conflict, not one this ADR resolves.

4. **The child sees the checked title before it is persisted; a redaction cannot silently rename
   the submission.** `CreateStorybookRequest` gains `title_ack: str | None = None`. Flow:
   - Run the check. If either classifier flags the title unsafe → `422`, generic message ("that
     title isn't allowed"), nothing written, nothing logged beyond pass/fail (CC-5: no title text
     in diagnostics, same rule `main.py:100-101` already follows for the story).
   - If `redact_pii(title) != title`:
     - If the redacted form is empty or exceeds `MAX_TITLE_CHARS` → `422`, "give your story a
       different title," nothing written.
     - Else, if `payload.title_ack` is not exactly equal to the redacted title → `409` with the
       redacted title in the response body, nothing written. The client shows it and resubmits the
       same request with `title_ack` set to that string once the child accepts it (or edits `title`
       and resubmits, restarting the check).
     - Else (`title_ack` matches) → proceed to insert.
   - If `redact_pii(title) == title` → proceed to insert.
   - The value written to `jobs.title` is **always** the redacted string, never `payload.title`
     directly, even when they're equal — one code path, not a "clean titles skip redaction" branch
     that could drift.

   This is the "explain any privacy replacement before the child commits a submission" requirement
   (spec §4) implemented as a stateless confirm-then-retry, not a stored draft: `title_ack` is
   client-held state for one retry, not a new persisted entity, so this adds no autosave (spec §3's
   "no persistent draft autosave" is unaffected).

5. **Immutability is enforced by absence of a write path, not by hiding UI.** No endpoint accepts a
   title update. `create_storybook` is the only place `jobs.title` is written. "Make the story
   again" and "Change my words" (spec §4) both go through `create_storybook` again, producing a new
   `job_id` with its own `title` — never an update to the original row. Confirming this needs no
   code change: `main.py`'s only `PATCH` route is `/me/avatar`; this ADR's implementation must not
   add a title field to any future PATCH route without superseding this decision.

6. **Failure recovery never stores an unchecked title.** `FailureScreen`'s resubmit and the `sb.prefill`
   revision payload (spec §4, `frontend/components/FailureScreen.tsx`) carry `title` as a plain
   string through client-side transfer storage only. Every resubmission re-enters `create_storybook`
   and re-runs steps 3–4 in full — there is no "already checked, skip the check" flag, because the
   only source of truth for "checked" is a freshly computed redaction match, not a boolean the
   client could forge or a stale result from a prior request.

**Consequences:**

- A submission now costs one extra synchronous round of the same two classifiers plus `redact_pii`,
  paid once per `POST /storybooks` (not per scene) — the same order of cost ADR-011 already accepts
  for the input-gate backstop call.
- A child can see a `409` mid-submit if their title contains a phone number or address; the title
  field, unlike the story field, cannot silently accept-and-rewrite, because there's no async node
  positioned to explain a change after the fact.
- `jobs.title` and `StoryMemory` never need to agree on a value, because only one of them ever holds
  a title. A future feature that *did* need the title inside generation (spec explicitly rules this
  out — "it does not provide characters, events, captions, or instructions to the illustration
  pipeline") would need a superseding ADR to add it to `contracts/`.
- The story body's pre-redaction write ordering remains uncontained. This ADR does not touch it and
  does not claim to; `docs/specs/story-titles.md` §2 already names it as a separate, pre-existing
  conflict.
- Extracting `check_text()` from `input_gate.py`'s inline sequencing touches a file on the
  child-safety critical path; the extraction must not change `input_gate`'s own behavior, and the
  implementer should add the extraction's test alongside the existing `input_gate` tests before
  touching `main.py`.

**Alternatives:**

- **Check title asynchronously, alongside `input_gate`, on the worker.** Rejected. The spec requires
  showing the checked/redacted title to the child *before* they commit (§4), and by the time the
  worker runs, the HTTP response enqueueing the job has already gone back to the client — there is
  no request left to attach the confirmation to. This is the async-vs-sync gap the Context section
  names.
- **Add `title` to `StoryMemory.Input` and let `input_gate` check it alongside the story.** Rejected.
  It would put title text inside the pipeline's checkpointed state and inside `contracts/`, contract
  the spec repeatedly says the title must stay outside of ("book metadata outside generation
  inputs"), and would require a `schema_version` bump for a field no pipeline node reads.
- **Silently store the redacted title without a confirm round-trip.** Rejected — spec §4 explicitly
  requires explaining a privacy replacement before commit; a silent rewrite is the "silent post-submit
  rename" the spec calls out as unacceptable.
- **A separate `POST /storybooks/title-check` endpoint, decoupled from submission.** Rejected as the
  first move: two round-trips (check, then submit) invite a stale-check race — the client could
  submit a title different from the one it checked. Folding the check into `create_storybook` itself
  with a `409`-and-retry keeps the check and the write atomic. Not precluded as a future addition if
  a product need for live-as-you-type checking arrives; that would need its own decision, since it
  reintroduces the race this rejects.
- **New moderation model or a title-specific classifier.** Rejected — no observed failure mode
  motivates one, and ADR-015/ADR-011 already fix the open-weight, two-vendor stack for text; a title
  is text.

**Escape hatch:** Adding title text to `contracts/story_memory.py` or any pipeline node input,
introducing a title-update/rename endpoint, checking titles asynchronously, or adding a new
moderation model for titles each require a superseding ADR and owner acceptance before
implementation.
