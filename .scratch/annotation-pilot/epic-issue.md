# [Epic] Objective 4: Research Annotation Surface, Pilot Validation & Dataset Infrastructure

## Overview & Capstone Context
This epic tracks the implementation, hardening, pilot validation, and dataset compilation infrastructure for **Objective 4: Fine-Tuning the VLM Consistency Judge** (`Qwen2.5-VL-7B-Instruct` via QLoRA with LLaMA-Factory).

To establish ground-truth labels on the held-out character-disjoint test set without introducing circularity (ADR-004) or data leakage, StoryBuddy implements a custom, blinded annotation surface (`frontend/app/(research)/annotate/` and `adjudicate/`) backed by Supabase RLS and short-lived signed URLs (ADR-026).

## Methodology & Architectural Invariants
- **Dual-Annotation Independence:** Every image pair is scored independently by two researchers (`Annotator A`, `Annotator B`) who are blinded to each other, story provenance, and model predictions.
- **Authoritative Adjudication:** Disagreements across `same_character`, the closed 7-item `failure_reasons` taxonomy, `anatomy_intact`, or `text_free` are surfaced to a distinct third researcher (`Adjudicator`) whose label serves as the authoritative ground truth.
- **Identity Isolation:** Strictly enforced invariant: `Annotator A != Annotator B != Adjudicator`.
- **Character-Disjoint Splits:** Splits are defined strictly by `char_id`. Test set consists exclusively of donated real-child stories (Ethics Stage 1). Constructed hard negatives reside in the `train` split only.

---

## Sub-Issues & Execution Roadmap

### Phase 1: Preflight & Parallel Foundations
- [ ] #44 — **00: Preflight Migration & Environment Verification**
- [ ] #45 — **01: Meaningful Visual Pilot Fixtures & Robust Seeding**
- [ ] #46 — **02: Annotation UI Hardening, Server Invariants & 3-Tier Blinding Verification**
- [ ] #52 — **08: Corpus Storage, Generation Telemetry & Cost Smoke Test**

### Phase 2: Adjudication & Exporter Hardening
- [ ] #47 — **03: Adjudication Flow & Final Label Authoritative Resolution**
- [ ] #48 — **04: Hardened Dataset Exporter, Consensus Resolution & Manifest**

### Phase 3: Verification & Automated Pipeline
- [ ] #49 — **05: Cross-Cutting Research Integrity Suite**
- [ ] #50 — **06: Automated Multi-Fixture E2E Golden-Path Test**

### Phase 4: Pilot Execution & Instrument Freeze
- [ ] #51 — **07: Human Annotation Pilot & Instrument Freeze**

---

## Post-Pilot Milestones
Upon completion of Ticket 07 (#51) and official freeze of the annotation instrument:
1. Run full corpus generation over donated child writing stories (~707 images).
2. Execute full human dual-annotation campaign (~750–1,000 pairs).
3. Export manifest and compile ShareGPT dataset via `backend/finetune/build_dataset.py`.
4. Fine-tune `Qwen2.5-VL-7B-Instruct` QLoRA adapter via LLaMA-Factory (`train_qlora.yaml`).
5. Evaluate against baselines on the character-disjoint test set per pre-registered evaluation protocol (`docs/product/PREREGISTRATION_OBJ4.md`).
