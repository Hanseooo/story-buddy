# StoryBuddy — Decision Backlog

The queue of **decisions not yet made**. Distinct from `ROADMAP.md` (build *order*) and
`ADRs.md` (decisions already *frozen*). This file only holds what is still open.

**How to use it.** Each row below is **one dedicated session** → one ADR (or a MASTER_SPEC /
spec edit). Per `CLAUDE.md §1`, architectural decisions are made in their own session, not
inline while building a module. When a row is decided: write the ADR, delete the row from
this file (git keeps the history), and update the affected spec in the same change.

**ADR numbering.** ADRs are append-only sequential; the last is **ADR-029**, so the next free
number is **ADR-030**. Numbers are assigned *when the ADR is written*, not reserved here —
the items below use stable `D-*` ids instead, because the write order can shift.

**Two non-decisions, recorded so they don't get reopened by reflex:**
- The **provider abstraction layer** is already decided — ADR-015 + `backend/providers.py`
  (four thin functions, one impl each, *"not a plugin framework"*). What's open is its
  *internals* (D-C below), not whether to build a wrapper/adapter layer.
- The **structured-output → Pydantic funnel** is already consistent — every LLM call goes
  through `providers.structured_text` / `judge`. The field-order *enforcement technique* is now
  settled too (D-D → parsed-key-order, MASTER_SPEC §3).

---

## Tier 1 — resolved

- ~~**D-1 · Moderation backstop routing**~~ → **ADR-011 (revised 2026-07-21c):** primary Qwen3Guard-Gen
  on the worker CPU, backstop routed to `gpt-oss-safeguard-20b` on OpenRouter.
- ~~**D-2 · PDF renderer**~~ → **ADR-013 (revised 2026-07-21):** WeasyPrint.
- ~~**D-B · LangGraph node & edge conventions**~~ → **ADR-024 (2026-07-22):** partial-return node signature;
  sequential per-scene loop (position from `final_image_ref is None`, no cursor); upsert-by-`scene_id` reducer
  on `scenes[]` only; two pure routers (moderation, consistency). Amends ADR-003, ADR-023.
- ~~**D-C · Provider resilience & failure-mode policy**~~ → **ADR-025 (2026-07-22):** transient-vs-hard error
  taxonomy + retry (OpenAI SDK config for text/judge, one small helper for the fal/httpx path, no new dep);
  hard provider failure raises → job `failed`, never a partial/placeholder book (extends ADR-010); at-least-once
  re-pay accepted (ms window); count-based per-book cost breaker on `cost.image_count`; `jobs.failure_reason`
  enum contract for CC-9, `error` string dev-only. Phase-2 mechanisms (N=3 off-ramp, daily cap, self-refusal
  soften-and-retry) deferred to their specs.

---

## Tier 2 — implementation-architecture (Phase-1 blockers, the real meat)

The ADRs froze *what* (models, pipeline shape); these freeze *how the code is built*. **All Tier 2 items are
resolved:** D-B → ADR-024, D-C → ADR-025, and **D-F + D-G → ADR-023 amendment (2026-07-22)** (D-F: sub-schema
in `contracts/` iff `StoryMemory` embeds it, else beside its node; D-G: `{prefix}{index}` ids —
`s`/`c`/`loc`/`obj` — minted once by the creating node, no id in the LLM schema, stable within-run/resume).
`story-memory-contract` is now `approved` (shape frozen); its **§9 construction gate is resolved** (ADR-023
amendment 2026-07-22b — the worker supplies `story_id = job_id` + Phase-1 dev sentinels for
`classroom_id`/`profile_id` in `config.py`, contract unweakened), so the `job_state.py` port is unblocked.

*(D-C · Provider resilience & failure-mode policy → ADR-025, 2026-07-22. Phase-2 mechanisms it deferred —
N=3 moderation off-ramp, per-classroom daily cap, self-refusal soften-and-retry — are owned by the
`moderation-stack` / `rate-limiting` / `self-refusal-fallback` specs, not this backlog.)*

---

## Tier 2b — opened by Phase 0.5 — **closed**

*(D-H · Image acceptance → **ADR-028**, 2026-07-29. All three sub-questions resolved: **(1)** `FailureReason`
is **frozen permanently at 7** — it is the *identity* taxonomy, and anatomy/composition are properties of the
rendering, so they stay out of the closed set Objective 4's F1 is computed over; **(2)** `VlmVerdict` gains
`anatomy_intact: bool = True`, declared last so ADR-004's ordering is untouched — additive, no `schema_version`
bump, and it also resolves the best-of ranking signal ADR-024 handed to `regeneration-controller`
(lexicographic over `same_character` → `anatomy_intact` → `style_match`, no scalar); **(3)** the canonical
reference is judged against its description inside `char_bible` with a **3-draw cap and best-of fallback**,
persisted as `Character.ref_verdict` — a node-internal loop, **not** a conditional edge, so ADR-003 and ADR-024
are unamended. ADR-007 is amended. No capstone document changes. Nothing blocks the `job_state.py` port.)*

