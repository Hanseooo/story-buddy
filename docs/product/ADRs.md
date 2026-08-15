# StoryBuddy — Architecture Decision Records

Each ADR is intentionally short and revisitable. Format: Status · Context · Decision · Consequences · Alternatives.

Each ADR now lives in its own file under `docs/product/adr/`; this page is only the index. Decisions are frozen (per AGENTS.md) — an existing ADR file is not edited to reflect a change of mind. A new decision means a NEW FILE in `docs/product/adr/` plus a new row in the table below, with the superseding or amending relationship recorded in the new file's Status line.

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR-001](./adr/ADR-001-image-generation-model-qwen-image-edit-open-weight.md) | Image generation model: Qwen-Image-Edit (open-weight, hosted inference) | Accepted · revised 2026-07-10 |
| [ADR-002](./adr/ADR-002-text-orchestration-vlm-judge-open-weight-models-via.md) | Text/orchestration + VLM judge: open-weight models via OpenRouter | Accepted · revised 2026-07-10 |
| [ADR-003](./adr/ADR-003-pipeline-as-a-deterministic-langgraph-state-machine-not.md) | Pipeline as a deterministic LangGraph state machine (not an autonomous agent) | Accepted |
| [ADR-004](./adr/ADR-004-consistency-via-vlm-as-judge-control-loop-human-ratings.md) | Consistency via VLM-as-judge control loop; human ratings as headline metric | Accepted · amended 2026-07-10 |
| [ADR-005](./adr/ADR-005-async-job-architecture-fastapi-rq-worker-redis.md) | Async job architecture: FastAPI + RQ worker + Redis + LangGraph checkpointing | Accepted |
| [ADR-006](./adr/ADR-006-supabase-for-auth-db-storage-realtime.md) | Supabase for Auth + DB + Storage + Realtime | Accepted · roles superseded by ADR-017 |
| [ADR-007](./adr/ADR-007-style-as-a-fixed-constant-carried-by-the-character.md) | Style as a fixed constant carried by the character reference | Accepted · amended by ADR-022 |
| [ADR-008](./adr/ADR-008-evaluation-three-objective-evaluation-expert-validation.md) | Evaluation: three-objective evaluation (expert validation + judge classification + ISO-25010) | Accepted · revised 2026-07-25 |
| [ADR-009](./adr/ADR-009-hosting-vercel-frontend-railway-backend-singapore.md) | Hosting: Vercel (frontend) + Railway (backend), Singapore region | Superseded by ADR-031 |
| [ADR-010](./adr/ADR-010-regeneration-policy-one-targeted-retry-best-of-fallback.md) | Regeneration policy: one targeted retry, best-of fallback | Accepted |
| [ADR-011](./adr/ADR-011-moderation-safety-stack-four-mechanisms.md) | Moderation & safety stack (four mechanisms) | Accepted · revised 2026-07-10b |
| [ADR-012](./adr/ADR-012-story-length-hard-cap-truncate-at-boundary-no.md) | Story length: hard cap + truncate-at-boundary (no summarization) | Accepted |
| [ADR-013](./adr/ADR-013-caption-source-and-pdf-export.md) | Caption source and PDF export | Accepted · revised 2026-07-21 |
| [ADR-014](./adr/ADR-014-observability-provider-langsmith.md) | Observability provider: LangSmith | Accepted · amended by ADR-030 (Langfuse) |
| [ADR-015](./adr/ADR-015-open-weight-model-mandate-what-open-source-means-here.md) | Open-weight model mandate: what "open source" means here | Accepted · hardened 2026-07-10b |
| [ADR-016](./adr/ADR-016-no-fine-tuning-in-v1.md) | No fine-tuning in v1 | Superseded by ADR-018 |
| [ADR-017](./adr/ADR-017-setting-teacher-managed-classroom-child-holds-an-issued.md) | Setting: teacher-managed classroom; child holds an issued account and operates the app; teacher reviews manually (auto-approve deferred) | Accepted · revised 2026-07-20 |
| [ADR-018](./adr/ADR-018-fine-tune-the-consistency-judge-qwen2-5-vl-7b-qlora.md) | Fine-tune the consistency judge (Qwen2.5-VL-7B, QLoRA) | Accepted · supersedes ADR-016 |
| [ADR-019](./adr/ADR-019-serving-the-fine-tuned-judge-vllm-scale-to-zero-openai.md) | Serving the fine-tuned judge: vLLM, scale-to-zero, OpenAI-compatible | Accepted · amends ADR-009 |
| [ADR-020](./adr/ADR-020-narration-expressive-open-weight-tts-chatterbox-via.md) | Narration: expressive open-weight TTS (Chatterbox) via hosted inference; Kokoro-82M as CPU fallback | Accepted · revised 2026-07-17 |
| [ADR-021](./adr/ADR-021-classroom-sharing-teacher-curated-display-only-gallery.md) | Classroom sharing: teacher-curated, display-only gallery of approved storybooks | Accepted · revised 2026-07-20 |
| [ADR-022](./adr/ADR-022-selectable-art-style-presets-three-prompt-fragment.md) | Selectable art-style presets (three, prompt-fragment based) | Accepted · amends ADR-007 |
| [ADR-023](./adr/ADR-023-story-memory-is-the-langgraph-state-single-int.md) | Story Memory is the LangGraph state; single-int versioning; status lives in the job row | Accepted (2026-07-22) · resolves D-A |
| [ADR-024](./adr/ADR-024-langgraph-node-edge-conventions-partial-return.md) | LangGraph node & edge conventions (partial-return, sequential per-scene loop, pure routers) | Accepted · amends ADR-003 |
| [ADR-025](./adr/ADR-025-provider-resilience-failure-mode-policy-d-c.md) | Provider resilience & failure-mode policy (D-C) | Accepted (2026-07-22) · resolves D-C |
| [ADR-026](./adr/ADR-026-researcher-facing-surfaces-two-authenticated-routes-no.md) | Researcher-facing surfaces: two authenticated routes, no dashboard | Accepted (2026-07-28) |
| [ADR-027](./adr/ADR-027-asset-encoding-retention-webp-scenes-png-references.md) | Asset encoding & retention: WebP scenes, PNG references, PDFs on demand | Accepted (2026-07-28) · confirms ADR-006 |
| [ADR-028](./adr/ADR-028-image-acceptance-identity-taxonomy-frozen-composition.md) | Image acceptance: identity taxonomy frozen, composition on the verdict, reference gated in-node | Accepted (2026-07-29) · amends ADR-007 |
| [ADR-029](./adr/ADR-029-the-character-reveal-an-effect-free-pause-node-a-child.md) | The character reveal: an effect-free pause node, a child-driven single redraw, prelude 9 | Accepted (2026-07-31) · amends ADR-003 |
| [ADR-030](./adr/ADR-030-observability-provider-switch-langsmith-to-langfuse.md) | Observability provider switch: LangSmith to Langfuse | Accepted · amends ADR-014 |
| [ADR-031](./adr/ADR-031-backend-hosting-migration-railway-to-northflank.md) | Backend Hosting Migration: Railway to Northflank | Accepted · supersedes ADR-009 |
| [ADR-032](./adr/ADR-032-moderation-models-api-calls-instead-of-local-models-due.md) | Moderation Models: API calls instead of local models due to RAM constraints | Accepted |
| [ADR-033](./adr/ADR-033-langgraph-checkpointing-forces-the-direct-postgres.md) | LangGraph checkpointing forces the direct Postgres connection (5432), not Supabase's transaction pooler (6543) | Accepted · constrains ADR-005 |
| [ADR-034](./adr/ADR-034-the-reference-gate-scores-itself-acceptance-is-derived.md) | The reference gate scores itself: acceptance is derived from a contradiction list, not asked for as a boolean | Accepted · amends ADR-028 |
| [ADR-035](./adr/ADR-035-the-style-fragment-s-own-prohibitions-filter-the.md) | The style fragment's own prohibitions filter the description: rendering properties are the style's jurisdiction, not the subject's | Accepted · extends ADR-007 |
| [ADR-036](./adr/ADR-036-the-rq-job-deadline-is-a-latency-bound-not-a-safety.md) | The RQ job deadline is a latency bound, not a safety bound: raise it to 1800s and cap regenerations when it binds again | Accepted (2026-08-14) |
| [ADR-037](./adr/ADR-037-trade-book-length-for-a-third-scene-attempt-inside-one.md) | Trade book length for a third scene attempt inside one truthful 55-image envelope | Accepted (2026-08-15) |
| [ADR-038](./adr/ADR-038-safe-failure-diagnostics-one-fixed-reason-taxonomy-for.md) | Safe failure diagnostics: one fixed reason taxonomy for child and teacher recovery | Accepted (2026-08-15, spec review pending) |
| [ADR-039](./adr/ADR-039-narrative-notes-do-not-define-canonical-character-identity.md) | Narrative notes do not define canonical character identity | Accepted (2026-08-15) · amends ADR-034/035; clarifies ADR-029 |
