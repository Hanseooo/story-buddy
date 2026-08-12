# StoryBuddy — Tech Stack Reference

> Derived from ADRs.md — if this doc and an ADR disagree, the ADR wins.

**Last generated:** 2026-07-28

**Purpose.** One page to answer "what model / service / library / API am I supposed to use here, and
where is it configured?" without re-reading 1500 lines of ADRs. If you're about to hardcode a model ID
or an SDK call at a call site, stop and read §5 first.

---

## 1. At-a-glance: every model

| Role | Exact model ID | License | Where it runs | Config setting | ADR | Phase |
|---|---|---|---|---|---|---|
| Text pipeline (analyze/segment/prompts) | `mistralai/mistral-small-3.2-24b-instruct` | Apache-2.0 | OpenRouter | `settings.text_model` | ADR-002 (amended 2026-08-11, 2026-08-12) | Phase 1 — model unchanged by the 08-12 amendment; it failed strict-schema fidelity on **Parasail** (row `558afb6d`), so `providers.TEXT_PROVIDERS` pins the route and `_chat` re-asks once. |
| ~~Text pipeline~~ (superseded 2026-08-11) | ~~`qwen/qwen3-32b`~~ | Apache-2.0 | OpenRouter | — | ADR-002 | Passed Probe 3 (2026-07-29) and still failed in production: emitted prose under `response_format`, prod job `af068baf`. `require_parameters: true` selects providers that *accept* structured output, not ones that *honour* it. |
| Consistency judge (prompted) | `google/gemma-3-27b-it` | Gemma license (not OSI) | OpenRouter | `settings.vlm_judge_model` | ADR-002, ADR-004 | Phase 1 |
| Consistency judge (fine-tuned, replaces prompted if it ships) | `Qwen2.5-VL-7B-Instruct` + QLoRA adapter | Apache-2.0 | Modal (vLLM, scale-to-zero), reached via `settings.judge_base_url` | `settings.judge_base_url` / `settings.judge_api_key` | ADR-018, ADR-019 | Phase 2.5 |
| Canonical character reference (text→image) | `fal-ai/qwen-image` | Apache-2.0 | fal.ai | `settings.fal_image_model` | ADR-001, ADR-007 | Phase 1 |
| Scene generation (reference-conditioned edit) | `fal-ai/qwen-image-edit-2511` | Apache-2.0 | fal.ai | `settings.fal_image_edit_model` | ADR-001 | Phase 1 |
| Input-text moderation (primary) | `meta-llama/llama-guard-4-12b` 0.6B | Apache-2.0 | OpenRouter | not yet in `config.py` — Phase-2 `moderation-stack` spec defines the shape | ADR-011 (revised 2026-07-21c) | Phase 2 |
| Input-text moderation (backstop) | `openai/gpt-oss-safeguard-20b` | Apache-2.0 (open weights, not the OpenAI API) | OpenRouter | `settings.moderation_backstop_model` (currently `None` — see §8) | ADR-011 | Phase 2 |
| Input-text moderation (config default, demoted) | `meta-llama/llama-guard-4-12b` | Meta Community License (not OSI) | OpenRouter | `settings.moderation_model` | ADR-011 | placeholder only — see §8 |
| Output-image NSFW gate (primary image guard) | `mistralai/mistral-small-3.2-24b-instruct` | Apache-2.0 | OpenRouter | `settings.moderation_primary_image_model` | ADR-011, ADR-032, ADR-002 (amended 2026-08-11) | Phase 2 |
| ~~Output-image NSFW gate~~ (superseded 2026-08-11) | ~~`qwen/qwen3-vl-32b-instruct`~~ | Apache-2.0 | OpenRouter | — | ADR-011, ADR-032 | Served by Alibaba Cloud it emitted `is_safe` before `safety_reasoning`; `providers._assert_field_order` rejects that under ADR-004 reason-then-score and hard-failed the job at `char_ref_mod`. Same class as the `text_model` failure one row up — the *provider*, not the model, decides structured-output fidelity. |
| Output-image safety rubric (violence/gore) | `google/gemma-3-27b-it` (separate call, separate concern from the judge) | Gemma license | OpenRouter | reuses `settings.vlm_judge_model`'s model id via a distinct prompt/call — **never the fine-tuned judge** | ADR-011, ADR-004 amendment (b) | Phase 2 |
| Narration (primary) | `Chatterbox` (Resemble AI) | MIT | fal.ai | not yet in `config.py` | ADR-020 | Phase 2 |
| Narration (CPU fallback) | `Kokoro-82M` | Apache-2.0 | OpenRouter | not yet in `config.py` | ADR-020 | Phase 2 |
| PII redaction | Presidio + spaCy | MIT / MIT | OpenRouter | not yet in `config.py` | ADR-011 | Phase 2 |