---

## Tier 2c — opened by `character-bible` (2026-07-30) — **closed**

*(D-I · The character/style reveal + confirm step → **ADR-029**, 2026-07-31. All three sub-questions resolved:
**(1)** a dedicated `reveal` node holding an `interrupt()` and **no effects** — so a resumed re-execution re-pays
nothing — with a pure `route_reveal` looping `"try_again"` back to `char_bible`; **(2)** one tap = **one** draw +
**one** judge call for the flagged character only, capped at **3 taps per book**, the redraw targeted by the
attribute the child tapped, the overwrite unconditional because the child is the judge; **(3)** CC-3's `prelude`
**6 → 9**, and ADR-024's `fixed_prelude` +7 super-steps. Amends ADR-003 on its branch **count** but not its
rationale — the router is pure and the nondeterminism is a human, not an orchestrator — plus ADR-024 (wiring) and
ADR-025 Decision 4 (breaker bound). Adds `awaiting_confirm` to `jobs.status` (a Phase-2 migration; `0002` goes to
`style-presets`) and
`POST /jobs/{id}/confirm`. **Nothing is built in Phase 1:** CC-1 requires the Phase-2 char-ref moderation gate to
precede the reveal, so the node, migration and endpoint land together with it. `character-bible` §5 and
`story-memory-contract` are corrected in the same change.)*

---

## Tier 3 — convention formalizations (likely MASTER_SPEC edits, not ADRs)

*(D-E · Testing-seam convention → MASTER_SPEC §6 "The node test seam", 2026-07-22: one module-level
helper per node = the effect boundary; helper seam for node/graph tests, provider seam for helper tests;
import providers by name for patch-where-used. This tier is closed.)*

---

## Feature-spec backlog (not decisions — normal brainstorming → spec flow)

Tracked here for one-file visibility. These follow the `CLAUDE.md §4` spec-before-code workflow
(`docs/specs/`, from `TEMPLATE.md`), **not** the ADR-session flow above. Written just-in-time in
roadmap order. Source: MASTER_SPEC §7.

**Phase 1 (core) — `story-memory-contract` FIRST (see D-A):**
- [x] `story-memory-contract`  spec **`approved`, shape frozen 2026-07-22** (ADR-023/024 + D-F/D-G amendment);
      **§9 construction gate resolved 2026-07-22b** (ADR-023 amendment — worker supplies `story_id=job_id` +
      Phase-1 dev sentinels). Next: the `job_state.py` migration (build).
- [x] `story-analyzer`   *(spec **built 2026-07-29** — `docs/specs/story-analyzer.md`;
      `pipeline/analyze.py` mints the roster. Caps characters at 3 — the pre-scene cost ceiling
      against ADR-028's 3-draw cap. Requires `species` at the LLM boundary so ADR-028's re-roll can't collapse
      on an empty description; `contracts/` untouched. Hands `Scene.characters_present` to `scene-segmentation`
      and description *richness* to `character-bible`)*
- [x] `scene-segmentation`   *(spec **built 2026-07-29** — `docs/specs/scene-segmentation.md`;
      `pipeline/segment.py` splits into scenes (≤15), enforces verbatim excerpts, maps names → char_ids.
      Retired `caption_for`/`SceneCaption` per ADR-013. Hands `scenes[].prompt` to `prompt-optimizer`.)*
