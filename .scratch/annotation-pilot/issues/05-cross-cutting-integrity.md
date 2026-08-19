# 05 — Cross-Cutting Research Integrity Suite

**What to build:**
A global research integrity test suite (`backend/tests/test_research_integrity.py`) that fails CI if methodological constraints are violated. Dual-boundary rule: preserve internal research metadata (`story_id`, `char_id`, `split`, `source_type` / `provenance`, `is_constructed_negative`) in DB and manifest records to enable automated audits, while strictly asserting that all external surfaces (Annotation UI, ShareGPT prompts) strip all identifiers.

**Key Architectural Invariants:**
1. **Character-Disjoint Splits:**
   - Assert zero overlap of `char_id` across `train`, `val`, and `test` splits.
2. **Test-Set Integrity:**
   - Assert `test` split contains ONLY real-child donated stories (`provenance == "donated"`). Zero synthetic characters permitted in test.
   - Assert constructed negatives exist ONLY in `train` (`split == "train"`).
3. **Data Completeness & Manifest Reconciliation:**
   - Assert every non-pilot pair has verified ground truth (2 agreeing or 2 conflicting + 1 adjudicator).
   - Assert exported counts reconcile exactly with `dataset_manifest.json`.
4. **Prompt & UI Blinding Verification:**
   - Assert that serialized ShareGPT prompt conversations (`to_llamafactory.py`) contain NO `char_id`, `story_id`, character names, story titles, or split identifiers.

**Blocked by:** 04-exporter-manifest

**Status:** ready-for-agent

### Checklist & Assertions:
- [ ] Write CI tests asserting character-level disjointness across train/val/test splits.
- [ ] Write CI tests asserting test set is 100% donated real-child stories with no constructed negatives.
- [ ] Write CI tests asserting constructed negatives reside strictly in train split.
- [ ] Write CI tests reconciling dataset item counts and character counts with `dataset_manifest.json`.
- [ ] Write CI tests scanning serialized ShareGPT outputs for metadata/provenance leakage.
