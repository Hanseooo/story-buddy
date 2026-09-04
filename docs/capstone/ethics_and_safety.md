# Ethics and Safety in StoryBuddy

StoryBuddy is an AI-powered storyboarding and picture-book generation system built for Grade 5–6 students. Because the primary users are children, the system's ethics, safety, and data protection policies are structural and non-negotiable. This document outlines the core safety mechanisms, focusing on Personally Identifiable Information (PII) redaction, the moderation pipeline, and the implications of operating within an open-weight model ecosystem.

## 1. PII Redaction (Presidio) and Localization

Children narrating their real lives (e.g., "My name is Juan, and I live at...") is the expected case in a storyboarding application. To ensure student privacy, StoryBuddy employs **Presidio**, an open-source data protection tool, to detect and redact PII from the input text before any storage or captioning occurs.

**Amended 2026-09-01 (ADR-045).** Presidio performs two separable jobs, and StoryBuddy now runs only one of them by default. **Structured identifiers hard-redact, unconditionally** — Philippine mobile numbers, addresses, TIN, SSS, PhilHealth, plus email, phone, and card formats. There is no setting that disables this half. **Person pseudonymization is off by default.** The paragraphs below marked *(superseded)* describe the pre-amendment behaviour and are kept because the reasoning in them is still the reasoning for the identifier half; read them against the amendment, not instead of it.

However, standard out-of-the-box recognizers present a critical localization challenge:
* **The Filipino PII Leak:** Presidio's default recognizers are heavily English/US-centric. Standard NLP models like spaCy often miss Filipino names. Furthermore, localized address structures (such as `Barangay`, `Purok`, or `Sitio`) and Philippine mobile number formats (e.g., `+63 9xx`) do not match built-in patterns.
* **The Mitigation:** Custom Filipino recognizers are mandated as a core Phase-2 deliverable, rather than a delayed polish item. This ensures that PII specific to the Philippines is effectively intercepted.
* **Scope of Redaction:** Within the *product*, redaction applies uniformly — the child's story text routes through this exact same PII gate before storage or captioning.

* **The research corpus is redacted separately, by hand.** Donated stories collected for the study are **redacted manually on receipt**, independent of the product's automated Presidio stack (`RESEARCH_PROTOCOL.md` §8). This is not redundancy: the automated stack is a **Phase-2 deliverable and does not exist when the corpus starts arriving**, so for the corpus the manual protocol is the *only* gate, not a second one. Stating that "the same PII gate covers everything" would be false for exactly the data that arrives first.

* **Person names are pseudonymized, not context-gated (corrected 2026-08-13; _superseded 2026-09-01 by ADR-045 — see below_).** This section previously claimed the gate "distinguishes narrative naming from self-disclosure." It does not, and `input-gate-hardening.md` §4c argues against building one: Presidio cannot tell a child writing *"my name is Mia"* from a child inventing a character called Mia, and a context test fails in the unsafe direction — one missed disclosure sends a real name to every downstream provider. Every detected `PERSON` / `PH_PERSON` span is therefore replaced, unconditionally.

  What prevents the mangling that motivated the original claim is the *operator*, not a gate. Persons are **pseudonymized** — each distinct name maps to a stable stand-in for the duration of the call (*Mia → Maya*), so the child still gets a protagonist an illustrator can draw and a caption that reads as prose. Which stand-in a story draws varies between stories, so a classroom's books do not all star the same handful of names. The stand-in is drawn from a pool matched to the gender implied by the character's own pronouns, falling back to a gender-neutral name whenever the pronouns are absent, plural, or contradictory (`input-gate-hardening.md` §4c, amended 2026-08-13) — a child's *she* is never renamed into a boy, and the system declines to guess rather than guessing wrong. Only structured identifiers hard-redact to `<ENTITY>`. This also inverts the cost of a false positive: an over-eager match yields a wrong name, not a hole in the child's book, which is what makes the aggressive Filipino marker rule (§4b) safe to ship.

  The residual risk is now a **usability** one rather than a privacy one — a child sees their invented character renamed. It is disclosed in the reader rather than hidden, so the swap reads as a safety feature and not a bug.

