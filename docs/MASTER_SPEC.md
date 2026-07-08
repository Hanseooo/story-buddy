# StoryBuddy — Master Spec (Engineering Constitution)

**Status:** living document · **Scope:** how the system connects and the rules for building it
**Companions:** enforced rules in `/CLAUDE.md` · product/architecture rationale in `docs/product/`

---

## 0. How to use this document

This is the **engineering entry point**. It does not re-decide product or architecture — those
live in `docs/product/` (PRD_v2, ADRs, ROADMAP) and are the source of truth for *why*. This doc
owns *how the pieces connect* and the engineering rules that keep an AI-assisted build coherent.

| You want… | Go to |
|---|---|
| The hard rules you must not break | `/CLAUDE.md` |
| Why a decision was made | `docs/product/ADRs.md` |
| What the product is / user flow | `docs/product/PRD_v2.md` |
| Build order & phase exit criteria | `docs/product/ROADMAP.md` |
| How modules connect / where code lives | §2 below (System Map) |
| The inter-module data contract | §3 below (Story Memory) |
| What to test and how | §4, §6 |
| Concerns every feature must honor | §5 (Cross-cutting registry) |
| How to write/spin a feature spec | §7 + `docs/specs/TEMPLATE.md` |
| Day-to-day build workflow (which tool, what size) | `docs/WORKFLOW.md` |

Feature specs are **derived from this doc**: each MVP module (PRD §5.1) gets one short spec in
`docs/specs/`, written just-in-time before it's built (roadmap order), referencing §3 and §5.

---

## 1. Repository layout

```
story-buddy/
  CLAUDE.md              # enforced AI operating contract (read every session)
  README.md
  docs/
    MASTER_SPEC.md       # this file
    product/             # PRD_v2, ADRs, ROADMAP — source of truth, do not duplicate
    specs/               # per-feature specs + TEMPLATE.md
  frontend/              # Next.js app — own package.json (vitest unit, Playwright e2e)
  backend/               # FastAPI web + RQ worker — own pyproject (pytest)
    pipeline/            # LangGraph nodes, one file per module
    contracts/           # Pydantic Story Memory schema = the frozen inter-module contract
```

**Frontend and backend are independent projects** (different languages; no shared monorepo build
tooling — that would be speculative for a solo build). Their only contract is the HTTP API and the
Story Memory shape. New ADRs **append** to `docs/product/ADRs.md` — there is no separate
`decisions/` folder.

### Folder rules for AI agents
- New pipeline module → a new file in `backend/pipeline/`, named for its single concern.
- Anything crossing the module boundary goes **through** `backend/contracts/`, never ad-hoc.
- Docs: product rationale → `docs/product/`; engineering how → here; per-feature → `docs/specs/`.
- Don't scatter READMEs; one per top-level project (`frontend/`, `backend/`) at most.

---

## 2. System Map — how the pieces connect

**Three deployed services** (ADR-005, ADR-009), not one:

```
[Next.js / Vercel]  --POST /storybooks-->  [FastAPI web / Railway]
        ^                                          |
        |                                    creates job row
   Supabase Realtime                               v
   (subscribes to job row) <----updates----  [Supabase Postgres]
        ^                                          ^
        |                                    checkpoint / status
        |                                          |
        +----------- final images/PDF -----  [RQ worker / Railway] --runs--> LangGraph pipeline
                     (Supabase Storage)              ^
                                                  [Redis broker]
```

**Request never runs the pipeline.** `POST /storybooks` writes a job row and returns `job_id`
immediately. The **RQ worker** pulls the job and runs the LangGraph graph, **checkpointing to
Postgres after each scene** (`langgraph-checkpoint-postgres`). The frontend watches the job row
via **Supabase Realtime**. A stall at scene N resumes from N — never re-rolls 1…N-1 (ADR-005).

### The LangGraph pipeline (deterministic state machine — ADR-003)

Explicit nodes; conditional edges **only** at moderation and consistency branch points.
Each node ↔ one module ↔ one file in `backend/pipeline/` ↔ one feature spec in `docs/specs/`.

```
input_gate ──► analyze ──► segment ──► char_bible ──► [char-ref moderation]
   (length,                                                  │ pass
    PII,                                                     ▼
    text mod)                                          generate_scene ──► consistency_check
                                                            ▲                    │
                                                            │ fail: 1 targeted   │ pass
                                                            └──── regenerate ◄────┤
                                                                 (best-of)        │ (each scene)
                                                                                  ▼
                                                          [output image moderation] ──► compose ──► export
```

