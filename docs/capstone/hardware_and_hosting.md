# Hardware, Hosting & Compute — What Runs Where

**Purpose.** One canonical statement of *where every piece of StoryBuddy actually runs* — so the capstone
manuscript, the PRD, and the ADRs never drift into contradicting each other on hardware, hosting, or the
privacy posture. If another document says something about compute that this file does not support, this file
is the one to trust (it tracks the ADRs; see cross-references at the end).

---

## 1. The one thing to understand first

**StoryBuddy is a cloud-hosted web application. No AI model runs on the end-user's device.**

The school (the deployment/client side) needs nothing more than a **web browser and an internet connection**.
Every heavy model runs off-device, in one of two ways:

- **Hosted inference of open weights** — the model's weights are open (Apache-2.0 / MIT), but we call them
  over HTTP on a managed GPU provider (fal.ai for images and narration, OpenRouter for text/VLM). We do not
  own or operate the GPU; we make an API call. This is what satisfies the open-weight mandate (ADR-015):
  *openness is a property of the weights; hosting is a separate question.*
  > ⚠️ **This reading is an operating assumption, not a confirmed one.** ADR-015 records that the project
  > owner — not the supervisor — judged hosted inference of open weights to satisfy the requirement, and
  > flags it for explicit confirmation before Phase 2 hardening. If the mandate turns out to mean
  > *self-hosted*, this section's architecture changes: a GPU service and its ops. The pipeline code does
  > not, because every vendor call is isolated in `backend/providers.py` — that isolation is the insurance
  > premium for this assumption.
- **A couple of small CPU models on our own server worker** — the moderation classifiers (and, as a fallback,
  Kokoro narration) are small enough to run on the CPU of the backend worker container (Railway). No GPU.

This is why the "should we run three models locally?" question dissolves: **in v1 we run essentially none of
the models locally** — not on the child's device and not on a developer GPU in production. Heavy models are
hosted; only tiny CPU classifiers sit on the server. Running models *on the user's machine* is a different
architecture entirely ("on-device," ADR-015 Reading 3), and it is explicitly **Future Work**, not v1.

---

## 2. What runs where (the full map)

| Component | Model / tech | Where it runs | Why there |
|---|---|---|---|
| Frontend web app | Next.js / React | **Vercel** (CDN + SSR) | Static + server-rendered pages; user's browser is the client |
| Backend API + job worker | FastAPI + RQ worker + Redis | **Railway** (Singapore) | Async job architecture (ADR-005); 3 services in one region |
| App data, auth, storage, realtime | Supabase (Postgres, Auth, Storage, Realtime) | **Supabase** (managed) | One service covers DB + auth + signed-URL storage + progress (ADR-006) |
| Story analysis / segmentation / prompts | `qwen/qwen3-32b` (open) | **OpenRouter** (hosted open weights) | Capable LLM behind one OpenAI-compatible API (ADR-002) |
| Consistency judge (VLM) | `gemma-3-27b-it` prompted → fine-tuned `Qwen2.5-VL-7B` | **OpenRouter**, later **Modal** GPU (ADR-019) | Prompted in early phases; self-hosted LoRA after Phase 2.5 |
| Image generation | `Qwen-Image-Edit` (Apache-2.0) | **fal.ai** (hosted open weights) | Reference-conditioned edit per scene (ADR-001) |
| **Narration (TTS)** | **`Chatterbox`** (MIT, expressive) | **fal.ai** (hosted open weights) | Expressive read-aloud; open-weight; per-page HTTP call (ADR-020, revised) |
| Narration fallback | `Kokoro-82M` (Apache-2.0) | **Railway worker CPU** | Zero-cost fallback if the hosted TTS is unavailable (ADR-020) |
| Input-text moderation | `Qwen3Guard-Gen` 0.6B + `gpt-oss-safeguard-20b` | **Railway worker CPU** / OpenRouter | Two independent open classifiers, both Apache-2.0 (ADR-011, revised 2026-07-21c — Granite Guardian is not routable on OpenRouter) |
| PII redaction | Presidio + spaCy | **Railway worker CPU** | Redact before storage/captioning/export (ADR-011) |
| Output-image moderation | `Falconsai/nsfw_image_detection` ViT (CPU) + `gemma-3-27b-it` (hosted) | **Railway worker CPU** + OpenRouter | NSFW gate on-worker; violence/gore rubric hosted (ADR-011) |
| Tracing / errors | LangSmith, Sentry | Managed services | Observability, not models (ADR-014) |

