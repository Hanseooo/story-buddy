# StoryBuddy — Product Requirements Document (v2)

**Subtitle:** An AI-Powered Storyboarding and Picture-Book Generation System
**SDG Alignment:** SDG 4 — Quality Education
**Doc status:** v2.4 — **RQ apparatus retired; realigned to the manuscript's five objectives (2026-07-25)**
**Supersedes:** PRD Draft v1
**Study design lives in `docs/product/RESEARCH_PROTOCOL.md`.** §10 below is a summary and a pointer.

---

## 0.4 What changed in v2.4 (2026-07-25) — the RQ apparatus is retired; five objectives replace it

The updated capstone manuscript is now authoritative for the study design (ADR-008, revised 2026-07-25).
- **"RQ1"–"RQ6" are retired.** The study is organized around the manuscript's **five objectives**
  (Implement → Produce → Determine acceptability via expert validation → Evaluate judge classification →
  Evaluate ISO/IEC 25010 software quality). See §10.
- **The RQ5 naive-reader/child-comprehension recall study is dropped entirely** — no reader-recall leg, no
  Tier-1/Tier-2 respondent tiers, no Fun Toolkit (Smileyometer, Again-Again), no child engagement
  instruments. Respondents are now: **Grade 5–6 learners** (write stories only, no evaluation role),
  **expert validators** (Dean/Professor of the Arts College, one Arts student/intern, one Education
  student/intern), and separate **designated software-quality evaluators** (ISO/IEC 25010).
- **Objective 3 (expert validation) uses a written, open-ended interview form + content analysis**
  (positive / negative / suggestion per criterion, five criteria), not the earlier feature-level scored
  rubric (CVI / Krippendorff's α).
- **Objective 4 (judge classification) is a formal, reported objective**: precision / recall / F1 (F1
  primary) against human reference labels, character-identity-level split, with an **optional** secondary
  comparison against the zero-shot base model and the existing prompted baseline. This is no longer
  "descriptive only / no comparative claim / build-gate only."
- **Objective 5 is ISO/IEC 25010 software quality** — five characteristics (Functional Suitability,
  Performance Efficiency, Usability, Reliability, Security), 5-point Likert, weighted mean + SD, Table 4
  interpretation bands.
- **Corpus renumbered and located:** ~~"~50 (60–70) donated stories"~~ → **15 stories collected → 10
  primary + 5 backup**, Grade 5–6. Stories collected at **Matina Aplaya Elementary School**; system
  development and evaluation at **Holy Cross of Davao College (HCDC)**, Davao City, Philippines.
- **ADR-018's δ = 3 non-inferiority gate is unaffected** — still a *deployment* gate (does the fine-tuned
  judge replace the prompted incumbent in the product), not a reported finding.
- Full detail: `docs/product/RESEARCH_PROTOCOL.md` (rewritten to match) and ADR-008 (revised 2026-07-25).

---

## 0.3 What changed in v2.3 (2026-07-22) — the study drops its comparative claim

- **RQ6 is demoted from primary comparative study to a descriptive report.** The judge fine-tune is
  **kept**; its **agreement with human labels** on the character-disjoint held-out set is reported. The
  **fine-tuned-vs-baseline comparison is dropped as a research claim** — no "fine-tuned 7B matches/beats
  prompted Gemma-3-27B" in the paper. **ADR-008, revised 2026-07-22.**
- **The study has no primary comparative study and makes no causal or comparative claim.** Objective 3 =
  evaluate the generated outputs (expert panel + RQ5 naive-reader recall); Objective 4 = **ISO/IEC 25010**
  software quality.
- **Methodological requirements survive:** inter-rater reliability on the human labels, held-out set
  **read once**.
- **ADR-018's δ = 3 non-inferiority gate is unaffected** — it is a *deployment* gate (does the fine-tuned
  judge replace the prompted incumbent in the product), not a reported finding.

---

## 0.2 What changed in v2.2 (2026-07-10) — setting, sharing, fine-tuning

- **The problem statement grew a "so what."** The technical problem (models can't hold characters
  consistent) and the educational benefit (a child's story finally gets an audience and an artifact) are
  the same claim from opposite ends. A picture book that drifts doesn't transmit the child's story — it
  transmits noise. See RESEARCH_PROTOCOL §1–§3.
- **Setting: Grade 5–6 Philippine students.** Teacher (or BEED student) owns the classroom and issues each
  student a classroom-scoped account; the child logs in and authors their own story directly; the
  parent's role stays consent-giver. Sharing is classroom-scoped. **No public mode, ever.** ADR-017.
- **The judge is fine-tuned** (`Qwen2.5-VL-7B`, QLoRA), served on vLLM. ADR-018 supersedes ADR-016;
  ADR-019 adds the fourth service. The **pipeline is still the contribution (§3)**.
- **No proprietary models at all** (ADR-015 hardened). Removes exactly two things: OpenAI
  `omni-moderation` → **`gpt-oss-safeguard-20b`** (Apache-2.0 open weights, via OpenRouter — Granite
  Guardian was the ADR-011b pick but is not routable there; ADR-011c), and ElevenLabs → an **open expressive TTS**
  (**Chatterbox**, MIT, hosted inference; Kokoro-82M CPU fallback — ADR-020, revised 2026-07-17).
  **meta-llama/llama-guard-4-12b** (119 languages) replaces Llama Guard and closes the Taglish hole.
- **Two new safety findings**, neither previously in any ADR: Presidio leaks Filipino PII by default, and
  the text gate's Filipino/Taglish performance was never measured. Both are now Phase-0.5/Phase-2 work.
- **The ethics submission splits in two**, because Tier 1 was silently blocked on Tier 2. ADR-008.

---

## 0.1 What changed in v2.1 (2026-07-10) — the open-weight switch

An external requirement directs StoryBuddy to use **open-source models**. See **ADR-015**, which
defines "open source" as **open weight** and records that hosted inference of open weights satisfies it.

- **Image model:** Nano Banana → **Qwen-Image-Edit** (Apache-2.0), hosted on fal.ai. ADR-001 revised.
- **Text + VLM judge:** Gemini → **`qwen/qwen3-32b`** and **`google/gemma-3-27b-it`** via OpenRouter. ADR-002 revised.
- **Moderation:** open classifiers primary, free proprietary backstop. ADR-011 revised.
- **No fine-tuning.** Identity via training-free reference conditioning; style already handled by
  ADR-007's constant. Scoped, costed, and deliberately deferred — **ADR-016**.
- **New Phase 0.5 spike** (ROADMAP) with a kill criterion, because non-human character consistency is
  no longer a vendor-verified feature.
- **Two capabilities lost, named honestly:** SynthID watermarking (no open equivalent) and the image
  model's built-in safety filter (which makes ADR-011's gate load-bearing).