| Node / module | Reads (Story Memory) | Writes | ADR / PRD |
|---|---|---|---|
| `input_gate` | `input.raw_text` | `input.redacted_text`, `word_count`, `truncated`, `moderation` | ADR-011,012 / §5,§13 |
| `analyze` | `input.redacted_text` | `characters[]`, `locations[]`, `objects[]`, `timeline[]` | §8 |
| `segment` | analysis + timeline | `scenes[].text_excerpt`, `caption` | ADR-012 / §5,§8 |
| `char_bible` | `characters[]` | `characters[].canonical_ref_image`, `ref_moderation_status` | ADR-001,007 |
| `generate_scene` | scene + char refs + `style` | `scenes[].attempts[].image_ref` | ADR-001,010 |
| `consistency_check` | ref + attempt image | `scenes[].attempts[].vlm_verdict`, `failure_reasons`, `passed` | ADR-004 |
| `regenerate` | `failure_reasons` | corrected `prompt` → new attempt; `final_image_ref` (best-of) | ADR-010 |
| `output moderation` | each `final_image_ref` | `scenes[].moderation_status` | ADR-011 |
| `compose` / `export` | passed scenes + captions | storybook + PDF in Storage | ADR-013 |

**The style constant is config, not a node** (ADR-007): a fixed prompt fragment + optional
style-anchor image, authored once. Identity *and* style both ride the canonical reference.

---

## 3. The frozen contract — Story Memory

The Pydantic model in `backend/contracts/` (shape sketched in PRD §19) is **the** interface
between every module. It is authoritative and versioned. Rules:

- Every LLM call uses Gemini structured output → validated into this schema (never raw dict).
- A module's spec (§7) declares exactly which fields it **reads** and **writes** — its contract slice.
- Schema change = contract change: update schema + affected specs + every consumer, one change.
- `eval.condition` (`pipeline_on | pipeline_off`) and `eval.seed` drive the ablation (§6, ADR-008).

Freeze the schema's *shape* before Phase 1 (ROADMAP dependency map). Field-level detail is
finalized in the Story Memory feature spec, which is the first spec written.

---

## 4. Tech stack (consolidated)

Product/architecture choices are in the ADRs; this is the working reference, **including testing**.

| Layer | Choice | Notes / ADR |
|---|---|---|
| Frontend | Next.js (React) + Tailwind + shadcn/ui (parent) + hand-built cartoon-pop (kid) + Motion + Lottie | Vercel, SSR landing. §9,§12 |
| Backend web | FastAPI | Railway (Singapore). ADR-009 |
| Worker / queue | RQ worker + Redis broker | Separate service. ADR-005 |
| Pipeline engine | LangGraph (deterministic) + `langgraph-checkpoint-postgres` | ADR-003,005 |
| LLM / VLM | Gemini (Flash tier for nodes; Gemini vision for judge) | ADR-002,004 |
| Image model | Nano Banana (Gemini 2.5 Flash Image / Nano Banana 2 Lite) | ADR-001 |
| Data / auth / storage / realtime | Supabase (Postgres + Auth + Storage + Realtime + RLS) | ADR-006 |
| Structured extraction | Gemini `response_schema` + Pydantic | §12, §3 |
| Moderation | OpenAI moderation (text) + Presidio (PII) + Vision SafeSearch/Gemini safety (image) | ADR-011 |
| Observability | LangSmith **or** Langfuse (tracing) + Sentry (errors) | §16 |
| Rate limiting | `slowapi` + per-profile daily cap + cost circuit-breaker | §14,§15 |
| Export | HTML template → PDF (Playwright **or** WeasyPrint — **open, ADR-013**) | §8 |
| **Testing — FE unit** | **vitest** | mock model calls; component + logic |
| **Testing — BE unit** | **pytest** | mock Gemini/Nano Banana; node logic, contracts, RLS, routing |
| **Testing — e2e** | **Playwright + Playwright CLI** | happy path, auth/RLS isolation, processing→slideshow, export |
| **Eval harness** | offline scripts + tracing exports | real models, story corpus; **not CI** (§6) |

### Frontend rendering strategy
Next.js is chosen for **one** load-bearing reason: the parent-facing **landing page is SSR** (SEO —
parents discover the product). Everything else is DX. Therefore:

- **Landing page:** server-rendered (SEO, fast first paint).
- **Authenticated app** (kid flow, parent dashboard): **client components + direct Supabase reads**
  (RLS-enforced), so navigation is instant/SPA-style with no server round-trip per page. Do **not**
  server-render these — that reintroduces per-navigation latency for zero SEO benefit.
- **CRUD:** the frontend does **not** host a backend. Light reads/writes → Supabase client directly
  (RLS); the one heavy write (make a storybook) → FastAPI `POST /storybooks` (ADR-005). Next.js API
  routes / server actions stay minimal — no CRUD API duplicated here.
