# StoryBuddy — Development Workflow

How to actually build this thing, day to day, with spec-driven + AI-assisted development.
Reread this whenever you're unsure "what tool do I use now, and at what size?"

**Companions:** rules in [`/CLAUDE.md`](../CLAUDE.md) · how the system connects in
[`MASTER_SPEC.md`](./MASTER_SPEC.md) · build order in [`product/ROADMAP.md`](./product/ROADMAP.md).

---

## The five levels

The whole confusion about "is a phase a spec?" dissolves once you see the granularity levels.
**A phase is not a unit of work — a module is.**

| Level | What it is | Tool | How many |
|---|---|---|---|
| Constitution | MASTER_SPEC + product docs | — (already done) | 1 |
| **Phase** | an **ordering bucket** from the ROADMAP — *not a document* | — | 4 (0–3) |
| **Feature spec** | one **module** in `docs/specs/` | `brainstorming` | ~22, written just-in-time |
| **Plan** | executable checklist for one spec | `writing-plans` | ~1 per spec |
| Code | the implementation | — | — |

You never write "a spec for Phase 1." You write one spec per **module** inside Phase 1
(MASTER_SPEC §7 lists them). Roughly **one spec → one plan → implement**.

---

## The per-module loop (your day-to-day)

```
pick next module from MASTER_SPEC §7 index
   → brainstorming  → feature spec in docs/specs/  (fill TEMPLATE, tick CC checklist) → approve
   → writing-plans  → plan file (checkable steps)                                     → approve
   → implement      → Tier-A tests green (CLAUDE.md §3) → mark spec "built"
→ next module
```

- Brainstorming per module is **fast** — the ADRs already locked the big decisions, so it's mostly
  nailing the **contract slice** (which Story Memory fields it reads/writes) and edge cases. That
  *is* filling `docs/specs/TEMPLATE.md`. It won't be the long interview the MASTER_SPEC needed.
- **Cluster when it's natural.** Tightly-coupled modules can share one brainstorming session and
  still produce separate specs (e.g. `analyze` + `segment`). Don't force isolated sessions on
  modules that are really one conversation.
- **One plan per spec** is the default. Split a plan only if a single module is genuinely large.

---

## The scaffolding exception (Phase 0)

Phase 0 — scaffold frameworks/deps, provision Supabase/Northflank/Vercel, walking skeleton — is
**not a feature module**. There's nothing left to decide (ROADMAP Phase 0 + ADRs *are* its spec),
so it **skips brainstorming** and goes straight to `writing-plans`:

```
ROADMAP Phase 0  →  writing-plans  →  plan file  →  approve  →  execute
```

Rule of thumb: **if the decisions are already made, skip brainstorming and go to writing-plans.**
Brainstorming is for when a module still has real design questions. Scaffolding and other
"just wire up what the ADRs already chose" work do not.

---

## Where the artifacts live — and what to keep vs delete

The noise trap in an AI-assisted repo is stale docs the agent has to wade through. Rule:
**one home per artifact type; specs are durable, plans are disposable.**

| Artifact | Location | Lifespan |
|---|---|---|
| Feature specs | `docs/specs/<module>.md` (from `TEMPLATE.md`) | **Keep** — the contract. Update in place, mark status. Never delete. |
| Plans | `docs/specs/plans/<name>.md` | **Delete** once the module is built + tests green + spec updated. Git keeps history. This folder only ever holds *in-flight* work. |
| New decisions | a new ADR file in `docs/product/adr/` + a row in the `docs/product/ADRs.md` index | Permanent, append-only — never edit a frozen ADR. |

**Point Superpowers at this structure.** By default `brainstorming` would write to
`docs/superpowers/specs/` — don't let it. It writes feature specs into `docs/specs/`, and
`writing-plans` into `docs/specs/plans/`. No parallel `docs/superpowers/` tree (CLAUDE.md §4).

**Do you delete plans after use? Yes.** A completed plan is spent scaffolding — the durable
knowledge is in the feature spec, which you keep current. A `plans/` folder full of finished
checklists is exactly the noise you were worried about.

---

## Quick decision guide

| Situation | Do this |
|---|---|
| Starting a new module with real design questions | `brainstorming` → spec → `writing-plans` → plan |
| Work whose decisions are already locked (scaffold, plumbing) | `writing-plans` directly |
| A module is really two conversations | two specs, maybe one brainstorming session |
| You hit something that fights a locked ADR | stop, write a new ADR, flag it (CLAUDE.md §1) |
| Behavior changed during a build | update the spec in the same change (CLAUDE.md §4) |

---

## Right now

**Phase 2 is in progress.** Phase 1 is complete; Phase 0.5 closed 2026-07-29 — see
`docs/product/PHASE_05_RESULTS.md`. The build log below is chronological.
`story-memory-contract` is **built** (2026-07-29).
`story-analyzer` is **built** (2026-07-29): `backend/pipeline/analyze.py`.
`scene-segmentation` is **built** (2026-07-29): `backend/pipeline/segment.py` splits into ≤15 scenes,
enforces verbatim excerpts, maps roster names → char_ids, enforces `caption = text_excerpt` (ADR-013).
`character-bible` is **built** (2026-07-30): `backend/pipeline/char_bible.py`.

`character-bible` is **built** (2026-07-30): `backend/pipeline/char_bible.py` mints at most 2 canonical
references (ADR-004), judges each against its `CharacterDescription` and re-rolls up to 3 times
(ADR-028), persists the verdict — including a failing one — and bumps `cost.image_count`.

