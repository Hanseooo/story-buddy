# Feature Spec — filipino-pii-recognizers

**Status:** draft · **Phase:** 2 (post-launch enhancement) · **Owner:** `backend/providers.py` (`redact_pii`)
**Derived from:** moderation-stack spec §8 · **Blocks:** graduation of `# ponytail: stock Presidio, Filipino names leak`

## Purpose

Stock Presidio + `en_core_web_sm` misses Filipino names, Tagalog PII patterns, and mixed
Tagalog-English (Taglish) text. This spec owns the custom recognizers that close those gaps before
`redact_pii` can drop the ponytail comment.

## Open questions (decide before build)

- **Entity types in scope:** Filipino names (first, last), TIN, SSS, PhilHealth, UMID, PRC license, passport numbers — confirm which are in scope for Phase 2.
- **Model strategy:** custom spaCy NER for Filipino names, or rule-based patterns only?
- **Taglish handling:** bilingual NLP engine or a second `en` pass after Tagalog tokenisation?
- **Evaluation set:** what test corpus (real + synthetic) validates coverage before removing the ponytail comment?

## Linked specs

- `moderation-stack` spec — caller; ships with stock Presidio under the ponytail comment until this spec lands.
