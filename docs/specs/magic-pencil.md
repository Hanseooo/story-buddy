# Feature Spec — Magic pencil (child creative control)

**Status:** approved (owner, 2026-11-01) · **Phase:** Post technical defense, rank 4 · **Owner nodes:**
`backend/pipeline/reveal.py`, `backend/pipeline/char_bible.py`, a post-completion page-edit worker task (OD-01)
**Derived from:** [`.scratch/ptd-child-creative-control`](../../.scratch/ptd-child-creative-control/map.md)
tickets 01 (audit) and 02 (interview, 2026-11-01) · **Rationale:**
[ADR-082](../product/adr/ADR-082-magic-pencil-child-edits-and-other-versions.md), amending ADR-029 §2
and ADR-069 · **Depends on:** ADR-080 holds, `moderation-stack.md` §9

## 1. Purpose and scope

Image generation is a dice roll. Today a child who dislikes a picture has one tool: up to 3 chip
redraws per book at "Meet your characters", each a fresh draw that can fix the chosen detail and break
others (owner's example: a "blue shirt" description also turned the skin blue). Pages cannot be
changed at all. The panel suggested the child adjust appearance and say how a page should look.

The magic pencil gives the child two general tools instead of more per-defect prompt fixes:

- **Other versions.** Pick another picture the pipeline already drew. No new image cost.
- **Pencil.** Write what to change; the current picture is edited once; the child keeps the new one
  or goes back.

Both tools appear at "Meet your characters" (the existing reveal pause) and on the finished book.
The child is the judge; the noisy checkers are not consulted on what the child chose.

**Users:** children aged 10–12 in a classroom (the moderation rubric's age band), and their teacher,
who handles held content and re-reviews edited books.

**Included:** the two tools on characters and pages, a per-book allowance, moderation and teacher
holds for pencil text and results, approval reset on edit, logging of every pencil use.

**Excluded (owner, 2026-11-01):**
- A blank custom prompt that draws a new picture from scratch. Rejected: it discards the story and the
  character canon, and image prompts are an adult skill.
- Pausing the run on each page that reached its retry cap. Rejected: more waiting, and ADR-003 keeps
  the graph's single pause point at the reveal.
- Editing the reference with only the chip's wording (audit option A2). Dropped: failed its screen,
  2 of 9 (`docs/capstone/model-probes-2026-10.md`, "Tap wording as an edit: result").
- Consistency-checker review of pencil results. The child judges.
- Page-level teacher approval. Review stays whole-book.
- Further paid probes for this epic. The pencil ships unmeasured on children's wording.

**Release gates (unchanged from the phase map):** the feature is off by default and synthetic-only
until an ethics re-review. Pencil free text does not ship before
`ptd-moderation-calibration` audit 01 resolves.

### 1.1 Existing behaviour that constrains this (verified 2026-11-01)

- Reveal chips come from style-filtered canon, never the judge (`reveal.py:29`, ADR-069). The
  confirm endpoint accepts only an offered chip (`main.py:274`, `moderation_hold.py:867`).
- A tap is one `text_to_image` draw plus one judge call, overwriting the reference unconditionally
  (`char_bible._mint_targeted`, `char_bible.py:374`). 3 taps per book (`MAX_RETRY_TAPS`).
- `mint_reference` uploads only the accepted or best-of draw; the other up to 2 draws are discarded
  (`char_bible.py:347-371`).
- Every scene draw is kept in `Scene.attempts`; only `final_image_ref` is moderated. Others stay
  `safety_eligibility="unreviewed"` (`output_mod.py:118`, `story_memory.py:212`).
- Delivery in teacher-review mode signs only a final image whose attempt is `cleared` or
  `teacher_allowed` (`moderation_hold.py:813-819`).
- Scene prompts are built at draw time in `generate_scene` (`generate_scene.py:76`), after the reveal.
- The finished book reads `jobs.pages` (`book/[jobId]/page.tsx:257`), written by the worker
  (`run_job.py:274`).
- Teacher review is whole-book: `approved_at` / `rejected_at` on `jobs`
  (`teacher-review-and-approval.md` §3).
- The off-by-default pattern is a settings flag snapshotted per submission:
  `settings.enable_teacher_moderation_review` → `jobs.moderation_mode="teacher_review_v1"`
  (`main.py:164`, `:211`).
- `IMAGE_BUDGET` = 55 per book, checked before every paid draw (`config.py:219-229`).
- `build_corpus` auto-confirms the reveal (#96), so corpus generation never exercises the pencil.

## 2. User stories and acceptance criteria

### US-01 — Pick another version of a character

As a child at "Meet your characters", I want to see other pictures of my character, so that I can pick
the one that looks right without waiting for a new drawing.

Applies: SH-01, SH-02, SH-04, SH-07, SH-08

- **AC-01.** When a character has at least one other kept picture, the reveal shows an
  "Other versions" control for that character. With none, the control is absent, not disabled.
- **AC-02.** Kept pictures are the unchosen draws of the initial mint (up to 2) and this book's
  earlier pictures of that character: each picture replaced by "Draw again", a pencil result, a
  version choice or a moderation replacement (OD-02). Earlier pictures that were flagged or
  withdrawn are never offered.
- **AC-03.** Opening other versions moderates each unmoderated picture before display (SH-02). A
  picture that fails moderation is marked excluded, is not shown and does not create a teacher hold
  (OD-03).
- **AC-04.** Choosing a version makes it the character's reference for the rest of the book. It costs
  no image and no go.
- **AC-05.** A character accepted on its first draw has no other versions until the child changes
  it; after "Draw again" or a kept pencil result, the earlier picture is another version, so either
  change can be undone at no image cost.

### US-02 — Change a character with the pencil

As a child at "Meet your characters", I want to write what to change about my character, so that I can
fix one thing without losing what I liked.

Applies: SH-01, SH-02, SH-03, SH-04, SH-05, SH-06, SH-07, SH-08, SH-10

- **AC-06.** Each character with a picture shows a "Magic pencil" control beside "Draw again" (today's
  chip button, unchanged). Both use the book's 3 character goes.
- **AC-07.** The pencil opens a labelled text box, max `MAX_PENCIL_CHARS` (about 200). Submit is
  disabled while empty. The count of goes left is shown.
- **AC-08.** On submit, the text is PII-redacted before it is stored (SH-03), then moderated (SH-02).
  A flag holds it for the teacher (SH-05); no image is drawn.
- **AC-09.** Cleared text edits the current reference once (`edit_image`, current picture as input,
  the child's text plus the fixed keep clause). One go is spent. No judge call.
- **AC-10.** The edited picture passes reference moderation (`char_ref_mod`) before display; a flag
  follows ADR-080's reference hold (rank 2 ticket 10). If the teacher requests a replacement, the
  same edit (same source picture and redacted text) is run once more within ADR-080's per-book
  replacement slot; it is not a fresh text-to-image draw.
- **AC-11.** The child then sees the new picture with "Keep this" and "Use the old one". "Use the old
  one" restores the previous reference; the new one stays available as another version. The go is
  spent either way.
- **AC-12.** When the child keeps the new picture, the redacted text is added to the character's
  child changes (SH-06) so later pages are drawn with it, including a change that contradicts the
  story.

### US-03 — Pick another version of a page

As a child reading my finished book, I want to see other pictures the app drew for a page, so that I
can choose the one I like.

Applies: SH-01, SH-02, SH-04, SH-07, SH-08, SH-09

- **AC-13.** A page with more than one kept attempt shows "Other versions". Attempts marked
  `excluded` are never offered.
- **AC-14.** Unmoderated attempts are moderated on open (SH-02); failures are not shown and do not hold
  (OD-03).
- **AC-15.** Choosing a version replaces the page picture in the book and the PDF. It costs no image
  and no page pencil.

### US-04 — Change a page with the pencil

As a child reading my finished book, I want to write what to change on a page, so that the picture
matches my story.

Applies: SH-01, SH-02, SH-03, SH-04, SH-05, SH-07, SH-08, SH-09, SH-10

- **AC-16.** Each page shows "Magic pencil" while page pencils remain (5 per book, SH-04).
- **AC-17.** Submission follows AC-07/AC-08: redact, store, moderate; a flag holds.
- **AC-18.** Cleared text edits that page's current picture once. The result passes output moderation
  before display; a flag holds under ADR-080 and the book keeps its current picture meanwhile. A
  teacher replacement re-runs the same edit once, as in AC-10. A teacher allow makes the result
  available for the child's keep-or-old choice; a teacher stop discards the request only, never the
  book.
- **AC-19.** The child chooses "Keep this" or "Use the old one" as in AC-11. A page edit changes only
  that page; it never changes the character's canon.

### US-05 — Teacher sees edited books again

As a teacher, I want an edited book to come back to me, so that classmates only see pictures I have
seen.

Applies: SH-09

- **AC-20.** Any page change to an approved or rejected book (a version choice or a kept pencil
  result) sets it back to pending and removes it from the gallery until re-approved.
- **AC-21.** Before the first change to an approved book, the child confirms: "Your teacher will look
  at your book again before classmates can see it." Cancel leaves the book unchanged.

### US-06 — Every pencil use is recorded

As the research team, I want each pencil use recorded, so that the unmeasured pencil can be measured
once real use is allowed.

Applies: SH-03, SH-08

- **AC-22.** Each pencil use records: job, target (character or page), before picture, after picture
  or the reason none exists, redacted text, moderation outcome, and the child's choice (kept, old, or
  none yet). Records live in a new job-owned table and follow story deletion (OD-04).

### US-07 — A moderation redraw keeps the child's chosen detail

As a child who tapped "Draw again" on a detail, I want the redraw to still try that detail if the first
result is flagged, so that my choice is not silently ignored.

Applies: SH-02

This fixes the open question in `reference-moderation-retry.md` §8.1 for **baseline-mode** jobs. It is
not behind the SH-01 setting: it corrects existing behaviour and needs no new child input. In
teacher-review mode a flag already holds and a teacher replacement redraws from
`ref_generation_prompt`, which carries the tapped emphasis (`char_bible.replace_reference`).

- **AC-23.** When `char_ref_mod` flags a reference produced by a "Draw again" tap in a baseline-mode
  job, the one automatic moderation redraw uses that reference's recorded prompt, including
  `Be sure to include: {chip}.`, as a single draw, not the untargeted 3-draw mint.
- **AC-24.** That redraw spends `ref_mod_retry_count` as today, not a child go. A second flag ends the
  job as today (`reference-moderation-retry.md` §4.6, "The redraw flags too").
- **AC-25.** A flag on an initial (untapped) reference keeps today's untargeted re-mint.

## 3. Shared behaviour

- **SH-01 — Off by default, per submission.** A new setting (default off) is snapshotted onto the job at
  submission, like `enable_teacher_moderation_review`. A job submitted with it off never shows the
  tools, even if the setting is later turned on. Turning it off does not remove tools from jobs
  already submitted with it on. The tools are offered only on jobs whose `moderation_mode` is
  `teacher_review_v1`, because holds (SH-05) exist only there (OD-05). A baseline-mode job never
  shows them.
- **SH-02 — Nothing unmoderated reaches a child.** Every picture the tools show, and every pencil
  text, passes the existing moderation stack first. An unmoderated attempt is moderated on demand and
  its `safety_eligibility` is stored so it is checked once. Classifier errors are not flags: the
  picture is not shown and the child sees "We couldn't load this picture right now."
- **SH-03 — Privacy before storage.** Pencil text is redacted with `providers.redact_pii` before it is
  stored, logged or sent to a model. Raw text is never persisted. A redaction failure rejects the
  submission with a retryable message and spends nothing.
- **SH-04 — Allowance.** 3 character goes per book, shared by "Draw again" and the character pencil
  (inside the existing 15-image prelude, no budget change). 5 page pencils per book. Every paid edit
  calls `check_image_budget()` first; the page pencil is disabled when page pencils are used up or the
  job's `image_count` has reached `IMAGE_BUDGET`. Other versions cost no images. A go is spent only
  when an image is produced (see edge cases for refusals).
- **SH-05 — Holds.** A flagged pencil text or result enters the ADR-080 teacher hold with neutral child
  copy ("Your teacher is taking a look"). The child never sees a moderation category. At the reveal
  the run stays paused; on a finished book the book stays readable with its current pictures, and only
  the pencil request waits.
- **SH-06 — Character child changes.** A kept character pencil text is stored on the character as an
  ordered list of child changes, separate from the analysed description (ADR-069's description stays
  unmutated). `build_prompt` renders them into later scene prompts after the description, through
  ADR-035's style filter. Additive, defaulted contract field; no `schema_version` bump (ADR-029 §3
  precedent).
- **SH-07 — States and focus.** Every tool has loading ("Changing your picture…"), error, disabled
  (with the reason: "No pencils left for this book"), and empty states. Opening a tool moves focus to
  its first control; Escape or Cancel closes it and returns focus to the control that opened it; Enter
  submits. Controls have accessible names that include the character name or page number. One tool
  request per book is in flight at a time; the others are disabled while it runs.
- **SH-08 — Exact, idempotent requests.** Each request carries the picture it was made from (path or
  version token). A request whose source is no longer current is rejected without spending. A repeated
  submit (double click, two tabs, retry after a network error) is deduplicated and spends at most
  once.
- **SH-09 — Book edits after completion.** Page tools appear only on a `complete` book that is not held
  and not stopped. An edit updates `jobs.pages` for that page and the delivery guard's eligibility for
  the new picture. Page edits run in a small worker task outside the graph that reuses `edit_image`
  and output moderation; `jobs.pages` is the book. The checkpointed `StoryMemory` is not changed: it
  stays the pipeline's record, and the US-06 log holds the edits (OD-01).
- **SH-10 — Child's words as written.** Pencil text is sent to the edit model as the child wrote it
  (after redaction), in any language; it is never translated or rewritten by another model (OD-06).

## 4. Edge cases

| Case | Expected behaviour | Home |
|---|---|---|
| Pencil text empty or whitespace | Submit disabled | AC-07 |
| Pencil text over the cap | Input stops at the cap; count shown | AC-07 |
| Pencil text contains a name, school or address | Redacted before storage and before the model | SH-03 |
| Pencil text is unsafe | Held for the teacher; no image drawn; neutral copy | AC-08, SH-05 |
| Moderation false alarm on harmless text | Held; teacher allows it; the edit then runs | SH-05 (rate is rank 2's audit) |
| Pencil text in Filipino or Taglish | Moderated and sent as written; whether the edit model follows it is unmeasured and logged | SH-10, AC-22 |
| Text is not about appearance ("make him fly") | Treated like any change; the child judges the result | AC-09, AC-18 |
| Text contradicts the story ("blue hair", story says black) | Allowed; on keep it becomes a child change used by later pages | AC-12, SH-06 |
| Text uses a style-forbidden trait ("glowing" under comic) | Stored verbatim; filtered out of rendered prompts per ADR-035 | SH-06 |
| fal content checker refuses the edit | No image; the child sees "We couldn't change this picture. Try different words."; no go spent | SH-04 |
| Edit returns a picture that fails moderation | Held under ADR-080; old picture stays; go spent (an image was paid) | AC-10, AC-18, SH-05 |
| Edit result is a different wrong picture | The child picks "Use the old one" | AC-11, AC-19 |
| Classifier error on text or picture | Not a flag; retryable message; nothing spent | SH-02 |
| Child leaves before choosing keep or old | Old picture stays current; new one remains another version | AC-11 |
| Child closes the tab mid-request | Request completes server-side; result waits for the keep/old choice on return | SH-08, AC-11 |
| Double click or two tabs | Deduplicated, one spend | SH-08 |
| Request made from a picture that has since changed | Rejected, nothing spent; the view refreshes | SH-08 |
| Character goes used up | Pencil and "Draw again" disabled with the reason; other versions still work | SH-04, AC-04 |
| Page pencils used up, or `image_count` at 55 | Page pencil disabled with the reason; other versions still work | SH-04 |
| Character has no picture (species-only) | No tools for that character | AC-06 |
| Character accepted on its first draw | No other versions until the child changes it | AC-05 |
| An unchosen draw fails moderation when opened | Marked excluded, not shown; no hold | AC-03 |
| "Draw again" replaces a picture the child liked | The old picture is another version; picking it costs nothing | AC-02, AC-05 |
| An earlier picture was flagged or withdrawn | Never offered as a version | AC-02 |
| An earlier picture was flagged, then teacher-allowed | Not kept as a version: a teacher can withdraw only the current picture (decided 2026-11-01, ticket 04) | AC-02 |
| Held pencil result: teacher requests a replacement | The same edit runs once more in ADR-080's replacement slot | AC-10, AC-18 |
| Held page pencil result: teacher stops it | Only the request ends; the book stays | AC-18 |
| Baseline job: flag on a tapped redraw | One redraw from the recorded prompt, chip kept | AC-23 |
| Baseline job: that redraw flags too | Job fails as today | AC-24 |
| Baseline job: flag on an initial reference | Untargeted re-mint as today | AC-25 |
| Pencil on a page of a book held for the teacher | Tools hidden until the hold resolves | SH-09 |
| Book stopped or failed | No page tools | SH-09 |
| Book approved, child edits a page | Confirm first; then pending, out of the gallery | AC-20, AC-21 |
| Teacher approves while a page edit is in flight | Approval applies; the kept edit then returns the book to pending | AC-20 |
| Teacher review note (ADR-081) points at a page | The child can use the page tools; no link between note and tool | US-04 |
| Setting turned off after submission | Tools stay for that job | SH-01 |
| Job submitted in baseline moderation mode (no holds) | No pencil or version tools | SH-01 |
| PDF export after an edit | Uses the current `jobs.pages` picture | AC-15 |
| Story deleted | Kept versions, pencil results and log rows are deleted with it | AC-22 |
| Old checkpoint without the new fields | Defaults apply: no child changes, no kept unchosen draws | SH-06 |
| Corpus runs | Never exercise the tools (`build_corpus` auto-confirms) | §1.1 |

## 5. Design decisions and rationale

- **The child judges; checkers stay out of it.** Pencil results skip the consistency judge. Reason
  (owner): the reference checker wrongly fails about 4 in 10 clean references
  (`model-probes-2026-10.md`), and judging what the child asked for brings back false alarms.
  Moderation is never skipped.
- **Edit the current picture, don't redraw.** Reason: a redraw is today's dice roll that breaks what
  the child liked. Evidence: change-phrased instructions fixed 5 of 9 references and carried onto 5 of
  6 pages; target-phrased chips fixed 2 of 9. Children's own wording is unmeasured.
- **Keep-or-old replaces the unconditional overwrite** for the pencil. Reason: a miss costs one go,
  not the picture the child liked. "Draw again" still overwrites, but the old picture becomes another
  version, so both changes are undoable with one rule (OD-02).
- **Child changes are stored apart from the description.** Reason: ADR-069 keeps the analysed
  description unmutated; pages still need the change or they disagree with the reference (audit 01).
  This amends ADR-069's "not a second author of canonical identity" for the child only.
- **Page edits never touch character canon.** Reason: a page edit is local; propagating it would
  re-open the contradiction question for every page.
- **Unchosen reference draws are kept and moderated lazily.** Reason: already paid for; moderation
  is spent only on what the child opens.
- **Approval resets on any page change.** Reason: review is whole-book; page-level approval is a new
  review model and rank 3's area.
- **Budget:** 3 character goes unchanged; 5 page pencils within `IMAGE_BUDGET`. *Inferred* from the
  October stage audit's draw counts that a typical book leaves headroom; not measured per book.
- **ADR-082** amends ADR-029 §2 (pencil as an edit; keep-or-old; kept and earlier pictures as
  versions) and ADR-069 (free text; child changes rendered into scene prompts).
- **Research record.** Each pipeline change gets a `research-changelog.md` row. The corpus, stage
  audit and judge dataset describe the pipeline without these tools.

## 6. Verification

Seams confirmed by the owner on 2026-11-01:

1. **Pure projections** (pytest, no mocks): the reveal payload's versions, goes and pencil
   availability; `build_prompt` rendering child changes through the style filter.
2. **API** (pytest, FastAPI test client, `backend/providers.py` mocked): pencil and version endpoints
   for redaction-before-storage, moderation routing to holds, allowance and budget, idempotency,
   stale-source rejection, approval reset.
3. **Worker** (pytest, providers mocked): the character edit path in `char_bible` and the page-edit
   task, including fal refusal and flagged results.
4. **Frontend** (vitest, existing `process/[jobId]/page.test.tsx` and the book page tests): states,
   focus, Escape/Enter, disabled reasons, keep/old, confirm-before-unapprove.
5. **Browser** (Playwright on a seeded synthetic classroom, feature on): one pass per story US-01–US-05.
6. **US-07** (pytest, providers mocked): a flagged tapped reference in a baseline job redraws once
   with the recorded prompt containing the chip; the untapped path is unchanged.

Precedents: the reveal and confirm tests from ADR-069, rank 2's hold tests (tickets 05–15). Each new
test fails first for the intended reason (`AGENTS.md`). Nothing here has been run; this spec
establishes no passing behaviour.

## 7. Decisions and readiness

All open decisions were resolved by the owner on 2026-11-01, taking each recommendation.

| ID | Decision | Resolution | Home |
|---|---|---|---|
| OD-01 | How a finished book is edited | A worker task outside the graph; `jobs.pages` is the book; the checkpoint is unchanged | SH-09 |
| OD-02 | Earlier pictures as versions | Yes; makes "Draw again" undoable at no image cost (pivot) | AC-02, AC-05 |
| OD-03 | Unchosen draw fails moderation on open | Marked excluded and skipped; no hold | AC-03, AC-14 |
| OD-04 | Where logs and kept pictures live | A new job-owned table with RLS, deleted with the story (schema change approved) | AC-22 |
| OD-05 | Teacher-review mode required | Yes; tools only on `teacher_review_v1` jobs (pivot) | SH-01 |
| OD-06 | Filipino/Taglish text | Sent as written and logged; never translated (pivot) | SH-10 |
| OD-07 | How a page pencil holds on a `complete` book (owner, 2026-11-01, ticket breakdown) | Reuse `job_moderation_reviews` with pencil kinds; the job stays `complete`, and the delivery guard, teacher queue and decision endpoint accept an open pencil review without pausing a run | SH-05, AC-18 |
| OD-08 | Teacher stops a held character pencil text at the reveal (owner, 2026-11-01) | Only the pencil request ends; the reveal returns with the old picture; the story is not stopped | SH-05, AC-08 |

**Readiness:** design ready for build tickets. Seams confirmed (§6), decisions resolved, ADR-082
accepted. This authorizes ticket breakdown, not implementation.

**Release gates, not build gates:** pencil free text does not ship before
`ptd-moderation-calibration` audit 01 resolves; ethics re-review before real children; the SH-01
setting stays off by default. US-07 is a baseline-mode bug fix and ships normally.

## 8. Sources and coverage

| Source requirement (ticket 02 comments, 2026-11-01) | Home |
|---|---|
| Conflict opened, synthetic-only, off by default, ethics re-review | §1 release gates, SH-01 |
| Free text ships after rank 2 audit 01 | §1 release gates, R-list |
| General tool, child judges, no per-defect fixes; no more paid tests | §1, §5 |
| A2 dropped | §1 exclusions |
| Other versions, moderated before shown, no image cost | US-01, US-03, SH-02, SH-04 |
| Pencil: write change, one edit, keep new or old; redact, moderate, hold; log | US-02, US-04, US-06, SH-03, SH-05 |
| Rejected: blank custom prompt; pausing per failed page | §1 exclusions |
| Contradicting change becomes this book's note, used by later pages | AC-12, SH-06 |
| Reveal: chip button stays as "Draw again", pencil beside it, shared 3 goes | AC-06, SH-04 |
| Budget: 3 character goes + 5 page pencils, within 55, disabled state | SH-04 |
| Keep unchosen reference draws, moderate on open; first-draw accept has one | AC-02, AC-03, AC-05 |
| Approved book edit returns to the teacher | US-05 |
| Pencil skips consistency checker | AC-09, §5 |
| Text defaults: about 200 characters, any language, neutral flagged copy | AC-07, SH-05, OD-06 |
| Audit 01 findings (canon conflict, lost chip on flag, rejected pages not visible) | §1.1, SH-06, edge cases |
| Probe result 2 of 9 | §1 exclusions, §5 |

| Audit option A1: keep the child's chip through a moderation flag (owner, 2026-11-01) | US-07 |
| Owner's rulings on OD-01 to OD-06 and seams | §6, §7 |
