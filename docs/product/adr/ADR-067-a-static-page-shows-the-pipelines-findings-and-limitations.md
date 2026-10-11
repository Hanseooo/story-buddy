# ADR-067 — A static page shows the pipeline's findings and limitations

**Status:** Accepted (2026-10-11) · the owner asked for the page; the decisions below are how it was
built and are the owner's to change at review · extends ADR-065 and ADR-066, which are not edited ·
adds one public frontend route · no backend route, no migration, no `StoryMemory` or `contracts/`
change · no Supabase read · no new dependency

**Context:**

On 2026-10-11 the owner asked for the study's limitations and pipeline findings to be shown on the
research site: duplicates, the edit model's defects, the human and non-human split, and the scene
editor against the others that were tried. A first answer changed one line of the docs hub so that
it pointed at the file. The owner rejected that as not usable.

What the code and documents say, checked on 2026-10-11:

- **`/research/results` is scoped to the judge.** ADR-066 decision 5 lists what it shows, and its
  title is "Judge results". The pipeline's defects are a different question.
- **The plain-language statement already exists.** `group-guide.md` §5.1, §5.3, §5.4 and §6 give the
  numbers, the table of what was tried and the nine limitations. The counts by defect and what the
  two automatic checks did are in `pipeline-stage-audit-2026-10.md`, "Provisional results".
- **The audit is provisional.** AI reviewers scored it and the owner has not confirmed the scores.
- **Phase 0.5 is not a finding.** `PHASE_05_RESULTS.md` says no Phase 0.5 number may appear as a
  finding in the paper without a fresh blind re-score. The guide repeats the numbers with that
  warning.
- **Epic #102 requires an ADR before a new route** and allows synthetic material only.
- **The results page says to extract `Source` and `ScrollTable` on their third use.** This page is
  the third.

**Decision:**

1. **`/research/limitations` is a public static route** in the same route group as the dataset,
   results and docs pages. It fetches nothing and reads no session, inherits that group's
   `error.tsx`, has a header tab, and is linked from `/research`.

2. **It shows six things:** the defect rate split by character kind, the most common major
   defects, what the reference check and the page check said about the reviewed images, the scene
   editor against FLUX.2 klein and OmniGen2, every October test of a fix, and the nine limitations.

3. **Every number comes from a tracked file and names it.** The sources are `group-guide.md`,
   `pipeline-stage-audit-2026-10.md`, `model-probes-2026-10.md` and `PHASE_05_RESULTS.md`. A unit
   test reads those files and fails when a number on the page is not printed there.

4. **The table of what was tried and the list of limitations are the group guide's own words.**
   The test compares them with §5.4 and §6 row by row and item by item. The page adds one short
   outcome label per row and one area label per limitation, and nothing else.

5. **The page says the audit is provisional**, near the top, and says who scored it.

6. **The Phase 0.5 numbers are shown as a build check, not as a finding.** The card says it was
   scored without blinding, that both runs failed the gate, and that it is not a finding of the
   study.

7. **No picture is shown.** An example image in a public repository stays in its history for good
   (ADR-065 consequences), and ADR-065 decision 6 has the owner choose such images. Adding them is
   a later change.

8. **Donated material does not appear.** The audit reviewed synthetic stories only. A test fails if
   the page or its data contains `don-`.

9. **`Source` and `ScrollTable` move to `frontend/app/(research)/_shared/components/`**, and the
   dataset and results pages import them.

**Consequences:**

- The page works with Supabase and the backend down.
- The group guide is now copied by a public page. A change to §5.1, §5.3, §5.4 or §6, or to the
  audit's "Provisional results", fails the test until `limitations/data.ts` follows. The guide says
  so at its top.
- Provisional numbers are public. If the owner's confirmation changes them, the page changes with
  the documents.
- The limitations are stated in two public places, the guide and this page. The test keeps them
  identical.
- The header has five public tabs. The row already wraps on a phone.

**Alternatives considered:**

- **Point the docs hub at the file.** Tried first (`94a3baa`) and rejected by the owner: a reader
  still has to open a long document on GitHub to find the limitations.
- **Add a section to `/research/results`.** Rejected: that page answers what the judge scored
  (ADR-066). The pipeline's defects need their own caveats beside them, the same reasoning that kept
  the results off the dataset page.
- **Render the guide's markdown.** Rejected for the reason ADR-065 gives: no markdown renderer, and
  the build was never checked to see `docs/`.
- **Write new wording for the limitations.** Rejected: a third statement of the same facts drifts.
  Copying the guide and testing the copy keeps one statement.
- **Show example pages for each defect.** Deferred, per decision 7.