- The "slow to navigate" feeling in `next dev` is on-demand route compilation; production builds
  don't do it. Use `loading.tsx` skeletons and default `<Link>` prefetch.

---

## 5. Cross-cutting concerns registry

Concerns that touch many modules. **Every feature spec ticks the ones it affects** (a checklist in
`TEMPLATE.md`), so nothing is forgotten per-feature. Reference by number, e.g. "honors CC-1, CC-3".

| # | Concern | What a spec must show | ADR/§ |
|---|---|---|---|
| CC-1 | **Moderation ordering** | input text → char-ref → output image; no image reaches a kid unmoderated | ADR-011 / §13 |
| CC-2 | **PII redaction** | Presidio before storage/caption/export; redacted text is what's persisted | ADR-011 / §14 |
| CC-3 | **Cost control** | counts toward per-book ceiling + circuit-breaker; per-profile daily cap | §15 |
| CC-4 | **Security (RLS + signed URLs)** | DB-layer isolation; no public assets | ADR-006 / §14 |
| CC-5 | **Observability** | emits traces/metrics (gen time, regen count, cost, VLM score) | §16 |
| CC-6 | **Accessibility** | read-aloud (TTS) captions; large targets; minimal text; STT input where relevant | §17 |
| CC-7 | **Reproducibility** | honors `eval.seed`; deterministic where the model allows | §20, ADR-010 |
| CC-8 | **Kid vs parent design language** | cartoon-pop (kid flow) vs calmer/denser (parent) | §9 |
| CC-9 | **Failure states = success states** | moderation/failure screens get equal design care; kid-legible | §9,§13 |
| CC-10 | **Checkpointing / resumability** | node is safe to resume mid-run; no re-roll of completed scenes | ADR-005 |

---

## 6. Testing strategy (two tiers — the bright line)

Non-negotiable split. See `/CLAUDE.md` §3.

**Tier A — Deterministic tests (CI, every change, must stay green).**
Everything with one right answer, **with Gemini/Nano Banana mocked**:
- Contract validation (Story Memory Pydantic round-trips, schema rejects bad shapes).
- LangGraph routing (moderation pass/fail and consistency pass/fail take the right edges).
- Job lifecycle & checkpoint/resume (stall at N resumes at N).
- Moderation ordering; PII redaction; truncate-at-scene-boundary; N=3 off-ramp; cost circuit-breaker.
- RLS isolation (a parent cannot read another's data); signed-URL access.
- e2e happy path + processing→slideshow via Realtime + PDF export (Playwright).
- **Never assert on generated content.** "Is the character consistent?" is Tier B.

**Tier B — Eval harness (offline, real models, on demand — never CI).**
The only place fuzzy quality is measured, on the real/realistic story corpus (PRD §10):
- Scene-selection quality (RQ1), consistency (RQ2 ablation pipeline-ON vs -OFF), acceptability (RQ3),
  under-length grace (RQ4), VLM–human agreement.
- **Is the same instrumentation as the Phase 3 study** (LangSmith/Langfuse) — build once, use for
  both dev feedback and research data. Costs money and is non-deterministic; that's why it's not CI.

---

## 7. Feature spec lifecycle

Each MVP module (PRD §5.1) becomes one spec in `docs/specs/`, from `TEMPLATE.md`.

**Lifecycle:** derive from this doc → fill contract slice (§3) + cross-cutting checklist (§5) →
human approves → implement → deterministic tests green (§6 Tier A) → eval checks if fuzzy (§6 Tier B) →
mark done. Behavior change later → update the spec in the same change (CLAUDE.md §4).

**Index (write just-in-time, roadmap order):**

| Phase | Specs to write |
|---|---|
| 1 (core) | `story-memory-contract`, `story-analyzer`, `scene-segmentation`, `character-bible`, `style-constant`, `prompt-optimizer`, `image-generator`, `consistency-checker`, `regeneration-controller` |
| 2 (safety/accounts) | `moderation-stack`, `self-refusal-fallback`, `length-guard`, `auth-and-profiles`, `parent-dashboard`, `export-pdf`, `rate-limiting`, `data-deletion`, `kid-flow-ui` |
| 3 (eval) | `ablation-switch`, `tier1-rating-harness`, `tier2-fun-toolkit`, `metrics-export` |

`story-memory-contract` is written **first** — it freezes §3 for everything downstream.

---

## 8. Open items (AI: do not guess these — flag them)

- **ADR-013 — PDF renderer** (Playwright vs WeasyPrint): decide via a small build-time spike.
- **Observability** — LangSmith vs Langfuse: pick one in Phase 0, record as a new ADR.
- **Story Memory field-level detail** — finalized in the `story-memory-contract` spec, not before.

Anything else that requires changing a locked ADR must go through the ADR process (CLAUDE.md §1).
