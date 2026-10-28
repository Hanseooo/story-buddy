# ADR-079 — Researchers can inspect failed and unapproved runs

**Status:** Accepted (2026-10-26), owner confirmation during the moderation-calibration interview.
Specification work only; implementation has not been authorized in this session.
Amends ADR-064 decisions 2 and 6 and its approved-only researcher restriction. The owner selected
the full existing run viewer for all researchers during the moderation-calibration interview.

**Context:** Researchers need to investigate moderation failures, including run `314fafc9`, using
the story context, generated image attempts and recorded verdicts. ADR-064 currently permits only
the adjudicator to inspect failed and unapproved runs. Other researchers receive `403 not_approved`;
a failed book cannot be teacher-approved, so that restriction prevents them from inspecting the
failure. A short run ID and `scene_safety` do not establish a false alarm or identify which
classifier flagged an image. This record makes no finding about that run.

**Decision:**

1. A signed-in account with `role = 'researcher'` may open the full existing run viewer for any
   existing job, regardless of `approved_at`, job status or `is_adjudicator`. The backend
   `GET /research/runs/{job_id}` enforces this rule on every request. Signed-out requests remain
   401, other roles remain 403, and unknown jobs remain 404.
2. The run list uses the same eligibility rule for titles and run links: every researcher can see
   the existing title and open every run. Signed-out visitors and other roles retain their existing
   title and detail restrictions. Remove the approved-only message for researcher viewers.
3. Expose the existing projected response: redacted story text, characters, prompts, signed images
   for retained attempts, recorded verdicts and moderation statuses, steps, timing, costs and
   projected state. Preserve ADR-064's exclusions of `input.raw_text`, `jobs.input_text`,
   `profile_id` and `classroom_id`. Preserve private Storage and existing signed-URL lifetimes.
   Missing images, checkpoints or verdicts remain unavailable, never inferred or reconstructed as
   historical evidence. This decision adds no logging or historical classifier fields.
4. Inspection grants no authority to approve a book, release a flagged image, resume a run or
   change moderation. Teacher release of flagged images remains a separate moderation decision.
   The existing annotation and adjudication permissions remain unchanged.
5. Retain the backend checkpoint projection as the data source, the existing Langfuse-link flag
   and warning, and the existing database RLS policies. This is a change to authorization for the
   run-viewer endpoint and its frontend presentation, not direct researcher table access or a
   public trace-sharing change.

**Consequences and ethics:** Every researcher account, including annotators, gains access to
unapproved child-derived content and potentially unsafe images. Redaction does not make a story
anonymous or an image safe. This deliberately replaces ADR-064's one-account exception to the
approved-only consent boundary with a researcher-role exception. The owner accepted
that access expansion; this record does not claim participant consent or ethics approval has
been obtained. Researchers can examine actual retained attempts rather than diagnose from a
failure label, but absent classifier reasoning still requires other evidence. Revoking access
later cannot recall content already viewed or downloaded.

**Verification required before completion:**

- An ordinary researcher can open both failed and complete-but-unapproved runs, see their titles
  and retained content, and continue to open approved runs. An adjudicator retains the same access.
- Signed-out and non-researcher requests remain denied at the backend, including direct requests;
  unknown jobs remain 404. Private-field exclusions and signed-image behavior remain enforced.
- Existing loading, empty, missing-data, error and navigation states continue to work. Update
  `docs/specs/research-run-browser.md` and affected access tests with implementation. Verify with
  the project's backend and frontend pre-merge commands and report any unperformed hosted checks.

**Alternatives:** Keep adjudicator-only inspection, which preserves the narrower access boundary
but prevents ordinary researchers from investigating failed runs. Expose operational diagnostics
only, which limits content access but cannot support independent review of the rejected images.
The owner selected the full viewer after these tradeoffs were explained.

**Sources:** [ADR-064](./ADR-064-the-run-viewer-reads-checkpoint-history-through-a-researcher-only-endpoint.md),
[research run browser spec](../../specs/research-run-browser.md), `backend/app/research.py`, and
the owner's Q4 answer in the moderation-calibration interview (2026-10-26).
