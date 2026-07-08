# StoryBuddy — Product Requirements Document (v2)

**Subtitle:** An AI-Powered Storyboarding and Picture-Book Generation System with Character and Style Consistency
**SDG Alignment:** SDG 4 — Quality Education
**Doc status:** v2 — design review complete; key decisions resolved; ready for implementation
**Supersedes:** PRD Draft v1

---

## 0. What changed from v1 (changelog)

This version resolves the open decisions from v1 §11 and the "notes to discuss" from v1 §12, and adds sections that were missing entirely. Highlights:

- **Image model chosen:** Nano Banana (Gemini 2.5 Flash Image family / Nano Banana 2 Lite). Hosted, not open-source. See ADR-001.
- **Text/orchestration model chosen:** Gemini. See ADR-002.
- **Style Bible Generator removed as a module** — style is a fixed *constant* in v1, carried by the canonical character reference image. See §8, ADR-007.
- **Consistency approach redesigned:** VLM-as-judge control loop (not CLIP embeddings) drives targeted regeneration; human ratings are the headline research metric. See §10, ADR-004.
- **Evaluation redesigned around a comparative ablation** (pipeline-ON vs pipeline-OFF), Tier 1 made self-sufficient, Tier 2 uses validated child-HCI instruments + behavioral logging. See §10, ADR-008.
- **Async architecture made explicit:** FastAPI + worker + Redis queue + LangGraph checkpointing on Supabase Postgres. See §12, ADR-005.
- **New sections:** Moderation & Safety Stack (§13), Security & Data Protection (§14), Cost Model (§15), Observability (§16), Accessibility (§17).
- **§11 open decisions resolved** — see §11.

---

## 1. Research Problem

Current AI tools can generate stories and images independently, but they struggle to: maintain character consistency across multiple generated images; maintain a consistent artistic style; determine which scenes deserve illustration; convert a story into a coherent picture-book presentation; and do all of this automatically without manual re-prompting and re-generation.

## 2. Research Goal

Develop an intelligent system that automatically transforms a child-written story into a storyboard-style digital picture book while maintaining narrative coherence, character consistency, and artistic style — with minimal manual intervention.

## 3. Main Research Contribution

Not "we called an image API." The contribution is an **AI Storyboarding Pipeline**: coordinated modules (analysis, scene selection, character memory, prompt construction, reference-conditioned generation, automated consistency verification, and composition) that together solve a problem no single generative-model call solves alone. The **consistency-verification-and-correction loop** is the load-bearing novel component and the primary object of evaluation (§10).

---

## 4. Target Users

- **Primary: children** (hands-on creators). Reading level, tone, and failure messaging must be kid-appropriate throughout. See accessibility (§17) — many target-age children cannot yet read/type fluently, which shapes the input and caption experience.
- **Secondary: parent/guardian** (account holder, gatekeeper, exporter, and Tier-1 evaluation audience).

**Out of scope for v1:** teacher/classroom accounts, multi-child collaboration, public sharing/social features.

---

## 5. Scope

### 5.1 MVP modules
1. Story Analyzer (grammar-tolerant entity + coreference extraction)
2. Scene Segmentation Engine (selects up to 10–15 scenes; graceful floor behavior for short stories)
3. Character Bible Generator + auto-generated canonical reference image (multi-character, max 2 canonical refs in v1)
4. **Style Constant** (fixed style; not a generator — see ADR-007)
5. Prompt Optimization Engine
6. Image Generation Engine (reference-conditioned, Nano Banana)
7. Consistency Checker (VLM-as-judge; triggers one targeted regeneration)
8. Slide Composer / Export (PDF + library)
9. Parent account + kid profile system (Supabase Auth + RLS)
10. Moderation & Safety Stack (input text, PII, output image, model self-refusal fallback)

### 5.2 Deferred to Future Work (named in paper, not built in v1)
Kid-uploaded character reference; multiple selectable art styles; multi-language; teacher/classroom tier; public sharing; collaborative multi-child stories; on-device / open-source generation (privacy-preserving) — see ADR-002.

### 5.3 Timeline
~1 month MVP build (solo, agentic-tooling-assisted); ~2–3 months reserved for evaluation and iteration. Ethics/consent process runs **in parallel from week 1** (§10, §18).

---