- [x] `character-bible`   *(spec **built 2026-07-30** — `docs/specs/character-bible.md`;
      `pipeline/char_bible.py` owns ADR-028's reference-acceptance loop — draw → judge vs
      `CharacterDescription` → re-roll, 3-draw cap, best-of by `attributes_present`. Caps references at
      **2** per ADR-004. Authored `settings.default_style_fragment` (ADR-022 `cel`); `contracts/`
      untouched. Opened **D-I**, since closed → **ADR-029** (the reveal is a Phase-2 `reveal` node; this
      spec's CC-3 `prelude` corrected 6 → 9). Hands deterministic-path idempotency and scene-image
      `cost.image_count` to `image-generator`, and the preset dict to `style-presets`.)*
- [x] `style-presets`   *(spec **built 2026-07-31** — `docs/specs/style-presets.md`; `settings.style_presets`
      computed field with three ADR-022 fragments, `POST /storybooks` validates and stores `style_preset_id`,
      worker resolves `None → "cel"` and constructs `StoryMemory.style` before the graph starts.
      `supabase/migrations/0002_jobs_style_preset_id.sql` ships the nullable column. Hands the preset dict and
      frozen `style.prompt_fragment` to `prompt-optimizer` and `image-generator`.)*
- [x] `prompt-optimizer`   *(spec **built 2026-07-31** — `docs/specs/prompt-optimizer.md`;
      `pipeline/prompt_optimizer.py` implements `build_prompt` (wired into `generate_scene`, replacing
      the caption stub) and `correct_prompt` (no caller yet — hands off to `regeneration-controller`).
      `contracts/` untouched.)*
- [x] `image-generator`   *(spec **built 2026-07-31** — `docs/specs/image-generator.md`;
      `generate_scene` is now reference-conditioned: `edit_image` when canonical refs are present,
      `text_to_image` otherwise. Fixes the `scene-1.png` Storage-path collision (deterministic
      per-scene paths). ADR-025 D4 cost breaker live. CC-10 Storage-exists skip (idempotent resume).
      `MAX_SCENES` and `IMAGE_BUDGET` extracted to `app/config.py`. `contracts/` untouched.
      `final_image_ref` is provisional — `consistency-checker` takes ownership.)*
- [ ] `consistency-checker`   *(code: `pipeline/consistency_check.py` — stub)*
- [ ] `regeneration-controller`   *(no file yet; needs the ADR-023 failure-reason enum + ADR-024 loop shape; owns the best-of **rule** — ADR-028 supplied the signal: lexicographic over `same_character` → `anatomy_intact` → `style_match`)*

**Phase 2 (safety / classroom):**
- [ ] `moderation-stack`   *(D-1 decided → ADR-011c; spec: **draft 2026-07-28** — `docs/specs/moderation-stack.md`; no code yet)*
- [ ] `filipino-pii-recognizers`
- [ ] `self-refusal-fallback`
- [ ] `length-guard`
- [ ] `auth-and-classroom`
- [ ] `teacher-dashboard`
- [ ] `classroom-sharing`   *(display-only gallery — no `peer-reflection`/`story-map`, cut per ADR-021)*
- [ ] `narration`   *(ADR-020; `providers.narrate()` not yet implemented)*
- [ ] `export-pdf`   *(D-2 decided → ADR-013: WeasyPrint)*
- [ ] `rate-limiting`
- [ ] `data-deletion`   *(must own ADR-029's ⚠️: a job can sit in `awaiting_confirm` forever. The sweep is one
      line over the existing `jobs.updated_at`; what this spec has to **decide** is the terminal status it writes,
      since a swept pause is not ADR-025-`failed` and `FailureReason` is frozen at 7 by ADR-028.)*
- [ ] `kid-flow-ui`

**Phase 2.5 (fine-tune):**
- [x] `judge-finetune`  ✅ written
- [x] `annotation-surface`  ✅ written *(ADR-026 — the `(research)/annotate/` + `adjudicate/` routes and the
  `annotations` table; supersedes `judge-finetune` §5's `labels/*.csv`)*

**Phase 3 (eval):**
- [ ] `metrics-export`
- [x] `functional-verification-matrix`  ✅ written *(Tool A, Objectives 1–2 — an offline script over tracing
  exports, no UI and no new table)*

*(Objectives 3 and 5 are **written instruments, not code**: the expert-validation interview (Objective 3) and
the ISO/IEC 25010 questionnaire (Objective 5) live in `docs/capstone/research_instruments.md` and are
administered on paper/by form. Objective 4's classification evaluation lives in `judge-finetune` (written);
its labels now come from `annotation-surface`. **Objectives 1–2 do have a code spec** —
`functional-verification-matrix` — added 2026-07-28; Tool A was previously absent from every product doc.
The former `tier1-rating-harness`, `comprehension-instrument`, and `tier2-fun-toolkit` specs remain
**dropped** — the naive-reader comprehension study and the Tier-2 child cohort were removed per ADR-008,
revised 2026-07-25.)*

---

## Recommended next session

> **Phase 0.5 is closed (2026-07-29).** See `docs/product/PHASE_05_RESULTS.md`.
>
> ✅ **`story-memory-contract` is built (2026-07-29).** See `docs/specs/story-memory-contract.md`.
>
> ✅ **`story-analyzer` is built (2026-07-29).** See `docs/specs/story-analyzer.md`.
>
> ✅ **`scene-segmentation` is built (2026-07-29).** See `docs/specs/scene-segmentation.md`.

> ✅ **`character-bible` is built (2026-07-30).** See `docs/specs/character-bible.md`.

> ✅ **`style-presets` is built (2026-07-31).** See `docs/specs/style-presets.md`.

> ✅ **`prompt-optimizer` is built (2026-07-31).** See `docs/specs/prompt-optimizer.md`.

> ✅ **`image-generator` is built (2026-07-31).** See `docs/specs/image-generator.md`.

**Build `consistency-checker`** — write `docs/specs/consistency-checker.md` from `docs/specs/TEMPLATE.md` before any code (AGENTS.md).

**No open decision blocks Phase 1, and the backlog has no open rows.** Tiers 1, 2, 2b, 2c, and 3 are all
resolved. D-I closed 2026-07-31 → ADR-029; it builds in Phase 2 behind the char-ref moderation gate.

After `consistency-checker`, in roadmap order: `regeneration-controller`.
