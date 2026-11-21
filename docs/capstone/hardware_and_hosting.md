# Hardware, Hosting & Compute — What Runs Where

**Purpose.** One canonical statement of *where every piece of StoryBuddy actually runs* — so the capstone
manuscript, the PRD, and the ADRs never drift into contradicting each other on hardware, hosting, or the
privacy posture. If another document says something about compute that this file does not support, this file
is the one to trust (it tracks the ADRs; see cross-references at the end).

---

> **Restored and updated 2026-11-21.** Commit `2cb6d2f` (2026-07-28) overwrote this file with the 4-byte text `proc`; it is restored here from `2cb6d2f^` (D-15 of `docs/specs/research-page-refresh.md`). Updated rows are marked *(updated 2026-11-21)* and cite their source. Hosting names in the July text are corrected to Northflank; the rest of sections 1, 3b, 5 and 6 is the July 2026 text. Where a July row disagrees with `backend/app/config.py`, the code wins. The current hosting and training hardware are in §7.

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
  Kokoro narration) are small enough to run on the CPU of the backend worker container (Northflank). No GPU.

This is why the "should we run three models locally?" question dissolves: **in v1 we run essentially none of
the models locally** — not on the child's device and not on a developer GPU in production. Heavy models are
hosted; only tiny CPU classifiers sit on the server. Running models *on the user's machine* is a different
architecture entirely ("on-device," ADR-015 Reading 3), and it is explicitly **Future Work**, not v1.

---

## 2. What runs where (the full map)

| Component | Model / tech | Where it runs | Why there |
|---|---|---|---|
| Frontend web app | Next.js / React | **Vercel** (CDN + SSR) | Static + server-rendered pages; user's browser is the client |
| Backend API + job worker | FastAPI + RQ worker + Redis | **Northflank**, North America region, free tier *(updated 2026-11-21: ADR-031, D-07; was Railway, Singapore)* | Async job architecture (ADR-005); 3 services in one region |
| App data, auth, storage, realtime | Supabase (Postgres, Auth, Storage, Realtime) | **Supabase** (managed) | One service covers DB + auth + signed-URL storage + progress (ADR-006) |
| Story analysis / segmentation / prompts | `mistralai/mistral-small-3.2-24b-instruct` *(updated 2026-11-21: `config.py:35`; was `qwen/qwen3-32b`)* | **OpenRouter** (hosted open weights) | Capable LLM behind one OpenAI-compatible API (ADR-002) |
| Consistency judge (VLM) | prompted `google/gemma-3-27b-it` in the product (`config.py:36`); `Qwen3.5-9B` + QLoRA trained and evaluated for Objective 4, not deployed *(updated 2026-11-21: ADR-061, `research-changelog.md`)* | **OpenRouter**; no Modal or RunPod service is running | The fine-tuned judge is a research result, not a served model |
| Image generation | `fal-ai/qwen-image` (references) and `fal-ai/qwen-image-edit-2511` (pages) *(updated 2026-11-21: `config.py:37-38`)* | **fal.ai** (hosted open weights) | Reference-conditioned edit per scene (ADR-001) |
| **Narration (TTS)** | **Cut, never built** *(updated 2026-11-21: ADR-058 superseded ADR-020)* | none | The Chatterbox and Kokoro rows of the July plan no longer apply |
| Narration fallback | **Cut** *(updated 2026-11-21: ADR-058)* | none | See the row above |
| Input-text moderation | `meta-llama/llama-guard-4-12b` (primary) + `openai/gpt-oss-safeguard-20b` (backstop) *(updated 2026-11-21: `config.py:61,70`)* | **OpenRouter** | Two independent open classifiers (ADR-011) |
| PII redaction | Presidio + spaCy | **Northflank worker CPU** *(updated 2026-11-21)* | Redact before storage/captioning/export (ADR-011) |
| Output-image moderation | `mistralai/mistral-small-3.2-24b-instruct` (primary) + `google/gemma-3-27b-it` (backstop) *(updated 2026-11-21: `config.py:68,73`; ADR-032 dropped the local NSFW ViT)* | **OpenRouter** | Both hosted (ADR-011, ADR-032) |
| Tracing / errors | Langfuse, Sentry *(updated 2026-11-21: ADR-030 replaced LangSmith)* | Managed services | Observability, not models |

