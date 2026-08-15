# ADR-004 — Consistency via VLM-as-judge control loop; human ratings as headline metric

**Status:** Accepted · **amended 2026-07-10** (judge model + verdict schema) · **amended 2026-07-10b**
(the judge is fine-tuned — ADR-018; the safety rubric is not — ADR-011). The decision itself stands.

**Context:** Whole-image CLIP embeddings are dominated by background/pose/scale and degrade on stylized and non-human characters — unreliable both as a control signal and as an eval metric. Using the same automated score to drive regeneration *and* report results is circular.

**Decision:** Use a **VLM-as-judge** (open-weight vision model — `google/gemma-3-27b-it`, ADR-002) as the runtime control signal: given the reference + a generated scene, return a structured verdict (same character? attributes present? style match?) plus **failure reasons**. Use **human ratings as the headline research metric**; report **VLM–human agreement** as a secondary result that validates the automated metric. For multiple characters, verify **each character separately** against its own reference (max 2 canonical refs, v1).

**Amendment (2026-07-10) — reason-then-score verdict schema.** VLM judges are a known-weak instrument for true *instance identity* discrimination: they conflate category and scene similarity with identity (NearID, [arXiv:2604.01973](https://arxiv.org/abs/2604.01973)). The mitigation is established: an explicit rubric plus **reason-then-score** ordering reaches ~79.6% human agreement (DreamBench++, [arXiv:2406.16855](https://arxiv.org/abs/2406.16855)). Therefore the verdict model in `backend/contracts/` **must** order its fields so the judge writes free-text `differences_observed` **before** it emits `same_character`. Field order is load-bearing in structured output — it forces the reasoning to condition the verdict rather than rationalize it.

**Amendment (2026-07-10b) — two calls, two concerns, never merged.** The judge is fine-tuned
(ADR-018). ADR-011's *image safety rubric* currently runs on the same base model, and that
coincidence must not become a coupling. **The fine-tuned model never sits on the child-safety
path.** Consistency is a quality signal with a best-of fallback; safety is a gate with no fallback.
A student-trained LoRA is an acceptable risk for the first and an unacceptable one for the second.

**Consequences:** Robust on non-human/stylized characters; interpretable failures enable *targeted* regeneration (ADR-010); no circularity in the paper; a bonus publishable result (metric validation). The judge is a *signal*, not an oracle — ADR-010's best-of fallback is what keeps a shaky verdict from producing a broken page.

**The non-circularity argument, stated once so it can be cited.** The judge drives regeneration inside
the pipeline. It is therefore **never** an outcome measure. The acceptability outcome is the **expert
validation** (Objective 3), and software quality is the **ISO/IEC 25010** questionnaire (Objective 5) —
neither of which the judge optimizes. The judge's own classification accuracy (Objective 4) is measured on a
human-labeled, character-disjoint held-out set it never trained on. **The expert validation is never scored
using the judge.** Panels ask this question; the answer lives here.

**Alternatives:** CLIP/face-embedding similarity as primary — rejected (fragile here, circular). Retained as *baselines* for the judge classification evaluation (Objective 4), alongside DINOv2, whose self-supervised features are a stronger instance-identity signal than CLIP's (ADR-018).
