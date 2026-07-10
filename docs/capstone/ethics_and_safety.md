# Ethics and Safety in StoryBuddy

StoryBuddy is an AI-powered storyboarding and picture-book generation system built for Grade 5–6 students. Because the primary users are children, the system's ethics, safety, and data protection policies are structural and non-negotiable. This document outlines the core safety mechanisms, focusing on Personally Identifiable Information (PII) redaction, the moderation pipeline, and the implications of operating within an open-weight model ecosystem.

## 1. PII Redaction (Presidio) and Localization

Children narrating their real lives (e.g., "My name is Juan, and I live at...") is the expected case in a storyboarding application. To ensure student privacy, StoryBuddy employs **Presidio**, an open-source data protection tool, to detect and redact PII from the input text before any storage, captioning, or PDF export occurs.

However, standard out-of-the-box recognizers present a critical localization challenge:
* **The Filipino PII Leak:** Presidio's default recognizers are heavily English/US-centric. Standard NLP models like spaCy often miss Filipino names. Furthermore, localized address structures (such as `Barangay`, `Purok`, or `Sitio`) and Philippine mobile number formats (e.g., `+63 9xx`) do not match built-in patterns.
* **The Mitigation:** Custom Filipino recognizers are mandated as a core Phase-2 deliverable, rather than a delayed polish item. This ensures that PII specific to the Philippines is effectively intercepted.
* **Scope of Redaction:** The redaction applies uniformly across the application. Both the primary stories and peer reflections route through this exact same PII gate. 

Additionally, by design, the platform collects minimal PII from the minor—students use nicknames and avatars, and no direct sign-up data is collected from them.

## 2. Moderation Pipeline and Ordering

StoryBuddy uses a robust, four-stage safety stack. A critical design decision is the use of **two independent open classifiers per path**—from different vendors and trained on different data. If either signal flags the content, it fails. 

The strict, non-negotiable ordering of the moderation pipeline is as follows:

### Stage 1: Input Text Moderation
Before any processing begins, the child's raw story is evaluated.
* **Primary Classifier:** `Qwen3Guard-Gen` (Apache-2.0). Supporting 119 languages, it closes the Filipino/Taglish safety gap by construction.
* **Independent Backstop:** IBM's `Granite Guardian` (Apache-2.0). It replaces proprietary backstops and provides vendor independence. 
* *Action:* If flagged, the system returns a gentle, non-scary "let's try that again" message to the child. 

### Stage 2: PII Detection
* As detailed above, Presidio redacts PII before the text continues down the pipeline.

### Stage 3: Output Image Moderation
Generated images are moderated **before** the child ever sees them. This includes the canonical character reference images generated prior to the storyboarding phase. 
* **Sexual Content:** Handled by `Falconsai/nsfw_image_detection` (an 86M ViT, Apache-2.0), running on the worker CPU in milliseconds.
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
* **Teacher-Gated Classroom:** The application functions solely within a teacher-owned classroom. The teacher is the gatekeeper, creating profiles and approving books before they enter the classroom gallery or are exported.
* **No Public Mode:** There is absolutely no public sharing mode. Peer-visible child-authored content without a gatekeeper acts as an unmoderated social network, which violates the project's safety ethos.
* **Row-Level Security (RLS):** Data isolation is enforced at the database level, ensuring that users can only access their specific classroom's content.

## Conclusion

The ethics and safety architecture of StoryBuddy is built on the premise that child safety cannot rely on vendor defaults or single points of failure. By chaining localized PII redaction, independent open-weight classifiers, and a strict teacher-gated environment, the system provides a safe, reproducible, and equitable platform for children to publish their stories.
