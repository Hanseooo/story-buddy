# 06 — Automated Multi-Fixture E2E Golden-Path Test

**What to build:**
A comprehensive end-to-end integration test (`backend/tests/test_annotation_pipeline_e2e.py`) validating the entire research pipeline across a 3-fixture test matrix from Supabase seeding through annotation, adjudication, dataset compilation, and ShareGPT serialization.

**Key Architectural Invariants & Test Matrix:**
1. **Fixture A (Unanimous Agreement Path):**
   - Annotator A and B submit identical labels (`same_character = true` or matching reasons).
   - Pair resolves automatically to `status = 'complete'`.
   - Adjudication queue remains empty for this pair.
   - `build_dataset.py` exports agreed label to manifest.
2. **Fixture B (Disagreement & Successful Adjudication Path):**
   - Annotator A and B submit conflicting labels (`same_character` mismatch or taxonomy difference).
   - Pair transitions to `status = 'conflicted'`.
   - Pair enters adjudication queue; distinct Adjudicator submits 3rd row (`status = 'adjudicated'`).
   - `build_dataset.py` resolves consensus using Adjudicator label and exports to manifest.
3. **Fixture C (Disagreement & Unresolved Failure Path):**
   - Annotator A and B submit conflicting labels.
   - NO Adjudicator row is submitted.
   - `build_dataset.py` attempts export -> strictly raises `ManifestError` and aborts.

**Blocked by:** 05-cross-cutting-integrity

**Status:** completed

### Checklist & Assertions:
- [x] Write end-to-end integration tests implementing Fixtures A, B, and C.
- [x] Assert valid ShareGPT output for Fixtures A and B.
- [x] Assert strict export failure for Fixture C.