**Reading of the map:** the only models resident on hardware *we* operate are small CPU classifiers on the
Railway worker. Everything expressive or large (image, text, VLM, expressive TTS) is a hosted API call. The
one optionally self-hosted GPU service — Modal, for the fine-tuned judge (ADR-019) — is **the first thing on
the de-scope ladder** and nothing may hard-depend on it.

---

## 3. Split hardware specification (per adviser's comment)

The original single hardware table conflated two different machines. They are split below.

### 3a. Development Environment Hardware
*What the student needs to build, orchestrate, fine-tune, and evaluate the system.* This is a developer
workstation, not a server — it never serves the deployed product to users.

| Component | Recommended specification | Purpose in development |
|---|---|---|
| Processor | Intel Core i5 (12th Generation) | Running the frontend dev server, FastAPI backend, and RQ worker locally |
| Memory (RAM) | 24 GB (minimum 16 GB) | The local worker holds the small CPU models (moderation classifiers, Kokoro fallback) during development |
| Graphics (GPU) | NVIDIA RTX 3050 Laptop GPU | **Light local prototyping only** — trying small models locally. *Not* used to serve production and *not* used to train the judge |
| Storage | 512 GB SSD | Codebase, story corpus, model caches, generated-output samples |

**Training & serving GPU (not part of the dev workstation — a separate box for the one-time fine-tune):**

| Resource | Specification | Purpose |
|---|---|---|
| CyberLab PC *(primary — tentative, specs to be confirmed)* | NVIDIA RTX 4060, 32 GB — *tentative; subject to change, pending confirmation* | One-time QLoRA fine-tune of the consistency judge; trained remotely via **AnyDesk** |
| Rented training GPU *(fallback)* | NVIDIA RTX 4090 (~24 GB) or A100, ~US$0.45–1.50/hr | One-time QLoRA fine-tune of the consistency judge (~US$5–15 total), a few hours (ADR-018). *Rent, do not buy* — the RTX 3050 cannot train a 7B VLM |
| Optional serving GPU | Scale-to-zero container (Modal / RunPod) | Serving the fine-tuned judge behind vLLM, if deployed (ADR-019). First item on the de-scope ladder |

> ⚠️ **Confirm the VRAM, not the RAM.** "RTX 4060, 32 GB" almost certainly reads as *RTX 4060 GPU + 32 GB
> system RAM* — but QLoRA is gated by **GPU VRAM**, and an RTX 4060 has **8 GB** (16 GB on a 4060 Ti). A 7B
> VLM QLoRA with two-image inputs wants **~16 GB+ VRAM**, so an 8 GB card likely runs out of memory. The
> CyberLab PC is the intended primary *if its VRAM turns out sufficient*; the rented RTX 4090 fallback exists
> precisely for the case where it is not. Verify the exact GPU model and VRAM before committing the training run.