* **Person pseudonymization is disabled by default (ADR-045, 2026-09-01).** The paragraph above records what was believed at the time: that a wrong name is a cheaper false positive than a hole in a child's book. Measurement did not bear that out. Renaming was not a usability cost, it was a correctness one, and every recorded failure of this function is a *person* failure — 16 of the 30 synthetic corpus records lost a declared character name; spaCy tagged `Grace` as `PERSON` once and `ORGANIZATION` twice in one story and split one child's character into two; the common noun `bush` became a character called `Cielo`; and ADR-041 traced a robot drawn with a human face to the human-coded pseudonym `Leo` standing in for `Bolt`. Three containment mechanisms — `_missed_mentions`, `_after_determiner`, and a text-seeded RNG — were built specifically to hold this behaviour together, and the failures continued past all three, because what remains are spaCy NER errors rather than logic we control.

  **What this costs, stated plainly.** A first name a child writes — including their own — now reaches the analyzer, the image providers, the stored captions, and the exported PDF. The gate that would have caught a self-disclosure is gone. This is accepted, not overlooked, and it is judged against the alternative: a pseudonymizer that corrupts the narrative the product exists to preserve, in exchange for a protection that `input-gate-hardening.md` §4c already showed cannot distinguish *"my name is Mia"* from a character named Mia. The identifier half — the part that carries the real re-identification risk, because a name alone rarely identifies a child but a mobile number or a barangay address does — is untouched and unconditional.

  **What this does not change.** Moderation runs on the raw text regardless (`input_gate.py`), so the two-classifier safety gate is unaffected. `PH_PERSON` and the Filipino marker recognizers still fire and are still counted in the `persons_detected` log field, so the cost of this decision stays measurable rather than going dark. Reverting is one environment variable, `PII_PSEUDONYMIZE_PERSONS=true`, with no code change and no migration.

  **Consent is unaffected.** The Stage-1 consent and assent forms promise redaction performed **manually by the research team** and have never referred to Presidio or to automated redaction. No statement made to a guardian or to a child becomes false through this amendment.

Additionally, by design, the platform collects minimal PII from the minor—students use nicknames and avatars, and no direct sign-up data is collected from them. Accounts are **teacher-issued**: the teacher creates each student account with a nickname and an initial password (which the child may change), with no email on the account and no self-serve signup, and password reset is teacher-initiated only. The child therefore holds a login credential but no recoverable identifier.

## 2. Moderation Pipeline and Ordering

StoryBuddy uses a robust, four-stage safety stack. A critical design decision is the use of **two independent open classifiers per path**—from different vendors and trained on different data. If either signal flags the content, it fails. 

The strict, non-negotiable ordering of the moderation pipeline is as follows:

### Stage 1: Input Text Moderation
Before any processing begins, the child's raw story is evaluated.
* **Primary Classifier:** `meta-llama/llama-guard-4-12b` (Apache-2.0). Supporting 119 languages, it closes the Filipino/Taglish safety gap by construction.
* **Independent Backstop:** `gpt-oss-safeguard-20b` (Apache-2.0, open weights) via OpenRouter. It replaces proprietary backstops and provides vendor independence (Granite Guardian was the original pick but is not routable on OpenRouter — ADR-011c). 
* *Action:* If flagged, the system returns a gentle, non-scary "let's try that again" message to the child. 

### Stage 2: PII Detection
* As detailed above, Presidio hard-redacts structured identifiers before the text continues down the pipeline. Person names are not rewritten (ADR-045).

### Stage 3: Output Image Moderation
Generated images are moderated **before** the child ever sees them. This includes the canonical character reference images generated prior to the storyboarding phase. 
* **Sexual Content:** Handled by `mistralai/mistral-small-3.2-24b-instruct` (Apache-2.0, multimodal), called via OpenRouter. It replaced `qwen/qwen3-vl-32b-instruct` on 2026-08-11: served by Alibaba Cloud that model emitted its verdict before its reasoning, which the ADR-004 field-order assertion rejects, hard-failing the job at the character-reference gate (ADR-002 amendment).
* **Violence, Gore, and Dangerous Content:** Handled by `google/gemma-3-27b-it` using a structured safety rubric. *(Note: The fine-tuned consistency judge is deliberately excluded from safety checks, as safety is a gate with no fallback).*
* *Action:* Unsafe images never reach the child.

### Stage 4: Model Self-Refusal Fallback
Because models may occasionally refuse legitimate mild-peril scenarios (e.g., "fighting a dragon"), the pipeline includes a fallback that softens and retries the prompt. If it still fails, the system gently reframes the request so the child's story does not dead-end.