## 6. Key Product Decisions (resolved)

| Decision | Choice | Why / ADR |
|---|---|---|
| Character reference origin | System auto-generates one canonical reference per character, reused via reference-conditioned generation | Stronger contribution; avoids moderating uploads; avoids style mismatch. ADR-001 |
| Image model | Nano Banana (Gemini 2.5 Flash Image / Nano Banana 2 Lite), hosted | Character consistency is its headline feature; cost ~$0.034–0.039/image; open-source consistency is a research project in itself. ADR-001 |
| Text/orchestration model | Gemini (Flash tier for pipeline nodes) | Single ecosystem, cheap, strong structured output. Local-model privacy variant is future work. ADR-002 |
| Style in v1 | Single fixed style, authored once as a constant; carried by the character reference image | Removes a module; character ref carries identity *and* style; cleaner consistency eval. ADR-007 |
| Consistency mechanism | VLM-as-judge control loop → one targeted, prompt-corrected regeneration → best-of fallback | Robust on stylized/non-human characters; interpretable; makes regeneration refinement not resampling. ADR-004, ADR-010 |
| Consistency metric (research) | Human ratings = headline; VLM-judge = runtime signal; report VLM–human agreement as a secondary result | Avoids circularity of optimizing and reporting the same score. ADR-004, ADR-008 |
| Auth model | Parent-created Supabase account; kid = nested profile (nickname + avatar, no direct PII from kid) | Avoids collecting PII from minors; RLS isolates data. ADR-006 |
| Design language | Cartoon-pop (kid flow); calmer/denser variant (parent screens) | Matches storybook tone; density fits parent dashboard. |
| Moderation | Input text + PII + output image, all moderated; model self-refusal has a fallback | Non-negotiable for child users. §13, ADR-011 |
| Captions | Kid's **verbatim** text excerpt (not LLM-rewritten) | Preserves story fidelity; no extra generation/moderation surface. |
| Orchestration style | Deterministic LangGraph state machine (not an autonomous agent) | Reproducibility, debuggability, cost control. ADR-003 |

---

## 7. User Flow

1. **Landing page** — parent-facing pitch; Sign up / Log in (SSR for SEO).
2. **Auth** — parent creates account or logs in (Supabase Auth).
3. **Kid profile select/create** — nickname + avatar; no PII from the kid.
4. **Write your story** — large friendly input; optional starter prompt; **read-aloud option** for pre-readers (§17); live length indicator against the word cap.
5. **Input gate** — (a) length check → gentle truncate-at-scene-boundary message if over cap (never silent summarization); (b) PII redaction; (c) text moderation → gentle "let's try that again" on failure.
6. **Processing view** — staged, animated, kid-legible progress via Supabase Realtime on the job row; never frozen/silent. Expect ~1–3 min.
7. **Character/Style reveal + confirm** — show the **moderated** canonical character reference(s) before full generation; lightweight confirm / "try again." *(Character reference is moderated before the child sees it — see §13.)*
8. **Full scene generation** — all scenes generated using the confirmed reference(s).
9. **Output moderation + consistency pass** — before the kid sees results; failed scenes get one targeted regeneration, then best-of fallback (§10, §13).
10. **Storybook slideshow** — image + verbatim caption + page number; next/prev; optional read-aloud.
11. **Parent review gate** — ON by default before export/share (may be bypassed inside a supervised study). §11.1.
12. **Export/Share** — PDF download and/or save to the parent's library (Supabase Storage, signed URLs).

---

## 8. Feature List

### MVP
- Story Analyzer (grammar-tolerant extraction: characters/locations/objects/events + coreference)
- Scene Segmentation (up to 10–15 scenes; **floor behavior**: fewer scenes allowed, never invent content)
- Character Bible + auto-generated canonical reference image (≤2 canonical characters)
- **Style Constant** (fixed prompt fragment + optional fixed style-anchor image; authored once)
- Prompt Optimizer (scene + character bible + style constant + story memory → structured prompt)
- Image Generator (reference-conditioned via Nano Banana)
- Consistency Checker (VLM-as-judge: presence, identity, key attributes, style; emits structured verdict + failure reasons)
- Regeneration controller (1 targeted retry with corrected prompt; best-of fallback; capped)
- Moderation stack (text + PII + image + model self-refusal fallback)
- Slide Composer (image + verbatim caption + page number + layout)
- Parent account + kid profile (Supabase Auth + RLS)
- Parent library/dashboard of saved storybooks
- Export (PDF; shareable link optional)
- Read-aloud (TTS) for captions — **strongly recommended in MVP** given target age (§17)