The RTX 3050 laptop is therefore a **development convenience**, not a system requirement, and the fine-tune
runs on a separate box — the CyberLab PC if confirmed suitable, otherwise a rented GPU on demand
(ADR-016/ADR-018's "rent, don't buy").

### 3b. Deployment / Client Environment Hardware
*What the school needs to run the finished product.* Because all generation happens in the cloud, this side
is deliberately minimal — the point of the equity argument (ADR-015, SDG 4) is that a provincial public
school can run this on ordinary hardware.

| Component | Requirement | Notes |
|---|---|---|
| Client device | Any modern PC, laptop, Chromebook, or tablet | Runs a **web browser only** — no installation, no GPU, no special hardware |
| Web browser | Current Chrome, Edge, Safari, or Firefox | The app is a responsive web application |
| Network | Broadband internet connection | All model inference happens in the cloud; the device sends text and streams back images, audio, and PDFs |
| (Server side — provisioned by the developer, **not** the school) | Vercel + Railway + Supabase + fal.ai + OpenRouter + optional Modal | Listed for completeness. The school provisions none of this; it is the hosted backend |

**The distinction that matters for the defense:** the RTX 3050 answers "what did the *researcher* need to
build this?"; the browser-and-internet row answers "what does a *school* need to use it?". They are not the
same machine, and conflating them overstated the deployment requirement.

---

## 4. Software & services specification (updated)

| Software / service | Purpose |
|---|---|
| Next.js & React | Frontend web application framework |
| FastAPI (Python) | Backend framework for API routing and job handling |
| Supabase | Database (Postgres), Authentication, Storage, and Realtime syncing |
| LangGraph & Redis | AI pipeline orchestration and background job queuing |
| OpenRouter | Hosted inference for open-weight LLMs / VLMs (text pipeline, prompted judge) |
| fal.ai | Hosted inference for the open-weight **image model** (Qwen-Image-Edit) **and narration** (Chatterbox) |
| Modal *(optional, late/de-scopable)* | Scale-to-zero GPU serving the fine-tuned judge via vLLM (ADR-019) |
| LangSmith & Sentry | Pipeline tracing (doubles as research instrumentation) and error tracking |
| Visual Studio Code | Primary source-code editor |
| Vercel & Railway | Cloud hosting for the frontend and backend, respectively |

*Change from the earlier table:* fal.ai is now noted as serving **both image and narration** inference, and
Modal is added as the optional GPU service for the fine-tuned judge.

---

## 5. Local vs hosted vs rented — three phrases that must not be confused

| Term | Meaning in StoryBuddy | Used for |
|---|---|---|
| **Hosted inference** | Open-weight model, run for us over HTTP by a managed provider | Images (fal.ai), narration (fal.ai), text/VLM (OpenRouter) — the v1 default |
| **On our server (CPU)** | Small model resident on the Railway worker container | Moderation classifiers, Presidio, Kokoro fallback |
| **Rented GPU (on demand)** | A cloud GPU we rent by the hour for a bounded job | Fine-tuning the judge; optionally serving it (Modal) |
| **Local / on-device** *(Future Work)* | Model runs on the developer's or the user's own machine | Prototyping only in v1; a genuine on-device deployment is Reading 3 of ADR-015 and out of scope |

**Why not run everything locally for privacy?** Because (a) the available consumer GPU (RTX 3050, 4–8 GB
usable) takes minutes per image at quality and cannot serve a timed user study, and (b) it would relocate,
not remove, the GPU dependency (drivers, CUDA, cold starts) onto a solo build. On-device is *reachable* — the
same open weights run quantized on a 12 GB card — but it is a deployment rewrite, not a v1 option (ADR-015).

---

## 5a. Are the models too heavy to run locally? (Yes — the big three)

The honest per-model answer, which is *why* v1 uses hosted inference:

| Model | Size | Realistic VRAM to run at usable speed | On an ordinary school PC? |
|---|---|---|---|
| Image generation (Qwen-Image-Edit) | ~20B | 24–48 GB (or quantized on 12–16 GB at **minutes per image**) | **No** |
| Text pipeline (qwen3-32b) | 32B | ~20 GB+ (Q4) — a 24 GB card | **No** |
| Prompted judge (gemma-3-27b) | 27B | ~16–20 GB (Q4) | **No** |
| Fine-tuned judge (Qwen2.5-VL-7B) | 7B | ~6–8 GB inference; ~16–20 GB to *train* (QLoRA) | Inference: maybe, on a 12 GB+ GPU |
| Narration (Chatterbox) | 0.5B | ~4–6 GB | Yes, on a modest GPU |
| Moderation (Qwen3Guard 0.6B, NSFW ViT, Presidio) | ≤0.6B | CPU | Yes |

**So "run it on hardware a school already owns" is false for the compute-heavy core.** The image, text, and
prompted-judge models each need a datacentre-class GPU. Only the small tail (7B judge, Chatterbox, the CPU
classifiers) is locally feasible. This is the exact reason ADR-015 chose hosted inference for v1 and parked
on-device deployment as Future Work — and why the value-proposition claim is "self-hostable / no per-seat
cost," **not** "free on the school's PC."

## 5b. Where the fine-tuned (and other) models are hosted — and why not Bedrock

**Inference (v1):** hosted open weights — **fal.ai** (image + narration), **OpenRouter** (text + prompted
judge). No GPU we own.

**Serving the fine-tuned judge (Phase 2.5+, optional):** **Modal** scale-to-zero GPU container behind vLLM,
OpenAI-compatible (ADR-019). **RunPod Serverless** and **Baseten** are drop-in equivalents. This is the *only*
GPU service we operate, and it is the first thing on the de-scope ladder.

**Why not AWS Bedrock (or a comparable managed catalog):**
- **It cannot serve our custom judge.** Bedrock Custom Model Import supports a fixed set of *text* architectures
  (Llama, Mistral, etc.); it does **not** import a multimodal Qwen2.5-VL QLoRA adapter. Our judge is exactly
  that, so Bedrock is a non-starter for the one model we self-host.
- **Our other models aren't in its catalog.** Qwen-Image-Edit and Chatterbox are not Bedrock-hosted; fal.ai is.
- **It adds AWS surface for no gain.** OpenRouter + fal.ai + Modal already cover every need at lower ops and
  lower cost for a solo build. Bedrock would be a heavier, pricier path to the same place. *(Verify the
  Custom-Model-Import support matrix if this is ever revisited — it changes.)*

## 5c. Training compute — the options (ranked)

Fine-tuning the judge is a **one-time ~$5–15, few-hour QLoRA run** (ADR-018). The intended plan and its fallback:

1. **CyberLab PC via AnyDesk (primary — tentative).** The school's lab PC (tentatively RTX 4060, 32 GB
   system RAM — *to be confirmed*), trained remotely over AnyDesk. Free, and it doubles as a self-hosting
   story (5d). Conditions that must hold, or it falls back to option 2:
   - **VRAM is the blocking spec.** QLoRA on a 7B VLM (two-image inputs) wants **~16 GB+ VRAM**. An RTX 4060
     is 8 GB (16 GB on a 4060 Ti) — the "32 GB" is system RAM, not VRAM. **Confirm the exact GPU + VRAM first;**
     8 GB likely OOMs and forces the rented fallback.
   - **AnyDesk is a GUI remote, not a compute workflow.** A multi-hour job driven through a remote desktop is
     fragile: launch under `tmux`/`nohup` so a dropped session doesn't kill the run, and treat AnyDesk as a
     viewport only. SSH is far better if the lab allows it.
   - **It is a shared, scheduled machine** — reboots, updates, and class bookings are outside your control.
   - **Data care:** training data derives from children's stories (Stage-1 consent). Keep it access-controlled;
     do not leave it resident on a shared lab PC.