**Reading of the map (July 2026 text; as of 2026-11-21 the moderation models are OpenRouter calls, so no model is resident on hardware we operate):** the only models resident on hardware *we* operate were small CPU classifiers on the
Northflank worker. Everything expressive or large (image, text, VLM, expressive TTS) is a hosted API call. The
one optionally self-hosted GPU service — Modal, for the fine-tuned judge (ADR-019) — is **the first thing on
the de-scope ladder** and nothing may hard-depend on it.

---

## 3. Split hardware specification (per adviser's comment)

The original single hardware table conflated two different machines. They are split below.

### 3a. Development Environment Hardware
*(Updated 2026-11-21: the only confirmed development hardware is the RTX 3050 Ti with 4 GB VRAM, `docs/capstone/research_runbook.md` ("RTX 3050 Ti has 4 GB VRAM"). The processor, memory and storage rows below are the July recommendations; the owner has not confirmed them. The registered training did not run on this machine; see §7.)*
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
| (Server side — provisioned by the developer, **not** the school) | Vercel + Northflank + Supabase + fal.ai + OpenRouter + optional Modal | Listed for completeness. The school provisions none of this; it is the hosted backend |

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
| Vercel & Northflank | Cloud hosting for the frontend and backend, respectively |

*Change from the earlier table:* fal.ai is now noted as serving **both image and narration** inference, and
Modal is added as the optional GPU service for the fine-tuned judge.

---

## 5. Local vs hosted vs rented — three phrases that must not be confused

| Term | Meaning in StoryBuddy | Used for |
|---|---|---|
| **Hosted inference** | Open-weight model, run for us over HTTP by a managed provider | Images (fal.ai), narration (fal.ai), text/VLM (OpenRouter) — the v1 default |
| **On our server (CPU)** | Small model resident on the Northflank worker container | Moderation classifiers, Presidio, Kokoro fallback |
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
| Moderation (July plan: Qwen3Guard 0.6B, NSFW ViT, Presidio; now OpenRouter calls plus Presidio) | ≤0.6B | CPU | Yes |

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

## 7. Current hosting and training hardware (2026-11-21)

**Hosting (D-07).** Frontend on Vercel (`docs/TECH_STACK.md`). Backend (FastAPI web, RQ worker, Redis) on Northflank, North America region, free tier (ADR-031; `backend/Procfile` defines the web and worker processes). The owner chose the region for the free tier. The Supabase project region is not recorded in any tracked doc.

**Training hardware.** The registered Objective 4 judge training (three seeds, `obj4-v1`) ran on a rented cloud GPU. The run record is git-ignored (`data/judge/qualification/vast-54113001/registered-training/.../runs/obj4-v1/seed-{0,1,2}/hardware.json` and `run_plan.json`), so its values are copied here. All three seeds report the same hardware:

| Item | Value | Source |
|---|---|---|
| GPU | NVIDIA RTX A6000, 49140 MiB (48 GB class), driver 580.178.04 | `hardware.json`, all three seeds |
| CUDA | 12.8 (`torch 2.11.0+cu128`) | `hardware.json` |
| Libraries | bitsandbytes 0.50.2, Python 3.12.14, Linux 6.8.0-138-generic | `hardware.json` |
| Trainer | LLaMA-Factory v0.9.5, commit `7af909522a951e3ad9f022ea6f88b6755257eaa5` | `run_plan.json` |
| Base model | `Qwen/Qwen3.5-9B`, revision `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | `run_plan.json` |
| Recipe | QLoRA, 4-bit bnb, LoRA rank 16, alpha 32, target all, cutoff length 2048, template `qwen3_5_nothink` | `backend/finetune/train_qlora.yaml` |

The rented-GPU provider is named Vast.ai in the manuscript table and the record folder is `vast-54113001`; the record itself does not name the provider (inferred). The CyberLab PC plan in §3a and §5c was not what the registered runs used: the run records name only the A6000 (inferred from their absence of any other host).

## Cross-references

- **ADR-001** — image model on fal.ai (hosted open weights)
- **ADR-002** — text/VLM on OpenRouter
- **ADR-005 / ADR-009 / ADR-031** — async architecture; Vercel + Railway hosting (ADR-009, superseded by ADR-031: Northflank); worker RAM budget
- **ADR-011** — moderation stack (which classifiers run on the worker CPU)
- **ADR-015** — the open-weight mandate and the three readings of "open source"; privacy caveat
- **ADR-016 / ADR-018 / ADR-019** — fine-tuning the judge (rent, don't buy); optional Modal GPU serving
- **ADR-020 (revised 2026-07-17)** — expressive narration (Chatterbox, hosted); Kokoro CPU fallback