### Stretch / Future Work
Kid-uploaded reference; selectable art styles; multi-language; teacher/classroom tier; social sharing; on-device/open-source generation.

---

## 9. Design & UX Direction

- **Kid flow (steps 3–10):** cartoon-pop — rounded shapes, warm saturated palette, soft depth, friendly micro-interactions (Motion), minimal text, large touch targets, Lottie wait-state animations. Every wait state needs a visible, kid-legible explanation.
- **Parent flow (steps 1–2, 11–12, dashboard):** same color DNA, calmer/denser grid/card layout (shadcn/ui acceptable here).
- Specific tokens (palette hex, type pairing, spacing, radius/shadow) are an implementation decision informed by the cartoon-pop direction; see the frontend-design skill at build time.
- **Failure/moderation states get the same design care as success states.** A harsh failure screen is a larger UX risk here than in a general-audience app.

---

## 10. Research Questions & Evaluation Plan

### Research Questions
- RQ1: How accurately does StoryBuddy identify key scenes from child-written stories?
- RQ2: **Does the Character Bible + VLM consistency loop measurably improve visual consistency vs. naive per-scene generation?** *(ablation — the central claim)*
- RQ3: How acceptable is the generated storybook (narrative coherence, visual consistency, illustration quality, usability)?
- RQ4 (revised): How gracefully does the system handle **under-length** stories (fewer than 10–15 natural scenes) without inventing content? *(replaces the original "does capping at 10–15 help" framing, which rarely arises for short kid stories)*

### Evaluation design (see ADR-008)
**Spine = comparative ablation.** Same story corpus generated twice: **pipeline-ON** (character reference + VLM checker + regeneration) vs **pipeline-OFF** (naive per-scene generation, no reference, no checker). Adult raters judge **blind** to condition.

**Tier 1 (adults — parents/teachers), no special clearance typically needed. Designed to stand alone.**
- Blind pairwise/scored ratings of narrative coherence, visual consistency, illustration quality, story completeness.
- **Inter-rater reliability** defined up front for Story Completeness (annotators agree on "major plot points"; report Cohen's/Krippendorff's).
- Target N ≈ 15–30 raters. Core claims (RQ1–RQ3) fully supported here so an IRB delay on Tier 2 cannot sink the capstone.

**Tier 2 (children), lighter touch, under parental supervision, contingent on ethics clearance. Enrichment, not load-bearing.**
- **Validated instruments:** Fun Toolkit (Read & MacFarlane) — Smileyometer (liking) + Again-Again table (engagement proxy). Cite in methods.
- **Story fidelity item** (kid-only ground truth): "Did the book tell the story you wanted to tell?"
- **Behavioral logging** (more reliable than child self-report): completion rate, time-on-task, spontaneous second-story starts, "try again" frequency. Watch the novelty confound — repeat-use within a session matters more than first-reaction delight.
- Target N ≈ 8–15 children.

### Metrics
| Metric | What it measures | Source |
|---|---|---|
| Story Completeness | Major plot points represented in selected scenes | Human annotation + IRR |
| Character Consistency | Same character recognizable across scenes | **Human (headline)** + VLM-judge (secondary) |
| Style Consistency | Fixed style maintained across scenes | Human + VLM-judge |
| Story Fidelity | Book matches child's intent | Child (Tier 2) |
| Engagement | Repeat-use / liking | Fun Toolkit + behavioral logs |
| Generation Time | Submission → completed storybook | Instrumentation (§16) |
| AI Resource Usage | Avg generation time, image count, regen count, API cost/story | Instrumentation (§16) |
| **VLM–Human agreement** | Does the automated checker track human judgment? | Derived (bonus result — validates the metric) |

### Story corpus (validity — do not skip)
Test stories must be **real or realistic child writing**, not builder-authored clean stories (which measure best-case only). Sources: collected real stories (ties to Tier-2 consent), a public children's-writing dataset, or adults deliberately writing "as a 6/8/10-year-old," including messy/non-linear ones. Document provenance — reviewers will ask.