**Not a model, but a required call param:** every OpenRouter structured-output call must send
`provider.require_parameters: true` in `extra_body` (`backend/providers.py:54`) — omitting it lets
OpenRouter silently downgrade `json_schema` to loose JSON mode (ADR-002). Sent to OpenRouter only;
self-hosted vLLM (the fine-tuned judge, post-Phase 2.5) rejects the field.

---

## 2. Services & infrastructure

| Service | For | Phase | Alternative considered |
|---|---|---|---|
| **Vercel** | Frontend hosting (Next.js SSR + static) | Phase 0 | Render, Fly.io (fine); DO App Platform (not preferred) — ADR-009 |
| **Northflank** (Singapore region) | Backend: FastAPI web + RQ worker + Redis, 3 services | Phase 0 | Render, Fly.io, DO droplet — ADR-031 |
| **Supabase — Postgres** | App data + LangGraph checkpoints (`langgraph-checkpoint-postgres`). ⚠️ **Reached on the direct connection, port 5432 — not the transaction pooler on 6543** (ADR-033) | Phase 0 | Roll-your-own Postgres — more ops, no gain — ADR-006 |
| **Supabase — Auth** | Classroom-scoped accounts: teacher/BEED-student issuer, child/student rows | Phase 0 (built), Phase 2 (real RLS) | Firebase — less Postgres/RLS-native — ADR-006. **Clerk** — rejected ADR-027: its self-serve/email product is what ADR-017 forbids, and it splits the JWT issuer from the Postgres enforcing RLS |
| **Supabase — Storage** | Generated images + audio via signed URLs; no public buckets. **PDFs are generated on demand, not stored** (ADR-027) | Phase 0 | **Cloudflare R2 / S3** — rejected ADR-027: compression removes the need, and neither can mint signed URLs client-side, so both force asset authz out of RLS into app code |
| **Supabase — Realtime** | Frontend watches job-row progress | Phase 0 | Websockets — more work, same result — ADR-005 |
| **Redis** | RQ broker for the async job queue | Phase 0 | Postgres-backed queue (viable simplification, revisit if Redis feels like overhead) — ADR-005 |
| **Modal** | Scale-to-zero GPU container serving the fine-tuned judge behind vLLM (OpenAI-compatible) | Phase 2.5 / Phase 3, **first item on the de-scope ladder** | RunPod Serverless, Baseten (drop-in equivalents); HF Inference Endpoints (thinner VLM LoRA support) — ADR-019 |
| **LangSmith** | Pipeline tracing — turns on via env vars (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`), zero-code LangGraph wiring | Phase 0 (from first commit) | Langfuse — open-source/self-hostable but more ops for a solo build — ADR-014 |
| **Sentry** | Error tracking, frontend + backend | Phase 0 | — |
| **fal.ai** | Hosted inference: image generation (both models) + narration (Chatterbox) | Phase 0/1 (images), Phase 2 (narration) | Novita, Replicate — named drop-in alternates for images (ADR-001) |
| **OpenRouter** | Hosted inference: text pipeline, prompted judge, moderation backstop | Phase 0/1 | — (aggregator chosen specifically so a model swap is a config change, ADR-002) |

---

## 3. Libraries

### Backend (`backend/pyproject.toml`) — uv-managed, Python ≥3.12

| Package | Pinned floor | Role |
|---|---|---|
| `fastapi` | >=0.115 | Web framework |
| `uvicorn[standard]` | >=0.32 | ASGI server |
| `pydantic` | >=2.9 | Contract validation (Story Memory, structured LLM output) |
| `pydantic-settings` | >=2.6 | `Settings` (env-overridable config) |
| `langgraph` | >=0.2.45 | Deterministic pipeline state machine (ADR-003) |
| `langgraph-checkpoint-postgres` | >=2.0.1 | Per-super-step checkpointing to Supabase Postgres (ADR-005, ADR-024). `PostgresSaver.from_conn_string` hardcodes `prepare_threshold=0` — "prepare every query", not "no prepared statements" — which is why `SUPABASE_DB_URL` must name **5432**, not the 6543 pooler (ADR-033) |
| `psycopg[binary]` | >=3.2 | Postgres driver |
| `openai` | >=1.99 | OpenAI-compatible client — points at OpenRouter *or* vLLM/Modal (ADR-019); not an OpenAI-model dependency |
| `fal-client` | >=0.7 | fal.ai SDK (images, narration) |
| `httpx` | >=0.27 | Direct HTTP (image download from fal result URL) |
| `supabase` | >=2.9.1 | Supabase Python client |
| `redis` | >=5.2 | RQ broker client |
| `rq` | >=2.0 | Job queue |
| `sentry-sdk[fastapi]` | >=2.17 | Error tracking |
| **dev:** `pytest` | >=8.3 | Test runner |
| **dev:** `pytest-mock` | >=3.14 | Mocking (every `providers.py` call is mocked in deterministic tests) |
| **dev:** `ruff` | >=0.8 | Lint only — `ruff format` deliberately not adopted (see `pyproject.toml` comment: an 88-col reformat would rewrap the whole repo in one feature diff) |

**Conditionally required, not yet added:** `pillow` — needed only if fal turns out not to accept an
`output_format` arg (ADR-027). Confirmed absent from `backend/uv.lock` as of this doc's generation. Do not add
it speculatively; run the fal check first.

**Tooling lock:** `uv` only. Forbidden: bare `pip install`, `poetry`, `pipenv`. Always `uv run <cmd>` from
`backend/` (pinned to `backend/.venv`).

### Frontend (`frontend/package.json`) — pnpm-managed

| Package | Pinned version | Role |
|---|---|---|
| `next` | 16.2.10 | App Router, SSR |
| `react` / `react-dom` | 19.2.4 | UI |
| `@supabase/supabase-js` | ^2.110.1 | Supabase client (Realtime job-progress watch, Storage signed URLs) |
| `@sentry/nextjs` | ^10.64.0 | Error tracking |
| `tailwindcss` / `@tailwindcss/postcss` | ^4 | Styling |
| **dev:** `vitest` | ^4.1.10 | Unit tests (`pnpm test`) |
| **dev:** `@testing-library/react`, `@testing-library/jest-dom` | ^16.3.2 / ^6.9.1 | Component testing |
| **dev:** `jsdom` | ^29.1.1 | Vitest DOM environment |
| **dev:** `eslint` / `eslint-config-next` | ^9 / 16.2.10 | Lint (`pnpm lint`) |
| **dev:** `typescript` | ^5 | Types |

**Tooling lock:** `pnpm` only. Forbidden: npm, yarn, bun.

**Note:** frontend `AGENTS.md` flags this Next.js version as having breaking changes vs. training-data
conventions — read `node_modules/next/dist/docs/` before writing Next.js code.

---

## 4. The image pipeline in detail

**Two models, one family, two separate env vars — this is the thing developers keep re-deriving, so it's
spelled out fully here (ADR-001, consequence recorded 2026-07-28).**

1. **`fal-ai/qwen-image`** (base, text-to-image) → `settings.fal_image_model` → called via
   `providers.text_to_image(prompt, seed=None)` (`backend/providers.py:88`). Generates the **canonical
   character reference**, once per character, up to 2 canonical refs in v1 (ADR-004). This is where **art
   style is decided** — the reference is generated *in* the chosen style preset (ADR-007, ADR-022), and
   because it's the thing every scene conditions on, style propagates for free.

2. **`fal-ai/qwen-image-edit-2511`** (editor, reference-conditioned) → `settings.fal_image_edit_model` →
   called via `providers.edit_image(prompt, image_urls, seed=None)` (`backend/providers.py:93`). Generates
   **every scene**, conditioned on 1–3 reference images. This is where **identity is preserved** — Qwen-
   Image-Edit is an editor: it cannot start a book, only continue one.

**How the output is stored (ADR-027):** scenes are persisted as **WebP q≈82**, canonical references as **PNG**.
The asymmetry is deliberate — references are the conditioning input every scene depends on and there are at most
2 per book (ADR-004), so recompression is not risked on the identity mechanism to save ~3 MB. Preferred encoding
route is an `output_format` key in the args dict `_run_fal` already forwards (`providers.py:88-95`); Pillow on
the worker is the fallback if fal does not expose it (see §8).

**Why the seam matters:** because style rides the reference and identity rides the editor, the two
concerns are **independently swappable**. An aesthetic problem ("I want more artistic flair") is fixed by
swapping `fal_image_model` alone — no touch to the consistency mechanism the Phase-0.5 kill criterion
tests. A consistency problem escalates the *editor* (see ladder below), leaving style untouched. This is
the same shape as the widely-recommended "hero image in a beautiful model, then edit for consistency"
hybrid — StoryBuddy's step 1 just uses an open-weight model instead of Midjourney/FLUX.

**Fallback ladder** (ADR-001, re-ordered 2026-07-28, license-clean before non-commercial — before any
Phase-0.5 probe ran). If Probe 1 fails on `fal_image_edit_model`, escalate in this order:

| Rung | Model | License | Note |
|---|---|---|---|
| 1 | **OmniGen2** | Open (verify per repo) | Leads OmniContext 7.95 (subject-consistency benchmark), ahead of Qwen-Image-Edit-2509 |
| 2 | **FLUX.2 [klein] 4B** | Apache-2.0 | Faster/cheaper, fits 12–16 GB if self-hosting forced; unproven on non-human identity |
| 3 | **HiDream-O1-Image** | MIT | Highest open-weight Elo (~1189); reference-conditioning story unproven |
| 4 | **FLUX.1 Kontext [dev]** | Non-commercial | Last rung — constrains what the artifact may later become |

**Z-Image** (Apache-2.0, 6B) is explicitly **not on the ladder** — it's the designated substrate only if
ADR-015's mandate is later ruled to mean *self-hosted*, not *hosted*.

⚠️ **Unverified (ADR-001):** whether fal.ai routes OmniGen2, HiDream-O1, or Z-Image at all. If it does,
escalating a rung is a `fal_image_edit_model` env change; if not, escalation becomes a `providers.py`
provider change — materially larger.

---

## 5. How to swap anything

The rule (`AGENTS.md`, `config.py:16`): **a model swap is an env change in `config.py`; a provider swap is
a `backend/providers.py` change. Never hardcode either at a call site.**

**Worked example — model swap.** Escalating the image-edit model to OmniGen2 after a Probe-1 failure
(assuming fal.ai routes it):
```
# .env (or Northflank env vars) — no code change
FAL_IMAGE_EDIT_MODEL=omnigen2/...actual-fal-endpoint-id
```
`providers.edit_image()` reads `settings.fal_image_edit_model` — nothing in `pipeline/` or `providers.py`
changes.

**Worked example — provider swap.** Moving the judge off OpenRouter to the self-hosted Modal/vLLM endpoint
after Phase 2.5 (ADR-019):
```
# .env
JUDGE_BASE_URL=https://<modal-endpoint>/v1
JUDGE_API_KEY=<modal-key>
```
This is *also* just a config change here, because `providers.judge()` already takes `base_url`/`api_key`
as parameters and vLLM speaks the same OpenAI-compatible protocol — the one code concession is that
`provider.require_parameters` is sent only when `base_url == OPENROUTER_BASE_URL` (`providers.py:54`),
since vLLM rejects the unknown field. A genuine *new* provider (e.g. leaving fal.ai entirely for image
generation) would instead require editing `_run_fal` / adding a new client in `providers.py` — that is
the one-file, not one-env-var, case.

---

## 6. What is explicitly forbidden and why

- **Closed/proprietary models of any kind** — not just as primaries, as backstops or accessories either
  (ADR-015, hardened 2026-07-10b). This is why `omni-moderation-latest` and ElevenLabs were removed from
  the stack entirely, not merely demoted.
- **FLUX.1-dev-derived adapters** — InstantCharacter, DreamO, UNO, ACE++, InstantID, PuLID. Their wrapper
  licenses look permissive but sit on a **non-commercial FLUX.1-dev base** whose terms they inherit; the
  wrapper license does not override the base (ADR-001 Alternatives). InstantID and PuLID additionally
  depend on InsightFace's non-commercial `antelopev2` and are face-embedding based — their own
  documentation calls animal/fantastical characters unstable, which is exactly the case this product
  requires to work.
- **Fine-tuning anything except the consistency judge** (ADR-016, superseded by ADR-018). Identity is
  blocked by *latency*, not cost — a child invents a character at write-time, so there's no dataset and no
  40-minute training budget inside a 1–3 minute flow. Style is already solved by ADR-007's fixed
  reference-carried constant. The judge is fine-tuned per `docs/specs/judge-finetune.md` — the one
  sanctioned LoRA.
- **Per-character LoRAs / DreamBooth at runtime** — rejected permanently on *latency*, not cost (ADR-016).
  A LoRA run is cheap (~30–60 min on a rented GPU) but there's no 40-minute budget inside the storybook
  generation flow.
- **Any model on the child-safety path being the fine-tuned judge** — ADR-004 amendment (b): the
  fine-tuned model is a quality signal with a best-of fallback; safety is a gate with no fallback. The two
  calls are never merged even though they currently share a base model (Gemma) by coincidence.

---

## 7. Costs

| Item | Cost | Source |
|---|---|---|
| Image generation | ~$0.02–0.035/image | ADR-001 |
| Per book (images) | ~$0.30–0.65/book | ADR-001 |
| Narration | ~cents/book (metered fal.ai Chatterbox, per page) | ADR-020 |
| Whole stack, monthly | ~$60–110/month at 200 books/month, dominated by image generation | ADR-015, PRD §15 |
| Judge fine-tune (one-time) | ~$5–15, a few hours on a rented RTX 4090 (~$0.45–0.49/hr) or A100 (~$1.50/hr) | ADR-016, ADR-018 |
| Judge serving (Modal, if kept warm) | ~$1/hr to keep one container warm during study sessions (cold start ~30–90s otherwise) | ADR-019 |
| Judge inference (steady state, if fine-tune ships) | ~2,000 calls/month × ~3s ≈ 100 GPU-minutes — cheaper than 2,000 Gemma-27B API calls | ADR-019 |
| Moderation backstop (`gpt-oss-safeguard-20b`) | One call per story (not per scene) — cost is noise | ADR-011 |
| Style presets | $0 marginal (presets are strings) | ADR-022 |
| Storage + egress | $0 — Supabase free tier (1 GB / 5 GB per month) is sufficient **only because scenes are WebP**; raw PNG breaches it mid-pilot at ~1.35 GB | ADR-027 |

---

## 8. Known gaps / unverified

Be honest — these are open, not silently resolved:

- **Phase 0.5 probes: partly run (2026-07-29).** Probe 1 (non-human identity) ran three times — absolute
  gate met at 80%, separation gate missed at +25 vs ≥30; Qwen-Image-Edit stays primary per the ADR-001
  amendment. Probe 3 (structured output) **passed** both arms. **Probe 2 (seed determinism) and probe 4
  (Filipino/Taglish moderation) are still unexecuted**, so §4's fallback ladder below rung 1 remains
  unverified on fal and the moderation gate is untested in either direction. See
  `docs/product/PHASE_05_RESULTS.md`.
- ~~**`backend/.env` does not exist**~~ — resolved; `backend/.env` exists and `Settings` instantiates
  (verified 2026-07-29 by resolving `fal_image_edit_model`). Only `.env.example` is in git, by design.
- ~~**`settings.moderation_backstop_model` is `None`**~~ — resolved 2026-08-02 by `moderation-stack`.
  `config.py` now carries three moderation settings, all set: `moderation_primary_model =
  "meta-llama/llama-guard-4-12b"` (an OpenRouter model, per ADR-032), `moderation_backstop_model = "openai/gpt-oss-safeguard-20b"` (ADR-011c), and
  `moderation_backstop_image_model = "google/gemma-3-27b-it"` (a separate field from `vlm_judge_model` so
  the safety rubric and the consistency judge can diverge).
- **RLS is not actually restrictive today.** There are exactly **two** policy surfaces:
  `supabase/migrations/0001_jobs_table.sql:18-21` on `jobs` (`for select to anon using (true)`) and
  `0004_jobs_pages.sql:19-22` on `storage.objects` (scoped only to the bucket) — RLS is *enabled* but
  nothing is *restricted*. Scoping today is a client-side `.eq('id', job_id)` convention (the UUID is the
  capability link), and no classroom/profile columns exist yet to scope by. Both migrations carry a
  `ponytail:` comment flagging that Phase 2's `auth-and-classroom` migration must drop both and replace
  them in one change (`kid-flow-book-persistence` constraint 4); no later spec may add a third surface.
- **Whether fal.ai actually routes OmniGen2, HiDream-O1, or Z-Image is unverified** (ADR-001). This gates
  whether escalating the fallback ladder is a one-env-var change or a `providers.py` provider change.
- **Whether fal accepts an `output_format` arg is unverified** (ADR-027). This gates whether WebP encoding is a
  one-key change to the args dict or a new Pillow dependency plus OpenRouter. One API-doc check, not a probe.
- **The 8–10× WebP ratio is an estimate, not a measurement.** ADR-027's storage math rests on ~1.2–2 MB PNG vs
  ~120–200 KB WebP for 1024×1024 illustrated art. Phase 0.5 is where real encoded byte sizes get recorded — the
  probes already generate the images, so this costs one `os.path.getsize` call, not a new experiment.
- **`generate_scene.py` still writes raw PNG.** ADR-027 is accepted but unbuilt: `backend/pipeline/generate_scene.py`
  uploads fal's bytes unmodified (now to `{story_id}/{scene_id}.png` — the `scene-1.png` collision was fixed
  by the `image-generator` spec, 2026-07-31). Both the path template and PNG upload change when ADR-027 is
  implemented. Until then the free-tier headroom in §7 is a plan, not a fact.
- **Supabase project region is unconfirmed against Northflank's Singapore pin** (ADR-031). Relevant to latency and
  to the Philippine Data Privacy Act framing in `docs/capstone/ethics_and_safety.md`, and **not changeable after
  project creation** without a migration. Not decided by ADR-027 — it sits with ADR-006.
- **ADR-015's "hosted inference counts as open-weight" reading is an unconfirmed operating assumption, not
  a supervisor ruling.** ADR-015 states explicitly: the project owner (not the supervisor) judged that
  hosted inference of open weights satisfies the mandate, and flags it for explicit confirmation before
  Phase 2 hardening. If the mandate turns out to mean *self-hosted*, this doc's entire hosting model
  (fal.ai, OpenRouter) changes to a GPU service StoryBuddy operates directly — the pipeline code itself
  would not change, because every vendor call is already isolated in `providers.py`.
- **CyberLab training GPU VRAM is unconfirmed.** `docs/capstone/hardware_and_hosting.md` §3a: the tentative
  spec "RTX 4060, 32 GB" almost certainly means an RTX 4060 GPU (8 GB VRAM, 16 GB on a 4060 Ti) + 32 GB
  *system* RAM — not 32 GB VRAM. QLoRA on a 7B VLM with two-image inputs needs ~16 GB+ VRAM, so an 8 GB
  card likely OOMs. The rented RTX 4090/A100 fallback (~$5–15, ADR-018) exists precisely for this case —
  verify the exact GPU model and VRAM before committing the training run.
- ~~**The output-image safety gate is entirely unbuilt.**~~ — resolved 2026-08-02 by `moderation-stack`:
  `input_gate` is a real implementation (meta-llama/llama-guard-4-12b OpenRouter API + Presidio PII redaction,
  concurrent, with an OpenRouter backstop), `char_ref_mod` gates every canonical reference before the
  reveal, and `output_mod` gates every output scene (qwen/qwen3-vl-32b-instruct + Gemma safety rubric, one
  soften-and-retry). `moderation_router` and `route_after_output_mod` enforce the ADR-011 ordering in
  `graph.py`. §1's moderation rows now describe shipped code, not a target. **Still open:** the worker RAM
  budget with Presidio+spaCy, the ViT and the CPU text gate all resident (`moderation-stack` §8).
- **Both moderation gates (input text, output image) are unverified in Filipino and Taglish** until the
  Phase 0.5 moderation probe runs — a release gate for Phase 2, not a curiosity (ADR-011).
