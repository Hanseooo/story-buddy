# 01 — Audit: review decisions and what a child sees

**Status:** needs-owner-verdict
**Type:** research
**Progress:** answered 2026-10-29, awaiting owner
**Blocked by:** None
**Conflict gate:** `teacher-review-and-approval.md` §12–13. Reading is allowed. Proposing a design
that shows a decision to a child needs the owner's verdict first.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

What does a review decision store and show today, and what would feedback that a child can see
and act on require, including teacher comments and highlights on story text?

## Starting evidence (2026-10-25)

- `jobs` stores only `approved_at` and `rejected_at`, mutually exclusive
  (`supabase/migrations/0011_jobs_rejected_at.sql`). No reason or comment field exists.
- Decisions go through `POST /jobs/{id}/review` (`backend/app/review.py:31`). The teacher screen has
  Pending, Approved and Rejected tabs (`frontend/app/classroom/[classroomId]/books/page.tsx:14`).
- The spec deliberately hides rejection from the child (`docs/specs/teacher-review-and-approval.md:534`,
  `:550`).
- `jobs.input_text` is the raw, pre-redaction story (`AGENTS.md`), so it is not a safe anchor for
  comments a classmate could reach.

## Investigate

- Every child-facing surface that renders a book's review state today.
- What a child can do with feedback. Is there a revise-and-resubmit path? A resubmit is a new paid
  run, so find the cost and the image budget.
- Wording a child reads as encouraging rather than rejected. Check existing kid-facing copy rules.
- A comment data shape: who writes it (the classroom's teacher), who reads it (the owning child, never
  classmates), RLS, retention, and how it interacts with `docs/specs/storybook-deletion.md`.