### ⚠️ Ethics timeline
Formal ethics review (Philippine Data Privacy Act 2012 + your university's ethics board; not US "IRB" per se) can take weeks. **Start in parallel with development, week 1.** Tier-1 self-sufficiency (above) is the insurance if Tier-2 clearance slips.

---

## 11. Open Decisions — RESOLVED

1. **Parent approval gate before export** → **ON by default** (human backstop over auto-moderation; bypass allowed inside supervised study).
2. **Regeneration cap** → **1 targeted, prompt-corrected retry** (2 attempts total); if still failing, keep the higher-scoring image (best-of), never a broken/placeholder page. ADR-010.
3. **Story length limit** → **hard word cap (~500–800 words, tunable)** with a gentle "let's make a book of the first part" truncation at a scene boundary. **No silent AI summarization** (it would illustrate the summary, not the child's story). ADR-012.
4. **Repeated moderation-failure off-ramp** → after **N=3** failed revisions of the same story, suggest starting a fresh story rather than an unbounded retry loop.
5. **Multiple main characters** → **max 2 canonical references** in v1; generation conditions on multiple reference images; the checker verifies **each character separately** against its own reference. ADR-004.
6. **Very short stories** → **fewer scenes allowed** (floor, e.g. ≥3); never invent content. Reframed as RQ4.
7. **Whole-run timeout / stall** → **LangGraph checkpointing + resumability**: a stall at scene N resumes from N, never re-rolls scenes 1…N-1. Kid sees "taking a little longer…" then "we saved your progress — come back soon." ADR-005.
8. **Image model/API** → Nano Banana. ADR-001.
9. **Moderation services** → text (OpenAI moderation) + PII (Presidio) + image (Vision SafeSearch or Gemini safety). Not a single provider. §13, ADR-011.

---

## 12. Technical Architecture

**Frontend:** Next.js (React) + Tailwind + shadcn/ui (parent) + hand-built cartoon-pop components (kid) + Motion (micro-interactions) + Lottie (wait states). Deployed on Vercel.

**Backend:** FastAPI (web) + **separate RQ worker** + **Redis** (broker), on Railway (Render/Fly.io equivalent; Singapore region). *A long pipeline cannot run in a request cycle — this is a 3-service deployment, not one.*

**Pipeline engine:** **LangGraph as a deterministic state machine** (explicit nodes; conditional edges only at moderation pass/fail and consistency pass/fail). LangChain omitted unless a concrete need appears. Gemini SDK called directly. ADR-003.

**State/persistence:** Supabase Postgres (app data + LangGraph checkpoints via `langgraph-checkpoint-postgres`); Supabase Auth (parent) + RLS; Supabase Storage (images + PDFs, signed URLs); Supabase Realtime (job progress). ADR-006.

**Structured extraction:** Gemini structured output (`response_schema`) + Pydantic validation on every LLM boundary. The Story Memory schema is the contract between modules.

**Export:** HTML storybook template → PDF via Playwright/WeasyPrint (server-side) — decide at build (ADR-013).

**Flow:** `POST /storybooks` creates a job row, returns `job_id` immediately → worker runs the LangGraph pipeline, checkpointing after each scene, updating job status → frontend subscribes to the job row via Realtime → on completion, images/PDF in Storage, book in library.

---

## 13. Moderation & Safety Stack

Four distinct concerns, four mechanisms:

1. **Input text moderation** — OpenAI moderation endpoint (free) on the child's story before any processing. Gentle, non-scary failure copy.
2. **PII detection/redaction** — Presidio (open-source) on input. A child narrating real life ("my name is… I live at…") is the *expected* case; redact before storage/captioning/export. This is separate from toxicity moderation.
3. **Output image moderation** — Vision SafeSearch (or Gemini safety) on **every generated image, including the canonical character reference before the reveal (flow step 7)**. No generated image reaches a child unmoderated.
4. **Model self-refusal fallback** — the image model may refuse legitimate mild-peril scenes ("fight the dragon"). On refusal: soften-and-retry the prompt, then a gentle "let's imagine that part a little differently." A scary-but-innocent story must not dead-end.

Ordering matters: input gate (step 5) → char-ref moderation (before step 7) → output moderation (step 9).

---

## 14. Security & Data Protection

- **RLS everywhere.** Parents read only their own account's data; enforced at the DB layer, not just the app.
- **Signed URLs** for all kid-generated images/PDFs; no public buckets.
- **Data retention & deletion path.** Define what's stored (profile, stories, images, logs), for how long, and give parents a one-action **delete-my-child's-data** path. Required posture under the PH Data Privacy Act.
- **Minimal kid PII by design** — nickname + avatar only; no direct collection from the minor.
- **Rate limiting / abuse** — `slowapi` + per-profile daily generation cap (also protects budget). Addresses single-account abuse.

---

## 15. Cost Model

At ~$0.034–0.039/image (Nano Banana; Batch/Flex ~$0.02): one book ≈ 1 reference + ~12 scenes + regenerations ≈ 15–18 images ≈ **~$0.55–0.70**, ~$1 worst case. Text/VLM calls add pennies.

- **Develop on the free tier + Batch API; spend paid budget only on study runs.** Keeps dev inside a small budget.
- Recommended budget for comfortable dev + a real study: **~$50–100** (not $15–20). Trivially cheap; don't constrain the research over ~$30.
- **Cost circuit-breaker:** a per-book worst-case ceiling that trips rather than silently running; per-account daily cap (§14).

---

## 16. Observability (doubles as research instrumentation)

Instrument the pipeline with **LangSmith** (native LangGraph tracing) or **Langfuse** (open-source, self-hostable). This captures generation time, per-scene regeneration counts, cost per book, and VLM-judge scores — i.e. the "AI Resource Usage" metrics and a large share of the eval dataset. Add **Sentry** for error tracking. Instrument from the walking-skeleton phase so data collection is free by the time you evaluate.

---

## 17. Accessibility

The primary user is a child; the core interaction assumes reading and typing, which many target-age children cannot do fluently. Provide **read-aloud (TTS, via Gemini) for captions** (recommended in MVP, not future work), consider **speech-to-text for story input** as a strong enhancement, and ensure large touch targets, high contrast, and minimal on-screen text throughout the kid flow.

---

## 18. Delivery Approach

**Walking skeleton → vertical slices → hardening** (see ROADMAP). Not waterfall (riskiest assumptions — consistency loop, model behavior, async latency — can only be validated by building, so hit them week 1). Not heavy agile ceremony (solo). Up-front design = this PRD + the Story Memory schema + the LangGraph shape (expensive to rework, so settled first). Ethics/consent track runs in parallel from week 1.

---

## 19. Reference: Story Memory Data Shape (v2 sketch — finalize in implementation)

```json
{
  "account_id": "",
  "profile_id": "",
  "story_id": "",
  "job": { "status": "", "current_stage": "", "created_at": "", "checkpoint_ref": "" },
  "input": { "raw_text": "", "redacted_text": "", "word_count": 0, "truncated": false, "moderation": {} },
  "characters": [
    { "char_id": "", "name": "", "description": {}, "canonical_ref_image": "", "ref_moderation_status": "" }
  ],
  "locations": [],
  "objects": [],
  "timeline": [],
  "style": { "style_constant_id": "", "prompt_fragment": "", "style_anchor_image": "" },
  "scenes": [
    {
      "scene_id": "",
      "text_excerpt": "",
      "caption": "",
      "characters_present": [],
      "prompt": "",
      "attempts": [
        { "image_ref": "", "vlm_verdict": {}, "failure_reasons": [], "passed": false }
      ],
      "final_image_ref": "",
      "consistency_check_status": "",
      "regeneration_count": 0,
      "moderation_status": ""
    }
  ],
  "cost": { "image_count": 0, "regen_count": 0, "usd_estimate": 0 },
  "eval": { "condition": "pipeline_on|pipeline_off", "seed": null }
}
```

---

## 20. Non-Functional Notes

- **Concurrency:** at demo/study scale a single serial worker is fine; "in the wild," concurrent submissions queue (acceptable) or scale RQ workers horizontally. Note the tradeoff; don't over-build for v1.
- **Reproducibility:** control seeds where the model supports it so the ablation is fair and re-runnable.
- **SynthID:** Nano Banana images carry an invisible SynthID watermark — useful provenance for a child-safety product; note it in the paper.