2. **Rented cloud GPU on demand (fallback).** An RTX 4090 (~24 GB, ~US$0.45/hr) or A100 on RunPod / Vast.ai /
   Modal. Reliable, headless (SSH + `tmux`), pay only for hours used, no dependency on a shared machine —
   ADR-016/018's "rent, don't buy." This is the dependable path if the CyberLab VRAM proves insufficient.
3. **The dev laptop (RTX 3050)** — **cannot** train the 7B VLM judge (4–8 GB usable vs ~16–20 GB needed).
   Prototyping and inference of small models only.

## 5d. A better use for the cyberlab PC: a self-hostability demo

If that lab PC turns out to have a **≥12 GB GPU**, its strongest contribution is *not* training but standing up
a live **self-hosting demonstration** of the lighter half of the stack — the fine-tuned 7B judge, Chatterbox
narration, and the CPU moderation classifiers — running on hardware a school actually owns. That is concrete,
honest evidence for the equity claim (Layer 2 of `value_proposition.md`) **without** pretending the 20–32B
image/text models run there (they don't). It substantiates *"self-hostable"* precisely, and no further.

## 6. Privacy posture — stated once, consistently

**StoryBuddy does not claim a privacy guarantee, and no document should imply one.** In v1 the child's text
transits third-party hosts (OpenRouter for analysis, fal.ai for image prompts and now narration). This is a
deliberate, documented limitation (ADR-015), mitigated — not eliminated — by:

- **PII redaction (Presidio) before** anything is stored, captioned, exported, or sent to a model (ADR-011).
- **No PII collected from children at all** — teachers create nickname+avatar profiles; students never sign
  up (ADR-017).
- **RLS classroom isolation, signed URLs, no public buckets** (ADR-006).

The narration change (ADR-020, revised) adds one data flow — redacted text to the TTS host — that is the
**same trust-boundary class** as the image and text calls already crossing to fal.ai and OpenRouter. It does
not worsen the posture, and it does not license a stronger privacy claim. A real privacy *guarantee* requires
the on-device architecture (ADR-015 Reading 3), which is Future Work.

---

## Cross-references

- **ADR-001** — image model on fal.ai (hosted open weights)
- **ADR-002** — text/VLM on OpenRouter
- **ADR-005 / ADR-009** — async architecture; Vercel + Railway hosting; worker RAM budget
- **ADR-011** — moderation stack (which classifiers run on the worker CPU)
- **ADR-015** — the open-weight mandate and the three readings of "open source"; privacy caveat
- **ADR-016 / ADR-018 / ADR-019** — fine-tuning the judge (rent, don't buy); optional Modal GPU serving
- **ADR-020 (revised 2026-07-17)** — expressive narration (Chatterbox, hosted); Kokoro CPU fallback