`style-presets` is **built** (2026-07-31, amended by ADR-042 2026-08-17): `STYLE_PRESETS` compatibility mapping and `SELECTABLE_STYLE_PRESET_IDS`, `POST /storybooks` validates selectable presets (`cel`, `gouache`, `cut_paper`) and defaults new jobs to `gouache`, worker resolves legacy `None → "cel"` and writes `StoryMemory.style` before the graph starts. Migration: `supabase/migrations/0002_jobs_style_preset_id.sql`, `0015_add_cut_paper_style_preset.sql`.

`prompt-optimizer` is **built** (2026-07-31): `backend/pipeline/prompt_optimizer.py` — `build_prompt`
(wired into `generate_scene`, replacing the `scene.caption or scene.text_excerpt` stub) and
`correct_prompt` (no caller yet; hands off to `regeneration-controller`).

`image-generator` is **built** (2026-07-31): `backend/pipeline/generate_scene.py` is now
reference-conditioned (`edit_image` when canonical refs present, `text_to_image` otherwise).
Fixes the `scene-1.png` path collision. ADR-025 D4 breaker live. `final_image_ref` ownership
transferred to `consistency_check`.

`consistency-checker` is **built** (2026-07-31): `backend/pipeline/consistency_check.py` judges each
scene image against its canonical references (one judge call per character, ADR-004), folds
worst-wins, gates on `same_character and anatomy_intact`, and finalizes every scene — pass, fail,
or unchecked. Takes `final_image_ref` ownership from `generate_scene`. `graph.py` gains its first
conditional edges: `route_next_scene` registered on `char_bible` and `consistency_check` (ADR-024).

`regeneration-controller` is **built** (2026-08-02): `backend/pipeline/regenerate.py` implements
ADR-010's one corrected retry. `consistency_check` gains `_rank`, the three-term finalize rule, and
best-of selection. `route_after_check` closes the retry branch. `recursion_limit` set.
`correct_prompt` gains `same_character` / `anatomy_intact` params and fixed correction clauses.
Per-attempt Storage path. `contracts/` untouched.

`compose` is **built** (2026-08-02): `backend/pipeline/compose.py` implements the terminal gate —
asserts ≥1 scene and every scene finalized (raise → job `failed`), classifies each page by the
attempt that won, emits the one per-book summary log line. Returns `{}`. `contracts/` untouched.

**Phase 1 is complete. Phase 2 has begun.**

`moderation-stack` is **built** (2026-08-02): `pipeline/input_gate.py` (real), `pipeline/char_ref_mod.py`,
`pipeline/output_mod.py`. `moderation_router` + `route_after_output_mod` in `graph.py`. `providers.py`
gains five moderation functions + `get_signed_url`.

`input-gate-hardening` is **built** (2026-08-02): `docs/specs/input-gate-hardening.md`, which absorbed and
replaced the `filipino-pii-recognizers` stub and the `length-guard` row. `app/length.py` `clamp_story`
(ADR-012 cap, paragraph→sentence boundary) + a minimum-length 422 at `POST /storybooks`;
`ph_recognizers.py` adds Tagalog marker patterns and the structured PH identifier recognizers, wired into
`providers._presidio`. Migration: `supabase/migrations/0003_jobs_truncated.sql`.

`kid-flow-ui` is **built as four specs** (2026-08-02 → 2026-08-04) — the docket
(`docs/specs/kid-flow-ui-docket.md`) is DONE:
- **S1 `kid-flow-book-persistence`** — `supabase/migrations/0004_jobs_pages.sql`; a book is an ordered
  JSONB `pages` array of `{scene_id, caption, image_path}` on the `jobs` row, durable Storage paths only.
  `run_job.py`'s `_finish` is the single writer; `compose` stays pure.
- **S2 `kid-flow-pause-lifecycle`** — ADR-029's reveal ships: `backend/pipeline/reveal.py` (effect-free,
  one `interrupt()`, pure projection), `0005_jobs_awaiting_confirm.sql`, `POST /jobs/{id}/confirm` as the
  only exit from a pause, 3-tap cap enforced in `route_reveal`.
- **S3 `kid-flow-failure-semantics`** — three verbs only (`redraw` / `revise` / `retry`); a terminal job is
  immutable; four render buckets on every URL-reachable surface.
- **S4 `kid-flow-reader-and-wait-states`** — the multi-page reader over `jobs.pages` with sign-at-read-time,
  the Realtime wait stepper off `current_stage`, the inline reveal on `/process/[jobId]`, and the four
  `FailureScreen` kinds. `useJob` seeds from a `SELECT` **and** subscribes.

`job-failure-reason` is **built** (2026-08-04): `supabase/migrations/0006_jobs_failure_reason.sql` plus the
taxonomy map in `run_job.py` — `child_text` only where `moderation_router` raises for the input text,
everything else and `null` → `machine`. (`0007` and `0008` are claimed by the auth specs; migrations
up to `0015` exist on disk; next free is `0016`.)

**`auth-and-classroom` is complete (2026-08-06).** The docket is DONE, `0007` and `0008` are applied,
S3's 33-test Tier-A isolation suite (`backend/tests/test_rls_isolation.py`) is written, and S4
(`middleware.ts`, `/join`, `/join/[code]`, `/s/[profileId]` bookshelf + settings) is fully built —
144 frontend tests across 17 files. ADR-017's classroom boundary is enforced and verified. Next free
migration is `0016`. **Next action per `docs/product/DECISION_BACKLOG.md`:** `data-deletion`
(ethics-gated; owes the `awaiting_confirm` sweep and S4's `asleep` status value) or `export-pdf`
(second reader of `jobs.pages`).