## 3. Safety Policies with Open-Weight Models

StoryBuddy operates under a strict mandate to use **open-weight models** without relying on proprietary backstops. While this ensures equity—allowing the system to be run by provincial public schools with no per-seat vendor costs—it fundamentally alters the safety posture:

* **No Built-in Safety Filters:** Unlike proprietary APIs (e.g., Google's SafeSearch), open image models (like Qwen-Image-Edit) do not ship with built-in safety filters. As a result, StoryBuddy's output image moderation gate (Stage 3) is **load-bearing**, not merely defense-in-depth. 
* **No Built-in Watermarking:** The open-weight shift means dropping proprietary watermarking (like SynthID). Provenance and C2PA Content Credentials are noted as future work, but watermarking is explicitly not claimed in the current system.
* **No Assumed Language Coverage:** The Taglish and Filipino performance of open text gates is treated as a critical child-safety vulnerability. Moderation performance in these languages must be empirically probed before Phase 2 release. 
* **Data Privacy Reality:** Running open weights on *hosted inference* (e.g., OpenRouter) means the child's text still transits a third party. Consequently, the project makes **no claims of absolute privacy preservation**. 

## 4. Setting and Human Backstops

Technical gates are supplemented by strict product boundaries:
* **Teacher-Gated Classroom:** The application functions solely within a teacher-issued classroom. The child logs into a teacher-issued account and operates the app directly—authoring their own story—but the **teacher remains the sole approver**: every generated book passes teacher review before it enters the classroom gallery (ADR-017). The teacher (or BEED education student) is the account issuer and the human backstop, no longer the sole operator. An **auto-approve** toggle (letting the teacher skip that review) is deliberately deferred to Future Work: it removes the human backstop, so it **cannot ship without an ethics re-review**—the automated moderation stack still runs on every book, but a human no longer sees each one.
* **Display-Only Gallery:** The classroom gallery is display-only — the approved storybook itself is the only peer-visible artifact. There is no reflection, comment, or scoring surface of any kind (ADR-021); no additional child-typed text is ever peer-visible.
* **No Public Mode:** There is absolutely no public sharing mode, and no self-serve signup. Peer-visible child-authored content without a gatekeeper acts as an unmoderated social network, which violates the project's safety ethos; the classroom-code gate and teacher approval are what keep the gallery from becoming one.
* **Consent and Assent:** Because the child is now an active user of the system and not merely a story donor, participation requires **guardian informed consent and age-appropriate child assent** (**Data Privacy Act of 2012, Republic Act No. 10173**; see `RESEARCH_PROTOCOL.md`). A child-held account raises the consent weight above a donation-only study—this is Ethics Stage-2 scope, distinct from the Stage-1 story donation.
  The separate Stage-1 story-donation wording is currently an unapproved draft at
  `docs/capstone/story_donation_consent_and_assent_draft.md`; it must not be administered before adviser,
  institutional-ethics and participating-school approval.
* **Institutional and ethics clearances:** Data collection and evaluation are gated on clearance from both sites — **Holy Cross of Davao College (HCDC)**, where the system is developed and evaluated, and the **participating elementary school** (Matina Aplaya Elementary School, Davao City), where stories are collected from Grade 5–6 learners. Neither corpus intake nor evaluation sessions begin before both clearances are in hand.
* **Row-Level Security (RLS):** Data isolation is enforced at the database level, ensuring that users can only access their specific classroom's content—and, now that each child holds an account, isolating one child's account from another's within the same classroom, not only adult-owned rows.
* **Asset access:** RLS governs rows; it does not govern files. Every generated image lives in a **private bucket** and is reached only through a **short-lived signed URL minted on read**. There are no public buckets, and no durable asset URL is ever stored — the database holds storage *paths*. A leaked row is useless without a live signature.
* **Failure and moderation screens receive the same design care as success screens.** A child whose story is blocked, or whose generation fails, sees an age-appropriate, non-punitive explanation rather than an error state — being refused by the system is a normal outcome of a child-facing safety stack, not an edge case, and it is the moment the product is most likely to make a child feel they did something wrong.

## Conclusion

The ethics and safety architecture of StoryBuddy is built on the premise that child safety cannot rely on vendor defaults or single points of failure. By chaining localized PII redaction, independent open-weight classifiers, and a strict teacher-gated environment, the system provides a safe, reproducible, and equitable platform for children to publish their stories.
