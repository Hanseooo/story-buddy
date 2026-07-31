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

Phase 0 — scaffold frameworks/deps, provision Supabase/Railway/Vercel, walking skeleton — is
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
| New decisions | append an ADR to `docs/product/ADRs.md` | Permanent, append-only. |

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

**Phase 1 is in progress.** Phase 0.5 closed 2026-07-29 — see `docs/product/PHASE_05_RESULTS.md`.
`story-memory-contract` is **built** (2026-07-29).
`story-analyzer` is **built** (2026-07-29): `backend/pipeline/analyze.py`.
`scene-segmentation` is **built** (2026-07-29): `backend/pipeline/segment.py` splits into ≤15 scenes,
enforces verbatim excerpts, maps roster names → char_ids, enforces `caption = text_excerpt` (ADR-013).
`character-bible` is **built** (2026-07-30): `backend/pipeline/char_bible.py`.

`character-bible` is **built** (2026-07-30): `backend/pipeline/char_bible.py` mints at most 2 canonical
references (ADR-004), judges each against its `CharacterDescription` and re-rolls up to 3 times
(ADR-028), persists the verdict — including a failing one — and bumps `cost.image_count`.

`style-presets` is **built** (2026-07-31): `settings.style_presets` computed field, `POST /storybooks`
validates and stores `style_preset_id`, worker resolves `None → "cel"` and writes `StoryMemory.style`
before the graph starts. Migration: `supabase/migrations/0002_jobs_style_preset_id.sql`.

`prompt-optimizer` is **built** (2026-07-31): `backend/pipeline/prompt_optimizer.py` — `build_prompt`
(wired into `generate_scene`, replacing the `scene.caption or scene.text_excerpt` stub) and
`correct_prompt` (no caller yet; hands off to `regeneration-controller`).

`image-generator` is **built** (2026-07-31): `backend/pipeline/generate_scene.py` is now
reference-conditioned (`edit_image` when canonical refs present, `text_to_image` otherwise).
Fixes the `scene-1.png` path collision. ADR-025 D4 breaker live. `final_image_ref` is provisional.

**Next action: `consistency-checker`** — write `docs/specs/consistency-checker.md` from
`docs/specs/TEMPLATE.md` before writing any code (AGENTS.md).
