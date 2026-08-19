# 04 — Hardened Dataset Exporter, Consensus Resolution & Manifest

**What to build:**
Update `backend/finetune/build_dataset.py` with strict hard-fails for invalid states or unresolved conflicts, replacing loose warning drops. Generate `dataset_manifest.json` reporting both character counts (`num_characters`) and pair counts (`num_pairs`) across splits, class balance, failure taxonomy distributions, and SHA-256 dataset hashes.

**Key Architectural Invariants:**
1. **Deterministic Consensus Resolution Algorithm & Hard-Fails:**
   - If a pair has >2 ordinary annotator rows -> **HARD FAIL** (`ManifestError`).
   - If a non-pilot pair has <2 annotations -> **HARD FAIL**.
   - If 2 ordinary rows agree -> use agreed final label (status `complete`).
   - If 2 ordinary rows disagree and exactly 1 valid adjudicator row exists -> use adjudicator final label.
   - If 2 ordinary rows disagree and NO adjudicator row exists -> **HARD FAIL**.
   - If 2 ordinary rows agree and an adjudicator row exists -> **HARD FAIL** (invalid state).
2. **Pilot Data Exclusion:**
   - Categorically exclude `is_pilot = true` rows from production dataset export.
3. **Character and Pair Counts in Manifest:**
   - `dataset_manifest.json` must record both character counts (`characters`) and pair counts (`natural_pairs`, `constructed_pairs`) per split (train, val, test) and overall.
4. **Single Polarity Inversion Seam:**
   - Maintain `label = not agreed.same_character` in `build_records` as the single authoritative conversion site (`label = True` is `different_character`).

**Blocked by:** 03-adjudication

**Status:** ready-for-agent

### Checklist & Assertions:
- [ ] Implement strict resolution algorithm and hard-fail error triggers in `backend/finetune/build_dataset.py`.
- [ ] Strictly filter out `is_pilot = true` rows during production dataset export.
- [ ] Include detailed split statistics in `dataset_manifest.json`: character counts, natural/constructed pair counts, taxonomy breakdown, adjudication rate, and SHA-256 hash.
- [ ] Write unit tests for consensus resolution (2 agreeing, 2 conflicting + 1 adjudicator, >2 annotators fail, unresolved conflict fail, invalid adjudicator fail).