- **The research contribution (§3) is unchanged.** The pipeline is the contribution; the model is the
  substrate. **This switch does not create a privacy claim** — the child's text still transits a third
  party. Do not write one into the paper.

---

## 0. What changed from v1 (changelog)

This version resolves the open decisions from v1 §11 and the "notes to discuss" from v1 §12, and adds sections that were missing entirely. Highlights:

- **Image model chosen:** ~~Nano Banana~~ → superseded by §0.1. See ADR-001.
- **Text/orchestration model chosen:** ~~Gemini~~ → superseded by §0.1. See ADR-002.
- **Style Bible Generator removed as a module** — style is a fixed *constant* in v1, carried by the canonical character reference image. See §8, ADR-007.
- **Consistency approach redesigned:** VLM-as-judge control loop (not CLIP embeddings) drives targeted regeneration; human ratings are the headline research metric. See §10, ADR-004.
- **Evaluation redesigned around a comparative ablation** (pipeline-ON vs pipeline-OFF), Tier 1 made self-sufficient, Tier 2 uses validated child-HCI instruments + behavioral logging. See §10, ADR-008.
- **Async architecture made explicit:** FastAPI + worker + Redis queue + LangGraph checkpointing on Supabase Postgres. See §12, ADR-005.
- **New sections:** Moderation & Safety Stack (§13), Security & Data Protection (§14), Cost Model (§15), Observability (§16), Accessibility (§17).
- **§11 open decisions resolved** — see §11.

---

## 1. Research Problem

**The setting.** A child writes a story. The teacher marks it. It goes in a folder. Nobody reads it. Prior
work on writing motivation is consistent that an authentic audience and actual publication are among the
strongest levers on children's writing engagement — and illustrating forty stories is not something a
Grade 5–6 teacher can do.

**The technical obstacle.** Current AI tools can generate stories and images independently, but they
struggle to: maintain character consistency across multiple generated images; maintain a consistent
artistic style; determine which scenes deserve illustration; convert a story into a coherent picture-book
presentation; and do all of this automatically without manual re-prompting and re-generation.

**Why these are the same problem.** The artifact is only worth publishing if it actually *is* the child's
story. A book whose hero changes face on page four does not transmit the child's story — it transmits
noise. The technical problem and the educational benefit are one claim viewed from two ends, which is what
makes this research rather than integration.

## 2. Research Goal

Develop an intelligent system that automatically transforms a child-written story into a storyboard-style digital picture book while maintaining narrative coherence, character consistency, and artistic style — with minimal manual intervention.

**Evaluated through five objectives** — implement the pipeline, produce the books, then determine
acceptability via expert validation, evaluate the judge's classification performance, and evaluate
software quality (ISO/IEC 25010). (RESEARCH_PROTOCOL §2.)

## 3. Main Research Contribution

Not "we called an image API." The contribution is an **AI Storyboarding Pipeline**: coordinated modules (analysis, scene selection, character memory, prompt construction, reference-conditioned generation, automated consistency verification, and composition) that together solve a problem no single generative-model call solves alone. The **consistency-verification-and-correction loop** is the load-bearing novel component and the primary object of evaluation (§10).

---

## 4. Target Users

- **Primary: the Grade 5–6 student author** (ages 10–12, Philippines). The child holds a teacher-issued,
  classroom-scoped account, logs in, and writes their own story directly. Reading level, tone, and failure
  messaging must be age-appropriate throughout.
- **Account issuer + reviewer: the teacher or BEED (education) student** — owns the classroom, issues each
  student account (nickname + teacher-set password), and reviews every generated book (manual
  approve/reject) before it enters the classroom gallery or is exported. *(ADR-017 — supersedes ADR-006's
  role model.)*
- **Parent/guardian: consent-giver, not an operator.** Guardian consent and child assent are required by
  the PH Data Privacy Act — a child-held account with a password and peer-visible typed content raises the
  consent weight above the earlier teacher-only-operator model (Ethics Stage-2 scope; `ethics_and_safety.md`).

**Scope is derived from the study's objectives**, not chosen for convenience: Grade 5–6 students write
independently (so the story is unambiguously theirs), read fluently (so the books produced from their
stories are substantive enough for expert validators to judge), are taught in English from Grade 4 (one
language, one moderation regime), and are pre-adolescent (age-appropriate content and design throughout).
See RESEARCH_PROTOCOL §11.

