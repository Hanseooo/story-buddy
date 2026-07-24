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
| The study: RQs, instruments, ethics, defense prep | `docs/product/RESEARCH_PROTOCOL.md` |
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
      plans/             # in-flight implementation plans — disposable, deleted when built
    capstone/            # research/manuscript docs — the paper, not the product
  frontend/              # Next.js app — own package.json (vitest unit)
  backend/               # FastAPI web + RQ worker — own pyproject (pytest)
    app/                 # FastAPI routers, config
    worker/              # RQ job runner
    pipeline/            # LangGraph nodes, one file per module
    contracts/           # Pydantic Story Memory schema = the frozen inter-module contract
    providers.py         # the only place a model provider is named (ADR-015)
    spikes/              # Phase 0.5 probes — real models, real money, never CI
    tests/               # pytest — deterministic, every model call mocked
  supabase/
    migrations/          # schema, RLS policies, buckets (CC-4)
```

**Not built yet** (listed so they are not invented elsewhere): `backend/finetune/` — Phase 2.5 data
manifests, training config, eval (ADR-018). `.github/workflows/` — see §6.

**Frontend and backend are independent projects** (different languages; no shared monorepo build
tooling — that would be speculative for a solo build). Their only contract is the HTTP API and the
Story Memory shape. New ADRs **append** to `docs/product/ADRs.md` — there is no separate
`decisions/` folder.

### Folder rules for AI agents
- New pipeline module → a new file in `backend/pipeline/`, named for its single concern.
- Anything crossing the module boundary goes **through** `backend/contracts/`, never ad-hoc.
- Structured-output sub-schema → `backend/contracts/` **iff `StoryMemory` embeds it** (e.g. `VlmVerdict`);
  a transient wrapper the node unpacks into contract fields and never persists (e.g. `SceneCaption`) lives
  **beside its node** in `backend/pipeline/`. Keys on *embedding*, not on being an LLM boundary (ADR-023 D-F).
- Docs: product rationale → `docs/product/`; engineering how → here; per-feature → `docs/specs/`;
  research/manuscript → `docs/capstone/`.
- Don't scatter READMEs; one per top-level project (`frontend/`, `backend/`) at most.

---

## 2. System Map — how the pieces connect

**Three deployed services** (ADR-005, ADR-009), not one — plus a **fourth, de-scopable** target in
Phase 2.5: the scale-to-zero Modal GPU container serving the fine-tuned judge (ADR-019; first thing cut,
and cutting it returns the judge to OpenRouter with an env-var change):

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
immediately. The **RQ worker** pulls the job and runs the LangGraph graph, **checkpointing to Postgres
after every node** (`langgraph-checkpoint-postgres`) — finer than ADR-005's original "per scene", because
LangGraph checkpoints each super-step (ADR-024). The frontend watches the job row
via **Supabase Realtime**. A stall at scene N resumes from N — never re-rolls 1…N-1 (ADR-005).

### The LangGraph pipeline (deterministic state machine — ADR-003)

Explicit nodes; conditional edges **only** at moderation and consistency branch points.
Each node ↔ one module ↔ one file in `backend/pipeline/`. **The spec mapping is not 1:1** and §7's index
is not phase-aligned with this table: `style-presets` and `prompt-optimizer` are Phase-1 specs covering
node *inputs* rather than nodes of their own, and the `input_gate` / output-moderation / `export` nodes
are specced in Phase 2 (`moderation-stack`, `length-guard`, `export-pdf`). Read §7 for what to write; read
this table for what runs.

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

**Style presets are config, not a node** (ADR-007, ADR-022): **three** hand-authored prompt fragments, one
chosen by the author *before* the canonical reference is generated and then frozen for the storybook
(`style.style_preset_id`). Identity *and* style both ride the canonical reference — which is exactly why
adding presets costs a dict and no new machinery, and why there is **no style-anchor image**.

---

## 3. The frozen contract — Story Memory

The Pydantic model in `backend/contracts/` (shape frozen in `docs/specs/story-memory-contract.md`;
PRD §19's `job` sketch object is **superseded** — ADR-023) is **the** interface
between every module. It is authoritative and versioned. Rules:

- Every LLM call uses **strict JSON-schema structured output** → validated into this schema (never raw
  dict). On OpenRouter this means `response_format: {type: "json_schema", strict: true}` **plus
  `provider.require_parameters: true`** — without the second flag, a routed provider lacking schema
  support silently downgrades to loose JSON mode and this validation boundary is all that catches it
  (ADR-002).
- A module's spec (§7) declares exactly which fields it **reads** and **writes** — its contract slice.
- Schema change = contract change: update schema + affected specs + every consumer, one change.
- The judge verdict is **reason-then-score**: `differences_observed` is declared *before*
  `same_character`. Field order is load-bearing, not cosmetic (ADR-004 amendment). Enforced at the
  provider boundary by `_assert_field_order`, which compares **parsed JSON key order** (`json.loads`
  preserves document order) against `schema.model_fields` — not a raw-text substring scan, so a value
  that quotes a field name can't false-trigger (D-D, 2026-07-22). Verdict fields must serialize under
  their Python names (no aliases), or the check finds no keys to compare and silently passes.
- `eval.seed` drives reproducibility (§6, ADR-008). Seed reproducibility is **provider-specific and must
  be empirically verified** (CC-7, Phase 0.5).

The schema's *shape* is now frozen: **ADR-023** decides the structural questions (the state **is** the
`StoryMemory` model; `schema_version:int` with fail-fast-and-restart, no migrations; live status lives in the
DB job row, not the contract; the failure-reason enum is a closed 7-value set), and field-level detail is
frozen in the **`story-memory-contract`** spec (`docs/specs/`). Node/reducer/loop conventions are frozen in
**ADR-024**: nodes **partial-return** (never mutate-and-return); `scenes[]` carries an upsert-by-`scene_id`
reducer; the per-scene loop is **sequential** (position derived from `final_image_ref is None`, no cursor); the
two branch points (moderation, consistency) use **pure routers** that return a label and never write state.

---

## 4. Tech stack (consolidated)

Product/architecture choices are in the ADRs; this is the working reference, **including testing**.

> **Chosen ≠ installed.** Rows marked ⚙️ are decided but **not yet in any manifest** — do not assume they
> are available. Currently ⚙️: shadcn/ui, Motion, Lottie, `slowapi`, Playwright.
>
> **Section-reference convention.** Bare `§N` in the Notes column (and in §5) refers to **`PRD_v2.md`**,
> which has §9–§20. This file has only §0–§8; its own sections are always written "MASTER_SPEC §N".

| Layer | Choice | Notes / ADR |
|---|---|---|
| Frontend | Next.js (React) + Tailwind + ⚙️shadcn/ui (teacher) + hand-built cartoon-pop (kid) + ⚙️Motion + ⚙️Lottie | Vercel, SSR landing. §9,§12 |
| Backend web | FastAPI | Railway (Singapore). ADR-009 |
| Worker / queue | RQ worker + Redis broker | Separate service. ADR-005 |
| Pipeline engine | LangGraph (deterministic) + `langgraph-checkpoint-postgres` | ADR-003,005 |
| LLM / VLM | `qwen/qwen3-32b` (nodes) + judge (`gemma-3-27b-it` → fine-tuned `Qwen2.5-VL-7B` in Phase 2.5) | ADR-002,004,015,018 |
| Image model | Qwen-Image-Edit 2509/2511 (Apache-2.0), hosted on fal.ai | ADR-001,015 |
| Judge serving | vLLM on a scale-to-zero GPU container (Modal). OpenAI-compatible — `JUDGE_BASE_URL` is the swap | ADR-019 |
| Model access layer | `backend/providers.py` — thin functions, one impl each. **The only file naming a *provider*** (model *ids* are env vars read in `app/config.py` — ADR-015: "swapping a model is an env var; swapping a provider is one file") | ADR-015 |
| Data / auth / storage / realtime | Supabase (Postgres + Auth + Storage + Realtime + RLS). **Classroom-scoped** | ADR-006, ADR-017 |
| Structured extraction | `json_schema` (strict) + `require_parameters` (OpenRouter only) + Pydantic | §12, §3, ADR-002 |
| Moderation | **Qwen3Guard-Gen** (worker CPU) **+ gpt-oss-safeguard-20b** (OpenRouter backstop) (text, both Apache-2.0) + Presidio **+ Filipino recognizers** (PII) + NSFW ViT & VLM rubric (image) | ADR-011 (D-1 resolved) |
| Narration | **Chatterbox** (MIT, expressive) via hosted inference, pre-rendered per page onto Storage; **Kokoro-82M** CPU fallback | ADR-020 (revised) |
| Fine-tuning | **The consistency judge only.** Identity = reference conditioning; style = ADR-007 constant; safety = never | ADR-018 (supersedes ADR-016) |
| Observability | **LangSmith** (tracing, ADR-014) + Sentry (errors) | ADR-014, §16 |
| Rate limiting | ⚙️`slowapi` + cost circuit-breaker; **per-classroom** daily cap deferred to Phase 2 (ADR-025) | §14,§15, ADR-025 |
| Export | HTML template → PDF via **WeasyPrint** (D-2 resolved, ADR-013) | ADR-013, §8 |
| **Testing — FE unit** | **vitest** | mock model calls; component + logic |
| **Testing — BE unit** | **pytest** | mock every `providers.py` call (via the node helper — §6 seam); node logic, contracts, RLS, routing |
| **Testing — e2e** | ⚙️**Playwright + Playwright CLI** | happy path, auth/RLS isolation, processing→slideshow, export |
| **Eval harness** | offline scripts + tracing exports | real models, story corpus; **not CI** (§6) |

### Frontend rendering strategy
Next.js is chosen for **one** load-bearing reason: the teacher-facing **landing page is SSR** (SEO —
teachers discover the product). Everything else is DX. Therefore:

- **Landing page:** server-rendered (SEO, fast first paint).
- **Authenticated app** (kid flow, teacher dashboard): **client components + direct Supabase reads**
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
| CC-3 | **Cost control** | count-based per-book breaker on `cost.image_count` (trips → job `failed`); per-classroom daily cap deferred to Phase 2 | ADR-025, §15 |
| CC-4 | **Security (RLS + signed URLs)** | **classroom**-scoped DB isolation; no public assets | ADR-006, ADR-017 / §14 |
| CC-5 | **Observability** | emits traces/metrics (gen time, regen count, cost, VLM score) | §16 |
| CC-6 | **Accessibility** | Expressive TTS narration per page (Chatterbox, hosted); large targets; minimal text | §17, ADR-020 |
| CC-7 | **Reproducibility** | honors `eval.seed`; deterministic where the model allows | §20, ADR-010 |
| CC-8 | **Student vs teacher design language** | cartoon-pop (student flow) vs calmer/denser (teacher) | §9 |
| CC-9 | **Failure states = success states** | moderation/failure screens get equal design care; kid-legible; UI branches on `jobs.failure_reason` enum, never raw `error` | ADR-025, §9,§13 |
| CC-10 | **Checkpointing / resumability** | node is safe to resume mid-run; no re-roll of completed scenes | ADR-005 |

---

## 6. Testing strategy (two tiers — the bright line)

Non-negotiable split. See `/CLAUDE.md` §3.

**Tier A — Deterministic tests (CI, every change, must stay green).**

> ⚠️ **There is no CI yet** — `.github/workflows/` does not exist, so "must stay green" is currently
> enforced only by running `pytest` locally. Every gate below that says *CI* means *will be CI*. Standing
> it up is the cheapest way to make the rest of this section true (`action_checklist.md` C4).

Everything with one right answer, **with every `providers.py` call mocked**:
- Contract validation (Story Memory Pydantic round-trips, schema rejects bad shapes).
- LangGraph routing (moderation pass/fail and consistency pass/fail take the right edges).
- Job lifecycle & checkpoint/resume (stall at N resumes at N).
- Moderation ordering; PII redaction; truncate-at-scene-boundary; N=3 off-ramp; cost circuit-breaker.
- RLS isolation (one classroom cannot read another classroom's data — ADR-017); signed-URL access.
  ⚠️ **Not true today.** The only migration (`supabase/migrations/0001_jobs_table.sql`) grants
  `select ... to anon using (true)` — no classroom scoping, and no classroom/profile tables exist. There
  is no RLS test. This is a **child-facing** gap, not a paperwork one; it closes in Phase 2 (CC-4).
- e2e happy path + processing→slideshow via Realtime + PDF export (Playwright ⚙️).
- **Never assert on generated content.** "Is the character consistent?" is Tier B.

**Tier B — Eval harness (offline, real models, on demand — never CI).**
The only place fuzzy quality is measured, on the real/realistic story corpus (PRD §10):
- Scene-selection / Story-Completeness (RQ1), acceptability (RQ3), under-length grace (RQ4), naive-reader
  recall (RQ5), judge agreement with human labels on the held-out set (RQ6 — **descriptive only; the
  fine-tuned-vs-baseline comparison was dropped**, ADR-008 rev. 2026-07-22), VLM–human agreement.
- **Is the same instrumentation as the Phase 3 study** (LangSmith/Langfuse) — build once, use for
  both dev feedback and research data. Costs money and is non-deterministic; that's why it's not CI.

**The node test seam (Phase-1 pipeline nodes).**
Every pipeline node is a pure function `node(state: StoryMemory) -> dict` — it returns **only the keys it
changed** and **never mutates `state`** (ADR-024; §3 above). All non-determinism and I/O (provider
calls, storage/DB) live in **one module-level helper per node** that the node calls and that returns
plain data. This yields two patch seams at two altitudes:

- **Helper seam** — node & graph tests patch the helper by name (`pipeline.analyze.caption_for`,
  `pipeline.generate_scene.generate_and_store`). One helper per node ⇒ one patch point per node in graph tests.
- **Provider seam** — the helper's *own* tests patch the `providers.py` function **as imported into the
  node module** (`pipeline.analyze.structured_text`).

Rules:
1. **One helper per node**, wrapping all of that node's effectful work; the node body only maps state. A
   node with no provider call and no I/O (e.g. `compose`) needs no helper.
2. **Import providers by name** — `from providers import structured_text`, never `import providers` +
   `providers.foo()`. The patch target must resolve to `pipeline.<node>.<fn>` (patch-where-used).
3. Node/graph tests mock the **helper**; helper tests mock the **provider**. Either way no real provider
   call runs in CI — this *is* what "mock every `providers.py` call" (CLAUDE.md §3) means.
4. Two unrelated effectful jobs in one node ⇒ **split the node** (one-concern rule, CLAUDE.md §6), don't
   add a second helper.

---

## 7. Feature spec lifecycle

Each MVP module (PRD §5.1) becomes one spec in `docs/specs/`, from `TEMPLATE.md`.

**Lifecycle:** derive from this doc → fill contract slice (§3) + cross-cutting checklist (§5) →
human approves → implement → deterministic tests green (§6 Tier A) → eval checks if fuzzy (§6 Tier B) →
mark done. Behavior change later → update the spec in the same change (CLAUDE.md §4).

**Index (write just-in-time, roadmap order):**

| Phase | Specs to write |
|---|---|
| 1 (core) | `story-memory-contract`, `story-analyzer`, `scene-segmentation`, `character-bible`, `style-presets`, `prompt-optimizer`, `image-generator`, `consistency-checker`, `regeneration-controller` |
| 2 (safety/classroom) | `moderation-stack`, `filipino-pii-recognizers`, `self-refusal-fallback`, `length-guard`, `auth-and-classroom`, `teacher-dashboard`, `classroom-sharing` (display-only gallery — no `peer-reflection`/`story-map`, both cut per ADR-021), `narration`, `export-pdf`, `rate-limiting`, `data-deletion`, `kid-flow-ui` |
| 2.5 (fine-tune) | ✅ `judge-finetune` *(written)* |
| 3 (eval) | `tier1-rating-harness`, `comprehension-instrument`, `tier2-fun-toolkit`, `metrics-export` |

`story-memory-contract` is written **first** — it freezes §3 for everything downstream.
The **failure-reason taxonomy** (`judge-finetune` §4) is shared by `regeneration-controller` and the
Phase-2.5 annotators. Design it once, in Phase 1, or invalidate every label collected under the old one.

---

## 8. Open items (AI: do not guess these — flag them)

**Blocking, and un-run:**
- ⚠️ **Non-human character consistency on Qwen-Image-Edit** — unverified by anyone. The **Phase 0.5 kill
  criterion**. Two characters (easy + invented), blind ON/OFF ablation, two pass conditions. **Every
  document downstream is contingent on this.** Do not collect fine-tune labels before it passes.
- ⚠️ **Seed determinism per hosted provider**, on **both** `edit_image` and `text_to_image` (CC-7). Phase 0.5.
- ⚠️ **Structured output for the judge with *image* input** — support is per `(model, provider)` *and* per
  modality. A text-only probe passes while the judge is broken. Phase 0.5.
- ⚠️ **Filipino / Taglish text-moderation performance** — never measured, and the proprietary backstop is
  gone. **Release gate for Phase 2.** Phase 0.5 probe 4 (ADR-011).

**Open — resolved by the owner, not by code:**
- ⚠️ **ADR-015 is still an operating assumption.** The mandate says "open source"; we build on reading 1
  (*open weight, hosting is orthogonal*). ADR-015 records this as **an assumption, not a confirmation**,
  and it is cheap to hold but expensive to discover wrong late. If the mandate turns out to mean
  *self-hosted*, ADR-015 is void and the fix is a GPU service and its ops — days, not weeks, because
  `providers.py` isolates every vendor call. **Confirm before Phase 2 hardening.** Related and
  unaddressed: ADR-015 permits the non-commercial FLUX.1-dev family as a *fallback*, which the capstone's
  "OSI-clean stack" framing does not currently mention.

**Verify at build time (do not guess):**
- **Modal cold-start budget** for a study session (ADR-019). Measure.
- **Worker RAM** — Presidio+spaCy, NSFW ViT, and the CPU text gate are resident (~2–3 GB); narration is a
  hosted TTS call (ADR-020, revised), so Kokoro is only resident if the fallback is kept warm.
  Check the plan tier at the *start* of Phase 2.

**Deferred by design:**
- **Story Memory field-level detail** — the `story-memory-contract` spec is **written and awaiting owner
  approval**, not yet frozen. §3 above describes its intended shape; until the spec is accepted, treat
  that shape as provisional and do not build consumers against it.
- **The failure-reason taxonomy** — extend it in Phase 1, never during Phase 2.5 annotation.

**Resolved:**
- ~~Moderation backstop routing (D-1)~~ → **ADR-011c:** primary `Qwen3Guard-Gen` on the worker CPU,
  backstop routed to `gpt-oss-safeguard-20b` on OpenRouter (the ADR-011b pair is not routable). One
  backstop call per story; no new privacy surface (input already leaves to OpenRouter, ADR-002).
- ~~ADR-013 PDF renderer (D-2)~~ → **WeasyPrint** — static paged-media template; lighter than Playwright's
  Chromium on a RAM-constrained worker.
- ~~DreamBench++ image licensing beyond evaluation~~ → **evaluate only, never train on it, never
  redistribute it** (`docs/specs/judge-finetune.md` §5.6, §12). Evaluation is the benchmark's
  intended use; no correspondence with the authors is required.
- ~~Observability — LangSmith vs Langfuse~~ → ADR-014 (LangSmith).
- ~~ADR-015's *hardening*~~ → confirmed: **no proprietary models anywhere**. `backend/providers.py` is what
  kept the blast radius to a handful of files. **This did not resolve ADR-015's open question** — see
  "Open" below.
- ~~`omni-moderation-latest` image-input support~~ → moot; the backstop is removed (ADR-015 hardened).

Anything else that requires changing a locked ADR must go through the ADR process (CLAUDE.md §1).