- Whether teacher comments need PII redaction (a teacher may write a child's name).
- Highlights: which text they anchor to (page text, not `input_text`), what happens if that text
  changes, and tap-to-open notes on mobile with accessible names.
- What an ethics re-review would need to cover.

## Edge cases the answer must cover

- A comment written about a child that the child should not read.
- A book deleted while comments exist.
- A teacher changes a decision after the child has seen feedback (Undo exists today).
- The child is offline or not logged in when feedback arrives. How do they find out?

## Done when

- Findings are labelled *measured* or *inferred*, with file references.
- Options for wording, the child's next step, the comment model and highlights, each with tradeoffs.
- The schema change and the ethics item each option needs.
- Cost estimate and a go/no-go.

## Comments

## Answer

**Method.** Read-only, $0, nothing run. *Measured* = read in the file cited. *Inferred* = reasoned from
what was read, not checked. Wording below is a draft for the owner, not copy to ship.

### Bottom line

**Conditional go on teacher comments. Highlights are a later ticket. No-go on three shapes** (a note
column on `jobs`, a child editing story text, a child reply thread). Every "go" needs the owner to
amend `teacher-review-and-approval.md` §4.10 and §12–13 first, and an ethics re-review before real
children see a note. This audit grants neither.

### Findings

**What a decision stores and shows**

1. A decision is two mutually exclusive timestamps and nothing else. *Measured:*
   `0011_jobs_rejected_at.sql`, `backend/app/review.py:16-27`. No reason, comment, actor or history.
   The teacher id is only logged.
2. The teacher's three verbs are `approved | rejected | pending` (`review.py:14`). "Pending" is the
   Undo target. *Measured.* Changing a label in the teacher UI changes no API value.
3. **A child's browser already receives both timestamps.** `useJob.ts:69` selects `approved_at,
   rejected_at` for the owner, and `students read own jobs` has no column filter
   (`0008_authorization_surface.sql:24`). *Measured.*
4. **Drift: the child already sees a review signal.** `book/[jobId]/page.tsx:340-345` shows the owner
   "Your teacher needs to approve this book before you can download it." whenever `approved_at` is
   null, and `page.test.tsx:113,186` pins it. ADR-071 (2026-10-21) added the download button.
   Spec §4.10 and §13.6 say every kid surface renders the same for all three states. Today a child
   can tell approved from not-approved. They still cannot tell rejected from pending. *Measured.*
   Flagged, not reconciled.
5. The bookshelf (`s/[profileId]/page.tsx`) shows no review state, only the `teacher-held` bucket
   (ADR-080, a moderation hold, not a review decision) and failed books. *Measured by grep for
   `approved|rejected`.*
6. Why the spec hides rejection: a verdict with no adult present, and a "waiting for your teacher"
   that never decays (§4.10). §12 says a reason field is "a place to write something about a child
   that the child cannot see" and needs "its own ethics pass". *Measured.*

**Channels and cost**

7. No email, no push (`teacher-review-and-approval.md:325`). Gallery freshness is per navigation, no
   Realtime (`classroom-sharing.md:120`). *Measured.* A child learns of feedback only on opening the
   app. The bookshelf likely fetches per visit. *Inferred.*
8. Resubmitting is a new job and a new paid run (`kid-flow-failure-semantics.md` §4.3-4.4). Cost per
   completed book is about $0.27-0.65 (`image-model-research-2026-10.md:149`, ADR-001:25). One run's
   structural ceiling is 55 images (`spend-and-retry-economics.md` §1), about $1.5 at the measured
   $0.027 per call. *Measured from docs; no live price check.* The existing `revise` path is offered
   only for a `child_text` failure (§4.3). Whether a finished book has a "make another from this"
   entry was not checked.
9. No kid-facing copy style guide exists. `DESIGN.md` covers fonts and layout only. The only written
   posture is "a child is never told their own writing was the problem"
   (`kid-flow-failure-semantics.md` §4.10). *Measured by grep.*

**Data shape**

10. **A note column on `jobs` would leak to classmates.** `students read approved peer jobs`
    (`0008:28`) and `researchers read approved jobs` (`0008:46`) select the whole row, with no column
    filter. Any column added to `jobs` is readable by both once the book is approved. *Measured.*
11. `jobs.input_text` is raw. `pages[].caption` is an excerpt of `redacted_text or raw_text`
    (`segment.py:353,383,447`), so captions are the safe anchor. *Measured.* The `raw_text` fallback
    means an unredacted caption is possible if redaction is absent. *Inferred, not traced.*
12. `pages` is written once by `_finish`, and a terminal job is immutable
    (`teacher-review-and-approval.md:37`, `kid-flow-failure-semantics.md` invariant 2). Anchors into
    captions do not move. *Measured from spec text, not from a code search for other writers.*
13. Presidio exists as `providers.redact_pii`, used on child title and text at submit
    (`main.py:166-167`). Nothing redacts teacher-authored text today. *Measured.*
14. The private-table precedent is `job_moderation_reviews` (`0022`): RLS on, `revoke all` from
    `authenticated`, service_role only, reached through FastAPI. ADR-080 already extends storybook
    deletion to cascade-remove those rows. *Measured.*
15. Deletion removes the `jobs` row last, after four stores (`storybook-deletion.md` §1). A table with
    `on delete cascade` to `jobs` is covered by that last step. *Inferred.*

### Edge cases

| Case | Answer |
|---|---|
| Comment about a child that the child must not read | Two kinds of note. A private teacher note never leaves the teacher API. A child note is shared only by an explicit send, with a preview. Never one field. Option C2. |
| Book deleted with comments | `on delete cascade` to `jobs`. No separate store, so nothing to add to the four-store cleanup (#15, confirm in the build spec). |
| Decision changed after the child saw feedback | Tie the note to the book, not the decision. Undo leaves the note. The teacher can withdraw a note (`withdrawn_at`); the child then sees it gone, with no explanation. |
| Child offline or logged out | No push channel (#7). A badge on the book's bookshelf card at next visit. |
| Teacher writes a child's name | Child notes pass `redact_pii` on send, and the teacher sees the redacted text before it goes. Private notes are stored as written and never reach a child or classmate. |

### Options

**W. Wording**
- **W1 Keep as is.** Teacher sees Reject, child sees nothing. $0. Does not answer the panel.
- **W2 Soften the teacher's label, child still sees no verdict.** Draft: "Share with class" / "Not
  ready to share yet". No API or schema change. Fixes the harsh word where it is read. Weak: the child
  gets no feedback.
- **W3 Child sees a note, never a verdict.** "A note from your teacher", shown only when one was sent.
  No approved/rejected word child-facing. Pair with W2. **Recommended.**
- **W4 Child sees "Shared with class" or nothing.** Extends finding #4. A missing badge is a rejection
  signal, which §4.10 forbids for `classroom-sharing` ("an absence badge"). Not recommended.

**N. Child's next step**
- **N1 Read-only note**, badge on the bookshelf card. $0. **Recommended first.**
- **N2 N1 plus an optional "Start a new version" link** into the editor with text prefilled. One paid
  run per click, $0.27-0.65, ceiling about $1.5. Never gated, as `revise` never gates. Needs the entry
  point checked (#8).
- **N3 Child edits page text in place.** No-go: breaks immutable `pages` (#12) and ADR-013.
- **N4 Child replies to the teacher.** No-go here: child free text, ADR-029 §2 and rank 4's gate.

**C. Comment model**
- **C1 One text column on `jobs`.** No-go (#10). No history, and Undo is ambiguous.
- **C2 Table `job_review_notes`.** Columns: `id`, `job_id` (cascade), `author_id`, `kind`
  (`private|child`), `body`, `scene_id` and `anchor` (nullable), `sent_at`, `withdrawn_at`,
  `created_at`. Service-role only, like `0022`. The child reads through one owner-checked endpoint
  returning only `kind=child`, sent, not withdrawn. Classmates and researchers get no path.
  **Recommended.** A migration plus endpoints plus two UI surfaces, so the §5 gate applies.
- **C3 Threads.** No-go (N4).

**H. Highlights** (later ticket, per the 2026-10-25 grill)
- **H1 Whole-page notes** (`scene_id` only). Smallest. No text selection needed on mobile.
- **H2 Sentence-level.** Anchor is `scene_id` plus sentence index (a caption is sentences joined by
  spaces). Teacher taps a sentence, no drag handles. Stable because `pages` is immutable.
  **Recommended** for mobile.
- **H3 Character ranges.** Free selection. Long-press selection fights the OS menu on phones. Highest
  cost and risk.
- Child view: the highlighted text is a real `<button>` named "Teacher note on page 3: <note>", opening
  an inline panel closable by button or Escape. No hover tooltip, since touch has none. If a caption
  ever changes, show the note at page level instead of dropping it.

### Schema and ethics per option

| Option | Schema | Ethics item |
|---|---|---|
| W2 | none | copy review |
| W3 + N1 + C2 | new `job_review_notes`, `jobs` untouched | Amend §4.10 and §12-13. Re-review adult free text shown to a child, the private/child split, redaction on send, retention tied to book deletion, no researcher or export path. |
| N2 | none | A child may feel pressed to redo; disclose the cost to the teacher. |
| H2 | `scene_id`, `anchor` (in C2 if built together) | Same as C2, plus an accessibility check on the tap panel. |

### Cost and go/no-go

- Build cost in dollars: **$0**. Verify with synthetic seeded jobs, no generation. A live N2 check is
  one paid run per attempt, to be proposed separately.
- Build size, *inferred*: migration, review/notes endpoints, teacher books page, child book page,
  bookshelf card. More than three modules, so the §5 gate applies to the build spec.
- **Go:** W2 + W3 + N1 + C2, then H2 as its own ticket.
  **No-go:** C1, N3, N4/C3, W4.
  **Blocked on the owner:** (a) the §4.10 amendment; (b) finding #4, either keep the "needs to
  approve" copy and amend §4.10 to say so, or drop the reason text and only disable the button;
  (c) the ethics re-review before any child sees a note.

### For ticket 02

Decisions for the grill: the §4.10 verdict; private versus child notes; whether an approved book can
carry a note; the teacher's redaction preview; N2 yes or no; whether a bookshelf badge for a present
note is acceptable given §4.10's "absence badge" rule (it is not an absence badge, but the owner
should say so).