**Out of scope for v1:** multi-child collaboration; cross-classroom sharing. **Out of scope permanently:
public sharing** — peer-visible content authored by minors, without a gatekeeper, is a social network for
ten-year-olds (ADR-017).

---

## 5. Scope

### 5.1 MVP modules
1. Story Analyzer (grammar-tolerant entity + coreference extraction; tolerant of light Taglish)
2. Scene Segmentation Engine (selects up to 10–15 scenes; graceful floor behavior for short stories)
3. Character Bible Generator + auto-generated canonical reference image (multi-character, max 2 canonical refs in v1)
4. **Style Presets** (three fixed styles, author picks one before generation; config, not a generator — ADR-007, ADR-022)
5. Prompt Optimization Engine
6. Image Generation Engine (reference-conditioned, Qwen-Image-Edit)
7. Consistency Checker (VLM-as-judge; triggers one targeted regeneration). **Fine-tuned in Phase 2.5** — ADR-018
8. Slide Composer / Export (PDF + library) + **expressive TTS narration** (Chatterbox, hosted) per page — ADR-020
9. **Teacher/BEED-student account + classroom + teacher-issued student accounts** (Supabase Auth for
   teacher; classroom-scoped nickname+password auth for students; RLS) — ADR-017
10. Moderation & Safety Stack (input text, PII incl. **Filipino recognizers**, output image, self-refusal fallback)
11. **Classroom sharing** (teacher-curated, display-only gallery of approved storybooks — gallery-gated) — ADR-021

### 5.2 Deferred to Future Work (named in paper, not built in v1)
Kid-uploaded character reference; multiple selectable art styles; multi-language; **"what happens next?"
continuation**; collaborative multi-child stories; **on-device generation** (the only variant that is
genuinely privacy-preserving — v1 runs open weights on *hosted* inference, ADR-015); **style LoRA**
(ADR-016 trigger); **Taglish story-analyzer fine-tune** (ADR-018); **C2PA watermark/provenance** (replaces
the SynthID capability lost with Nano Banana, ADR-001). **Public sharing is not deferred — it is rejected** (ADR-017).

### 5.3 Timeline
**3–6 months.** Build is solo; the research track has three members. At 3 months the ROADMAP's de-scope
ladder is not optional; at 6 months it is insurance. **Ethics Stage 1 is filed before Phase 0.5 completes** —
it is the long pole and cannot be compressed by coding faster (§10, §18, RESEARCH_PROTOCOL §9).

---

## 6. Key Product Decisions (resolved)

