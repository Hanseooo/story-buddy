# 07 — Human Annotation Pilot & Instrument Freeze

**What to build & conduct:**
Execute the human pilot with two independent researchers and one adjudicator across the 17 meaningful visual fixture pairs. The pilot is an **instrument diagnostic, UX smoke test, and protocol freeze gate**, verifying UI ergonomics, signed URL latency, taxonomy rubric clarity, queue transitions, and export mechanics before the full ~750-1000 dataset annotation campaign.

**Key Architectural Invariants & Scientific Framing:**
1. **Instrument Diagnostic Scope:**
   - Over N=17 adversarial pairs, agreement metrics (raw agreement, confusion categories, adjudication rates) serve as diagnostic feedback to refine the annotation guide and UI.
   - It is explicitly NOT a statistical claim of inter-rater reliability (Cohen's κ over 17 samples is underpowered; formal IRR is evaluated during the full research protocol).
2. **Diagnostic Records:**
   - Record median/p95 annotation latency per pair.
   - Record specific taxonomy confusions or ambiguous visual features.
   - Verify zero signed-URL timeouts or image loading failures.
3. **Formal Instrument Freeze:**
   - Upon successful export of the pilot and review of diagnostic findings, the annotation guide, taxonomy definitions, and UI are officially **frozen**.

**Blocked by:** 01-visual-fixtures, 02-annotation-ui, 03-adjudication, 04-exporter-manifest, 05-cross-cutting-integrity, 06-automated-e2e

**Status:** ready-for-agent

### Checklist & Assertions:
- [ ] Two independent researchers annotate 17 meaningful pilot pairs in `/annotate`.
- [ ] Adjudicator resolves any conflicting pairs in `/adjudicate`.
- [ ] Export process completes successfully for pilot validation.
- [ ] Record diagnostic metrics: completion time, disagreement types, UI/URL performance notes.
- [ ] Confirm and officially freeze the annotation instrument and guide.
