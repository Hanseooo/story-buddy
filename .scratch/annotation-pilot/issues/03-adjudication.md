# 03 — Adjudication Flow & Final Label Authoritative Resolution

**What to build:**
Build the `/adjudicate` interface and server actions (`frontend/app/(research)/adjudicate/`). Surface conflicting pairs across `same_character`, taxonomy reasons (normalized set equality), `anatomy_intact`, and `text_free`. An adjudicator resolves the disagreement by submitting an authoritative third row to `annotations`.

**Key Architectural Invariants:**
1. **Adjudication Eligibility Rule:**
   - A pair is available for adjudication IF AND ONLY IF **exactly 2 independent non-adjudicator annotations exist** AND they conflict.
   - Pairs with 0, 1, or >2 annotations or pairs where Annotator A and B agree must NEVER appear in the adjudication queue.
2. **Distinct Adjudicator Identity Separation:**
   - Adjudicator MUST be a distinct researcher (`adjudicator_id != annotator_A_id` and `adjudicator_id != annotator_B_id`).
   - Verified via `profiles.is_adjudicator = true` and `auth_role() = 'researcher'`.
3. **Blinded Competing Labels:**
   - The UI presents conflicting submissions as anonymous "Annotator 1" and "Annotator 2" (or "Label A" and "Label B").
   - Strip all annotator names, user IDs, emails, and submission timestamps.
4. **Normalized Set Equality:**
   - Taxonomy comparison between Annotator A and B uses normalized set equality (ignoring array ordering).
5. **Authoritative Ground Truth:**
   - Adjudicator submits an authoritative third row in `annotations` (or updates `research_pairs.status = 'adjudicated'`).

**Blocked by:** 01-visual-fixtures, 02-annotation-ui

**Status:** ready-for-agent

### Checklist & Assertions:
- [ ] Build `/adjudicate` page fetching pairs with status `conflicted` and exactly 2 competing non-adjudicator annotations.
- [ ] Render blinded side-by-side images and anonymous Annotator A vs Annotator B labels.
- [ ] Implement conflict detection comparing `same_character`, `anatomy_intact`, `text_free`, and set-normalized `failure_reasons`.
- [ ] Implement adjudication submission action writing authoritative third row and updating `research_pairs.status = 'adjudicated'`.
- [ ] Enforce `adjudicator_id != annotator_A_id` and `adjudicator_id != annotator_B_id`.
- [ ] Write component and server-action unit tests covering eligibility, conflict detection, anonymization, and persistence.