| Decision | Choice | Why / ADR |
|---|---|---|
| Character reference origin | System auto-generates one canonical reference per character, reused via reference-conditioned generation | Stronger contribution; avoids moderating uploads; avoids style mismatch. ADR-001 |
| **Model openness** | Open **weight**; hosted inference; self-hosting always available, never required | External mandate. Hosting is orthogonal to openness. **ADR-015** |
| Image model | Qwen-Image-Edit 2509/2511 (Apache-2.0), hosted on fal.ai | Multi-reference conditioning, no training; ~$0.02–0.035/image. Non-human consistency **unverified — Phase 0.5 spike**. ADR-001 |
| Text/orchestration model | `qwen/qwen3-32b` via OpenRouter | Open weight, strict structured output, cheap. **Set `provider.require_parameters: true`.** ADR-002 |
| Fine-tuning | **None in v1** | Identity needs no training (reference conditioning); style is already a constant (ADR-007). Costed and deferred with an explicit trigger. **ADR-016** |
| Style in v1 | Single fixed style, authored once as a constant; carried by the character reference image | Removes a module; character ref carries identity *and* style; cleaner consistency eval. ADR-007 |
| Consistency mechanism | VLM-as-judge control loop → one targeted, prompt-corrected regeneration → best-of fallback | Robust on stylized/non-human characters; interpretable; makes regeneration refinement not resampling. ADR-004, ADR-010 |
| Consistency metric (research) | Human ratings = headline; VLM-judge = runtime signal; report VLM–human agreement as a secondary result | Avoids circularity of optimizing and reporting the same score. ADR-004, ADR-008 |
| Auth model | **Teacher-issued classroom account**: child gets nickname + teacher-set password (no email, no self-serve signup); teacher-initiated reset only | Keeps the child off self-serve/social-network surfaces while letting them author and own their story; RLS isolates by classroom (and by child within it). **ADR-017** |
| Sharing | **Classroom-scoped, teacher-gated, display-only gallery.** No public mode, ever. No reflection/comment surface — the storybook is the only peer-visible artifact. | Peer-visible child content without a gatekeeper is a social network for ten-year-olds. ADR-017, ADR-021 |
| **Fine-tuning** | **The consistency judge** (`Qwen2.5-VL-7B`, QLoRA), served on vLLM | Identity and style are the wrong targets (ADR-016's reasoning survives); the judge is the documented weakest link with a known prompting ceiling. **ADR-018, ADR-019** |
| Narration | **Chatterbox** (MIT, expressive) via hosted inference, pre-rendered per page; **Kokoro-82M** CPU fallback | Expressive, emotional read-aloud; open-weight so the mandate holds; small metered cost. **ADR-020** (revised) |
| Design language | Cartoon-pop (student flow); calmer/denser variant (teacher screens) | Matches storybook tone; density fits the teacher dashboard. |
| Moderation | Two independent **open** classifiers per path + PII + image gate + self-refusal fallback | Non-negotiable for child users. Proprietary backstop removed and replaced, not abandoned. §13, ADR-011 |
| Captions | Kid's **verbatim** text excerpt (not LLM-rewritten) | Preserves story fidelity; no extra generation/moderation surface. |
| Orchestration style | Deterministic LangGraph state machine (not an autonomous agent) | Reproducibility, debuggability, cost control. ADR-003 |

---

## 7. User Flow

1. **Landing page** — teacher-facing pitch; Sign up / Log in (SSR for SEO).
2. **Auth** — teacher or BEED student creates account or logs in (Supabase Auth), creates a **classroom**,
   and issues each student a classroom account (nickname + initial teacher-set password).
3. **Student login** — child logs in with classroom code + nickname + password (their own account, not a
   profile pick); no self-serve signup, no email; the child can change their password from settings.
4. **Write your story** — large friendly input; optional starter prompt; live length indicator against the word cap.
5. **Input gate** — (a) length check → gentle truncate-at-scene-boundary message if over cap (never silent summarization); (b) PII redaction; (c) text moderation → gentle "let's try that again" on failure.
6. **Processing view** — staged, animated, kid-legible progress via Supabase Realtime on the job row; never frozen/silent. Expect ~1–3 min.
7. **Character/Style reveal + confirm** — show the **moderated** canonical character reference(s) before full generation; lightweight confirm / "try again." *(Character reference is moderated before the child sees it — see §13.)*
8. **Full scene generation** — all scenes generated using the confirmed reference(s).
9. **Output moderation + consistency pass** — before the kid sees results; failed scenes get one targeted regeneration, then best-of fallback (§10, §13).
10. **Storybook slideshow** — image + verbatim caption + page number; next/prev; **narration** (ADR-020).
11. **Teacher review gate** — every book is manually approved or rejected by the teacher before it enters
    the classroom gallery or is exported. There is no auto-approve toggle (deferred to Future Work — an
    ethics re-review is required before that can ship). ADR-017.
12. **Classroom gallery** — classmates read/listen to approved books. Display-only: no reflection prompt,
    comment, or scoring surface. ADR-021.
13. **Export** — PDF download and/or save to the classroom library (Supabase Storage, signed URLs).
    The PDF is the only way a book leaves the container; the child shares the artifact, not the platform.

---

## 8. Feature List

### MVP
- Story Analyzer (grammar-tolerant extraction: characters/locations/objects/events + coreference)
- Scene Segmentation (up to 10–15 scenes; **floor behavior**: fewer scenes allowed, never invent content)
- Character Bible + auto-generated canonical reference image (≤2 canonical characters)
- **Style Presets** — three hand-authored prompt fragments; the author picks one **before** the canonical
  reference is generated, and it is then frozen for the storybook. No style-anchor image (ADR-022).
- Prompt Optimizer (scene + character bible + selected style preset + story memory → structured prompt)
- Image Generator (reference-conditioned via Qwen-Image-Edit)
- Consistency Checker (VLM-as-judge: presence, identity, key attributes, style; emits **reasoning first**, then a structured verdict + failure reasons — ADR-004)
- Regeneration controller (1 targeted retry with corrected prompt; best-of fallback; capped)
- Moderation stack (text + PII + image + model self-refusal fallback)
- Slide Composer (image + verbatim caption + page number + layout)
- Teacher/BEED-student account + classroom + teacher-issued student accounts (Supabase Auth for the
  teacher; classroom-scoped nickname+password auth for students) + RLS — ADR-017
- Teacher library/dashboard of classroom storybooks — ADR-017
- Export (PDF; shareable link optional)
- Read-aloud (TTS) for captions — **strongly recommended in MVP** given target age (§17)

### Stretch / Future Work
Kid-uploaded reference; selectable art styles; multi-language; auto-approve toggle (deferred behind an
ethics re-review); social sharing; on-device generation; style LoRA; C2PA provenance.

---

## 9. Design & UX Direction

- **Kid flow (steps 3–10):** cartoon-pop — rounded shapes, warm saturated palette, soft depth, friendly micro-interactions (Motion), minimal text, large touch targets, Lottie wait-state animations. Every wait state needs a visible, kid-legible explanation.
- **Teacher flow (steps 1–2, 11, dashboard — ADR-017):** same color DNA, calmer/denser grid/card layout (shadcn/ui acceptable here).
- Specific tokens (palette hex, type pairing, spacing, radius/shadow) are an implementation decision informed by the cartoon-pop direction; see the frontend-design skill at build time.
- **Failure/moderation states get the same design care as success states.** A harsh failure screen is a larger UX risk here than in a general-audience app.

---

## 10. Objectives & Evaluation Plan

> **Full study design, instruments, ethics staging, and defense preparation live in
> `docs/product/RESEARCH_PROTOCOL.md`.** This section is a summary. Where they disagree, ADR-008 wins.

### The five objectives

There is **no RQ apparatus** — "RQ1".."RQ6" are retired (ADR-008, revised 2026-07-25). The manuscript
states five objectives:

1. **Implement** an orchestrated AI pipeline as the core processing framework of StoryBuddy.
2. **Produce** digital picture books from child-written stories through the implemented pipeline.
3. **Determine the acceptability** of the generated digital picture books in terms of presentation quality
   and classroom suitability, through **expert validation**.
4. **Evaluate the character-consistency classification performance** of the fine-tuned lightweight VLM
   against human-established reference labels — **precision, recall, and F1-score (F1 primary)**.
5. **Evaluate the software quality** of StoryBuddy using applicable **ISO/IEC 25010** quality
   characteristics.

Objectives 1–2 are the build. **Objectives 3, 4, and 5 are the three evaluation legs.** Scene coverage
against a story's major plot points and graceful under-length handling are described **pipeline
behaviours** of Scene Segmentation (§5.1, §8), not standalone measured objectives with their own
instrument.

⚠️ **Objective 3 is never scored using the consistency judge.** The judge drives regeneration inside the
pipeline; using it as the outcome measure would be circular. The judge's own accuracy is the separate
Objective 4 question, measured on a human-labeled, character-disjoint held-out set. See ADR-004's
non-circularity note.

⚠️ **Do not claim learning gains.** The corpus is 15 stories (10 primary + 5 backup, below), no
non-illustrated control, no pre/post, no longitudinal window. Prior literature on authentic audience is
the *warrant* for why acceptability matters; it is not a finding of this study.

### Evaluation design (see ADR-008)

**Three legs, one per evaluation objective — no reader-comprehension leg.**
- **Objective 3 — expert validation.** Purposively selected expert validators — the Dean/Professor of the
  Arts College, one Arts student/intern, one Education student/intern — respond to a **written,
  open-ended interview form** (Tool B). Responses are analysed by **content analysis**: each is
  coded **positive / negative / suggestion** per criterion, across five criteria (narrative coherence,
  story faithfulness, visual presentation, visual style consistency, classroom suitability). This replaces
  the earlier feature-level scored rubric (CVI / Krippendorff's α).
- **Objective 4 — judge classification.** The fine-tuned `Qwen2.5-VL-7B-Instruct` (QLoRA) judge predicts
  Same/Different Character on the character-disjoint held-out set; scored against human reference labels
  with **precision, recall, F1 (F1 primary)**. **Optionally**, reported alongside the zero-shot base model
  and the existing prompted baseline on the same held-out pairs — secondary to the absolute agreement
  figure, not a replacement for it. ADR-018's δ = 3 non-inferiority test remains a **deployment gate**
  (does the fine-tuned judge replace the prompted incumbent in the product), not a reported finding. Full
  machinery in ADR-018 and `docs/specs/judge-finetune.md`.
- **Objective 5 — software quality.** The ISO/IEC 25010 questionnaire (Tool C) — five applicable
  characteristics (Functional Suitability, Performance Efficiency, Usability, Reliability, Security),
  5-point Likert, weighted mean + SD per characteristic, interpreted against Table 4 bands
  (4.20–5.00 Excellent · 3.40–4.19 Very Good · 2.60–3.39 Good · 1.80–2.59 Fair · 1.00–1.79 Poor) —
  administered to **designated software-quality evaluators** (IT practitioners and teachers), separate
  from the expert validators.

**Objectives 1–2 are the built artifact, verified — not judged — by Tool A.** The **Functional Verification
Matrix** records system-generated pass/fail per functional category (input validation & moderation, story
analysis, scene structuring, visual planning, scene generation & refinement, picture book production) as
`Successful ÷ Total × 100`. It has **no human respondents**, runs on **fixture stories** — so it carries no
ethics load and is defensible in October — and is computed by an offline script over tracing exports, not a
dashboard (`docs/specs/functional-verification-matrix.md`, ADR-026).

⚠️ **A Pass is not a quality claim.** A Pass means the stage executed and emitted valid output. For scene
generation a Pass means *the loop shipped a page* — **including a page the judge flagged and best-of-fell-back
on**. Defining Pass as "the judge approved it" would score outputs with the judge and break non-circularity
(ADR-004).

### Researcher-facing surfaces

Two authenticated routes, built in Phase 2.5 on the Phase-2 `researcher` role — **`(research)/annotate/`** (with
`adjudicate/`) for Objective 4's labelling, and **`(research)/books/`** to serve Objective 3's stimuli with
provenance stripped and order shuffled. Blinding is enforced in code rather than by discipline. There is no
metrics dashboard and no run-trace viewer; the latter is what LangSmith is for (ADR-014). Objectives 3 and 5
collect their responses on paper and by form, not in-app. Rationale and rejected alternatives: **ADR-026**.

### Respondents

| Group | Role | Contributes to |
|---|---|---|
| Grade 5–6 learners | Write original stories only — no evaluation role | Corpus |
| Expert validators (Dean/Professor Arts College, Arts student, Education student) | Written open-ended interview + content analysis | Objective 3 |
| Designated software-quality evaluators (IT practitioners, teachers) | ISO/IEC 25010 questionnaire | Objective 5 |

Full detail (recruitment, instruments, ethics staging): `docs/product/RESEARCH_PROTOCOL.md` §4–§10.

### Metrics
| Metric | What it measures | Source |
|---|---|---|
| Functional verification (Objectives 1–2) | Per-category success rate, `Successful ÷ Total × 100` | Tool A — offline script over tracing exports, on fixture stories |
| Expert validation (Objective 3) | Positive / negative / suggestion tallies per criterion | Content analysis, Tool B |
| Judge classification (Objective 4) | Precision, recall, F1 (F1 primary) vs human reference labels | Held-out test set; optional comparison vs zero-shot base + prompted baseline |
| Software quality (Objective 5) | Weighted mean + SD per ISO/IEC 25010 characteristic | Tool C |
| Generation Time | Submission → completed storybook | Instrumentation (§16) |
| AI Resource Usage | Avg generation time, image count, regen count, API cost/story | Instrumentation (§16) |

### Story corpus (validity — do not skip)
Corpus = **donated child writing + researcher labels**: **15 stories collected from Grade 5–6 learners at
Matina Aplaya Elementary School → 10 primary + 5 backup.** System development and evaluation take place at
**Holy Cross of Davao College (HCDC)**, Davao City, Philippines. Not builder-authored clean text, which
would measure best-case behavior only. Researcher-written stories are permitted **only** as
judge-training-split augmentation — never as evaluation stimuli and never in the judge's val/held-out-test
splits. Document provenance — reviewers will ask.

### ⚠️ Ethics timeline
Formal ethics review (**Data Privacy Act of 2012, Republic Act No. 10173** + your university's ethics
board; not US "IRB" per se) can take weeks. **Start in parallel with development, week 1.** Stage-1 story
donation (RESEARCH_PROTOCOL §9) is the long pole and unblocks the corpus; Stage 2 gates classroom system
use only, not any evaluation leg.

---

## 11. Open Decisions — RESOLVED

1. **Teacher approval gate before a book enters the gallery or is exported** → **manual, always** (human backstop over auto-moderation; no auto-approve bypass — deferred to Future Work behind an ethics re-review). *Was "parent approval gate" — ADR-017.*
2. **Regeneration cap** → **1 targeted, prompt-corrected retry** (2 attempts total); if still failing, keep the higher-scoring image (best-of), never a broken/placeholder page. ADR-010.
3. **Story length limit** → **hard word cap (~500–800 words, tunable)** with a gentle "let's make a book of the first part" truncation at a scene boundary. **No silent AI summarization** (it would illustrate the summary, not the child's story). ADR-012.
4. **Repeated moderation-failure off-ramp** → after **N=3** failed revisions of the same story, suggest starting a fresh story rather than an unbounded retry loop.
5. **Multiple main characters** → **max 2 canonical references** in v1; generation conditions on multiple reference images; the checker verifies **each character separately** against its own reference. ADR-004.
6. **Very short stories** → **fewer scenes allowed**; scene count tracks the story's distinct major plot points, target ≥3 where the arc supports it, never padded to reach it (never-invent overrides the floor). Described as a pipeline behaviour of Scene Segmentation, not a standalone evaluation objective (RESEARCH_PROTOCOL §4).
7. **Whole-run timeout / stall** → **LangGraph checkpointing + resumability**: a stall at scene N resumes from N, never re-rolls scenes 1…N-1. Kid sees "taking a little longer…" then "we saved your progress — come back soon." ADR-005.
8. **Image model/API** → **Qwen-Image-Edit (Apache-2.0) on fal.ai.** Open weight, hosted. ADR-001, ADR-015.
9. **Moderation services** → text (**meta-llama/llama-guard-4-12b** on the OpenRouter + **`gpt-oss-safeguard-20b`** on OpenRouter, both Apache-2.0) + PII (Presidio + **Filipino recognizers**) + image (NSFW ViT + VLM safety rubric). **Two independent open classifiers per path.** §13, ADR-011.
10. **Fine-tuning** → **the consistency judge** (`Qwen2.5-VL-7B`, QLoRA), served on vLLM. Identity and style
    remain the *wrong* targets — ADR-016's reasoning is preserved and is precisely why the judge is right. **ADR-018, ADR-019.**
11. **What "open source" means** → **open weight**, hosted inference, self-hosting available — and, as of
    2026-07-10b, **no proprietary models anywhere**, including backstops and accessories. ADR-015 (hardened).
12. **Setting and gatekeeper** → **teacher- (or BEED-student-) issued classroom account**, Grade 5–6
    students as authors who log in and operate the app directly, teacher narrowed to account issuer +
    reviewer, sharing scoped to the classroom, **no public mode**. Parent is the consent-giver, not an
    operator. **ADR-017.**
13. **Classroom gallery** → display-only; the approved storybook is the only peer-visible artifact. No
    reflection/comment surface, no research instrument riding on it — the child-facing Story Map stays
    cut. **ADR-021.**

---

## 12. Technical Architecture

**Frontend:** Next.js (React) + Tailwind + shadcn/ui (teacher) + hand-built cartoon-pop components (kid) + Motion (micro-interactions) + Lottie (wait states). Deployed on Vercel.

**Backend:** FastAPI (web) + **separate RQ worker** + **Redis** (broker), on Northflank (Render/Fly.io equivalent; Singapore region). *A long pipeline cannot run in a request cycle — this is a 3-service deployment, not one.*

**Pipeline engine:** **LangGraph as a deterministic state machine** (explicit nodes; conditional edges only at moderation pass/fail and consistency pass/fail). LangChain omitted unless a concrete need appears. Model APIs called directly through `backend/providers.py` — the only file that names a vendor (ADR-003, ADR-015).

**State/persistence:** Supabase Postgres (app data + LangGraph checkpoints via `langgraph-checkpoint-postgres`); Supabase Auth (teacher) + classroom-scoped student auth + RLS; Supabase Storage (images + PDFs, signed URLs); Supabase Realtime (job progress). ADR-006.

**Structured extraction:** strict `json_schema` structured output + `provider.require_parameters: true` + Pydantic validation on every LLM boundary. The Story Memory schema is the contract between modules. ADR-002.

**Export:** HTML storybook template → PDF via Playwright/WeasyPrint (server-side) — decide at build (ADR-013).

**Flow:** `POST /storybooks` creates a job row, returns `job_id` immediately → worker runs the LangGraph pipeline, checkpointing after each scene, updating job status → frontend subscribes to the job row via Realtime → on completion, images/PDF in Storage, book in library.

---

## 13. Moderation & Safety Stack

Four distinct concerns, four mechanisms. **Open classifier as the gate, free proprietary classifier as
an independent backstop; either one flagging fails the content** (ADR-011).

1. **Input text moderation** — **`meta-llama/llama-guard-4-12b`** (Apache-2.0, 119 languages, the 0.6B variant on the
   OpenRouter) + **`openai/gpt-oss-safeguard-20b`** (Apache-2.0 open *weights*, via OpenRouter, independent
   backstop) on the child's story before any processing. Gentle, non-scary failure copy.
   meta-llama/llama-guard-4-12b's multilingual coverage closes the Filipino/Taglish hole *by construction*; gpt-oss-safeguard
   supplies the vendor independence the removed OpenAI backstop used to. **Both open.**
   *(Granite Guardian was the ADR-011b backstop; it is **not routable on OpenRouter** — verified 2026-07-13,
   D-1 resolved in ADR-011 revision c.)*
2. **PII detection/redaction** — Presidio (open-source) on input. A child narrating real life ("my name is… I live at…") is the *expected* case; redact before storage/captioning/export. This is separate from toxicity moderation.
   ⚠️ **Presidio's defaults leak Filipino PII.** spaCy NER misses Filipino names; `Barangay`/`Purok`/`Sitio`
   address structure and `+63 9xx` formats match no built-in pattern. Custom recognizers are a **Phase-2
   deliverable**, not a polish item (ADR-011).
3. **Output image moderation** — on **every generated image, including the canonical character reference
   before the reveal (flow step 7)**. No generated image reaches a child unmoderated.
   - `qwen/qwen3-vl-32b-instruct` (86M ViT, Apache-2.0, CPU, milliseconds) — sexual content.
   - `google/gemma-3-27b-it` with a safety rubric — violence, gore, dangerous content, which the
     NSFW classifier does **not** cover. **Never the fine-tuned judge** (ADR-004 amendment b) — consistency
     has a best-of fallback, safety has none.
   - These two are *complementary*, not independent. **ShieldGemma 2** on ADR-019's GPU container is the
     optional hardening that restores true redundancy.
4. **Model self-refusal fallback** — the image model may refuse legitimate mild-peril scenes ("fight the dragon"). On refusal: soften-and-retry the prompt, then a gentle "let's imagine that part a little differently." A scary-but-innocent story must not dead-end.

Ordering matters: input gate (step 5) → char-ref moderation (before step 7) → output moderation (step 9).

> ⚠️ **The open image model ships no built-in safety filter.** Under the proprietary stack, Google's
> filter was a silent second line of defense behind SafeSearch. It is gone. Mechanism 3 is now the
> *only* thing between a generated image and a child — load-bearing, not defense-in-depth. Expect
> mechanism 4 (self-refusal) to fire *less* often; do not read that as the system being safer.
>
> ⚠️ **Both text gates are unverified in Filipino and Taglish until the Phase 0.5 moderation probe runs.**
> A miss on a harmful case is a child-safety hole; a miss on a benign case dead-ends a child's dragon
> fight. The probe tests both directions and is a **release gate for Phase 2**.

---

## 14. Security & Data Protection

- **RLS everywhere.** Teachers read only their own classroom's data; children read only their own account's data; enforced at the DB layer, not just the app.
- **Signed URLs** for all kid-generated images/PDFs; no public buckets.
- **Data retention & deletion path.** Define what's stored (account, stories, images, logs), for how long,
  and give the teacher a one-action **delete-a-student's-data** path, actionable on a guardian's request.
  Required posture under the PH Data Privacy Act.
- **Minimal kid PII by design** — nickname + teacher-set password only; no email, no self-serve signup, no
  direct collection from the minor beyond the account itself and their own typed story
  (which routes through PII redaction, ADR-011).
- **Rate limiting / abuse** — `slowapi` + per-account daily generation cap (also protects budget). Addresses single-account abuse.

---

## 15. Cost Model

At ~$0.02–0.035/image (Qwen-Image-Edit; $0.02 on Novita, $0.035 on fal.ai): one book ≈ 1 reference +
~12 scenes + regenerations ≈ 15–18 images ≈ **~$0.30–0.65**, ~$1 worst case. Text/VLM calls add pennies.

At **200 books/month** (2,000 images), the whole open-weight stack runs **~$60–110/month**, dominated by
image generation:

| Layer | Monthly |
|---|---|
| Image generation (2,000 images) | $40–70 |
| VLM judge (2,000 calls, two images each) | $5–15 |
| Text LLM (~200 stories) | $2–10 |
| Text moderation (meta-llama/llama-guard-4-12b on OpenRouter + `gpt-oss-safeguard-20b`, ADR-011c) | $1–5 |
| Image moderation (CPU classifiers on the existing worker) | $0–10 |

- **Develop against the cheapest provider; spend paid budget only on study runs.**
- Recommended budget for comfortable dev + a real study: **~$50–100**. Trivially cheap; don't constrain the research over ~$30.
- **Cost circuit-breaker:** a per-book worst-case ceiling that trips rather than silently running; per-classroom daily cap (§14).
- **Fine-tuning the judge is a one-time ~$5–15** on a rented 4090 (ADR-018). **Set a budget alarm.**
- **Serving the judge *lowers* running cost**: ~2,000 calls/month at ~3 s each is ~100 GPU-minutes on a
  scale-to-zero container, cheaper than 2,000 Gemma-27B API calls (ADR-019). Keep-warm during a study
  session is ~$1/hr.
- **Narration is a small metered cost** — ~cents/book of hosted expressive TTS (Chatterbox on fal.ai),
  minor beside image generation; the Kokoro CPU fallback is $0 if the metered path is dropped (ADR-020, revised).

---

## 16. Observability (doubles as research instrumentation)

Instrument the pipeline with **LangSmith** (native LangGraph tracing; ADR-014 — resolved). This captures generation time, per-scene regeneration counts, cost per book, and VLM-judge scores — i.e. the "AI Resource Usage" metrics and a large share of the eval dataset. Add **Sentry** for error tracking. Instrument from the walking-skeleton phase so data collection is free by the time you evaluate.

---

## 17. Accessibility

The primary user is a Grade 5–6 student. They read and type, but reading a story aloud is still a
comprehension aid, and it is what makes a *picture book* feel like a book.

**Narration: `Chatterbox`** (MIT, expressive open-weight TTS) — served via **hosted inference on fal.ai**; the
worker pre-renders one MP3 per page onto Supabase Storage during generation and the frontend is an `<audio>`
tag (ADR-020, revised). Emotion-intensity is tuned once to a warm storyteller register. **`Kokoro-82M`**
(Apache-2.0, CPU) is the zero-cost fallback. Narration reads the child's **verbatim redacted text**, so it adds
no moderation surface — but note it now travels to the TTS host (same trust boundary as the image/text calls;
ADR-015 claims no privacy guarantee).

- **Word-level highlighting is deliberately dropped.** It needs character-level timestamps (the one thing
  ElevenLabs sells) and it is a fluency aid for *emergent* readers. This age band reads. Add it if a teacher asks.
- ⚠️ **English-only, still.** No open expressive TTS supports Tagalog/Taglish; sentences are read with English
  phonology. A recorded limitation — not a regression from Kokoro.
- **Speech-to-text for story input** (`SpeechRecognition`) remains a possible enhancement, not MVP.

Large touch targets, high contrast, and minimal on-screen text throughout the student flow.

---

## 18. Delivery Approach

**Walking skeleton → vertical slices → hardening** (see ROADMAP). Not waterfall (riskiest assumptions — consistency loop, model behavior, async latency — can only be validated by building, so hit them week 1). Not heavy agile ceremony (solo). Up-front design = this PRD + the Story Memory schema + the LangGraph shape (expensive to rework, so settled first). Ethics/consent track runs in parallel from week 1.

---

## 19. Reference: Story Memory Data Shape (v2 sketch — finalize in implementation)

```json
{
  "classroom_id": "",
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
  "style": { "style_preset_id": "", "prompt_fragment": "" },
  "scenes": [
    {
      "scene_id": "",
      "text_excerpt": "",
      "caption": "",
      "characters_present": [],
      "prompt": "",
      "attempts": [
        {
          "image_ref": "",
          "vlm_verdict": {
            "differences_observed": "",
            "same_character": false,
            "attributes_present": [],
            "style_match": false
          },
          "failure_reasons": [],
          "passed": false
        }
      ],
      "final_image_ref": "",
      "consistency_check_status": "",
      "regeneration_count": 0,
      "moderation_status": ""
    }
  ],
  "narration": [{ "scene_id": "", "audio_ref": "" }],
  "sharing": { "teacher_approved": false, "in_gallery": false },
  "cost": { "image_count": 0, "regen_count": 0, "usd_estimate": 0 },
  "eval": { "seed": null }
}
```

**Field order inside `vlm_verdict` is load-bearing.** `differences_observed` is declared *before*
`same_character` so the judge reasons before it scores — this is the mitigation for VLM judges
conflating category similarity with instance identity (ADR-004 amendment). It survives the fine-tune:
`differences_observed` is a **training target**, drawn from a closed taxonomy, never model-generated
(ADR-018, `docs/specs/judge-finetune.md` §3.4).

**`failure_reasons` is a closed taxonomy**, shared by the judge's training targets and the regeneration
controller's prompt corrector. Design it once, in Phase 1. See `judge-finetune.md` §4.

---

## 20. Non-Functional Notes

- **Concurrency:** at demo/study scale a single serial worker is fine; "in the wild," concurrent submissions queue (acceptable) or scale RQ workers horizontally. Note the tradeoff; don't over-build for v1.
- **Reproducibility:** control seeds so generation runs are deterministic and re-runnable. ⚠️ **Seed behavior is
  provider-specific and must be verified empirically, not read off the docs** — fal.ai and Together
  document reproducible seeds; Replicate has an open, unresolved bug (#334) where seeds are ignored
  under its fast path, and distilled models (FLUX.1-schnell) are inherently less seed-stable. Probed in
  the Phase 0.5 spike. Locally, `torch.use_deterministic_algorithms(True)` is required and costs
  performance — acceptable in the offline eval harness, which is separate from production (MASTER_SPEC §6).
- **Watermarking / provenance:** ⚠️ **capability lost.** Nano Banana embedded an invisible SynthID
  watermark. SynthID-*Text* is open-sourced; SynthID-*Image* is not, and there is no drop-in equivalent.
  The layered replacement is **C2PA Content Credentials** (provenance metadata) + `invisible-watermark`
  (statistical signal) — neither alone matches SynthID's robustness. **Future Work, not MVP. Do not
  claim watermark provenance in the paper.** ADR-001.
