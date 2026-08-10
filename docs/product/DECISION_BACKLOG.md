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

- ~~**D-1 · Moderation backstop routing**~~ → **ADR-011 (revised 2026-07-21c):** primary meta-llama/llama-guard-3-8b
  on the OpenRouter, backstop routed to `gpt-oss-safeguard-20b` on OpenRouter.
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
`repeated-failure-offramp` / `rate-limiting` / `self-refusal-fallback` specs, not this backlog.
**Reassignment note (2026-08-02):** ADR-025 pointed the N=3 off-ramp at `moderation-stack`, which shipped
without it; ownership now sits on its own row below. ADR-025 is **not** amended — the backlog is the live
owner map, same convention `input-gate-hardening` used for the length guard.)*

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
- [x] `consistency-checker`   *(spec **built 2026-07-31** — `docs/specs/consistency-checker.md`;
      `consistency_check` judges each scene against its canonical references (one `judge` call per
      character, ADR-004), folds worst-wins, gates on `same_character and anatomy_intact`, and
      finalizes every scene — pass, fail, or unchecked. Takes `final_image_ref` ownership from
      `generate_scene`. `route_next_scene` closes ADR-024's loop. `contracts/` untouched.)*
- [x] `regeneration-controller`   *(spec **built 2026-08-02** — `docs/specs/regeneration-controller.md`;
      `pipeline/regenerate.py` implements ADR-010's one corrected retry. `consistency_check` gains
      `_rank`, the three-term finalize rule, and best-of selection. `route_after_check` closes the
      retry branch. `recursion_limit` set. `correct_prompt` gains `same_character` / `anatomy_intact`
      params and `IDENTITY_CLAUSE` / `ANATOMY_CLAUSE`. Per-attempt Storage path. `contracts/` untouched.
      Remaining Phase-1 spec: `compose`.)*
- [x] `compose`   *(spec **built 2026-08-02** — `docs/specs/compose.md`; `pipeline/compose.py`
      implements the terminal gate: nothing to assemble, because `scenes[]` order already **is** the
      page sequence. Asserts ≥1 scene and every scene finalized (raise → job `failed`), emits the one
      per-book summary line that `functional-verification-matrix` reads, returns `{}`. `contracts/`
      untouched, no migration, no new branch point. Opened no decision — flagged **two unowned gaps**:
      the multi-page persistence gap, **closed 2026-08-02** by `kid-flow-book-persistence` (S1), and the
      `awaiting_confirm` sweep, still owned by `data-deletion` below.)*

**Phase 2 (safety / classroom):**
- [x] `moderation-stack`   *(D-1 decided → ADR-011c; spec: **built 2026-08-02** — `docs/specs/moderation-stack.md`;
      `pipeline/input_gate.py` (real implementation — meta-llama/llama-guard-3-8b + Presidio concurrent, backstop fallback),
      `pipeline/char_ref_mod.py` (qwen/qwen3-vl-32b-instruct + Gemma safety rubric per char ref),
      `pipeline/output_mod.py` (same two-classifier check + soften-and-retry). `moderation_router` and
      `route_after_output_mod` added to `graph.py` (ADR-024 pure-router pattern). `providers.py` gains
      `get_signed_url`, `_parse_guard_response`, `redact_pii`, `classify_text_primary/backstop`,
      `classify_image_primary/backstop`. Worker RAM budget open (§8). The custom Presidio recognizers and
      the length guard are now `input-gate-hardening`; the soften-and-retry is `self-refusal-fallback`.)*
- [x] `input-gate-hardening`   *(spec: **built 2026-08-02** — `docs/specs/input-gate-hardening.md`;
      replaces the `filipino-pii-recognizers` and `length-guard` rows. `app/length.py` `clamp_story`
      (ADR-012 cap, paragraph→sentence boundary with a retains-half floor) + a minimum-length 422 at
      `POST /storybooks` — closes `compose`'s reachable zero-scene raise. `ph_recognizers.py`:
      Tagalog marker patterns (`si`/`ni`/`kay`/`sina`/`nina`/`kina`) + structured-format recognizers
      (`PH_MOBILE`, `PH_ADDRESS`, `PH_TIN`, `PH_SSS`, `PH_PHILHEALTH`) wired into `providers._presidio`
      (now `@lru_cache(maxsize=1)`); `redact_pii` pseudonymizes `PERSON`/`PH_PERSON` (Maria→Ana) so
      `redacted_text` survives as a narrative; structured identifiers hard-redact. PSA surname deny-list
      deferred — marker patterns alone are shippable per spec §8's own escape hatch; deny-list is
      additive to `ph_recognizers.py` when a licensed source is confirmed. One `jobs.truncated`
      migration (number resolved at merge). `contracts/` untouched.)*
- [ ] `self-refusal-fallback`   *(**scoped 2026-08-02 to true model refusal only** — the case PRD §13.4 /
      ADR-011 mech. 4 / `ethics_and_safety.md` Stage 4 all describe: the model **declines** a benign
      mild-peril prompt. Text-side that is `message.parsed is None` (`analyze.py:84`, ADR-025 D1);
      image-side it is a fal provider error (`character-bible` §7). Both hard-fail the job today, which
      makes PRD §13.4's *"a scary-but-innocent story must not dead-end"* false — closing that is this
      spec's whole job (soften-and-retry → gentle reframe). **Not in scope:** `output_mod`'s
      soften-and-retry, which is the opposite trigger (the model complied, the classifier flagged) and
      already **shipped** in `output_mod.py` with a stock softener; this spec may lend it a better
      softener later, but does not own or redesign it. **N=3 split out** to its own row below.
      **Spec written 2026-08-02 — `docs/specs/self-refusal-fallback.md`, status `draft`.** Adds
      `providers.RefusalError` (detected via the SDK's `message.refusal`, checked *before* the
      `parsed is None` branch) + `pipeline/refusal.py` (`soften`, `retry_on_refusal` — one retry, no
      ladder). `contracts/` untouched, no node, no edge, no ADR amended. ⚠️ **Not `approved`:** the
      image half is gated on a rung-1 fal probe (§8 Q1) — Qwen-Image-Edit ships no safety filter and
      may never refuse, in which case the image half is YAGNI and only the text half builds. Building
      it would also move ADR-025 D4's `IMAGE_BUDGET` and change `generate_and_store`'s `paid` bool
      to a count.
      **⏸ DEFERRED 2026-08-02 — do not build, do not spike yet.** The mechanism only fires on a *false*
      refusal (the model being overcautious about a safe story); genuinely unsafe content is already
      caught by `input_gate` and `output_mod`. PRD §13.4 was written when the stack was proprietary,
      where refusals were common — the open-weight switch may have deleted the trigger, and ADR-011's
      own warning says open image models refuse **less**. Failing closed is today's behavior, so
      deferring costs nothing but the lost book on a refusal that may never happen.
      **Reopen when any ONE of these is true:**
      **(a)** a job fails with `parsed is None` on a story that *passed* the input gate — that is the
      refusal signature, and it means the trigger is real;
      **(b)** the CC-5 logs show any refusal at a `providers.py` boundary once real kid stories flow;
      **(c)** the donated corpus turns out peril-heavy (monsters, fights, ghosts) — check this before
      Objective 3's stimuli runs, not after;
      **(d)** `settings.fal_image_model` / `text_model` is swapped for a model that ships a built-in
      safety filter, which reintroduces the trigger by construction.
      The spec is written, so reopening is a build, not a design session.)*
- [ ] `repeated-failure-offramp`   *(split from `self-refusal-fallback` 2026-08-02. PRD §11.4: after **N=3**
      failed revisions of the same story, suggest a fresh story instead of an unbounded retry loop.
      Previously homeless — `ROADMAP.md` filed it under the length guard (corrected in the same change),
      ADR-025 assigned it to `moderation-stack` / `self-refusal-fallback`, and `moderation-stack` shipped
      without it. ⚠️ **Blocked, and possibly YAGNI.** "Revisions of the same story" spans **job
      submissions**, but `StoryMemory` is per-run and `story_id = job_id` (ADR-023 amendment) — there is no
      cross-run counter and no story lineage. It needs a `jobs` column or a lineage id, i.e. a schema
      decision (`CLAUDE.md §2`), **and** there is no revision flow shipped to count: `kid-flow-ui` owns
      "try again with a different story". Do not write this before that flow exists.
      **Half-unblocked 2026-08-02 by `kid-flow-failure-semantics` (docket S3):** the revision flow is
      now specified — `revise` (child edits, new job) and `retry` (same text, new job), both plain
      `POST /storybooks`. S3 ships N=3 as a **client-side, reason-blind counter that suggests and
      never gates**, so PRD §11.4 is satisfied without a column. This row therefore only survives if
      the count must become durable, cross-device, or teacher-visible — and it is **still blocked on
      the same schema decision**, now named: `jobs.parent_job_id`. **The flow is now built (S4, 2026-08-04)** —
      `/write` carries the client-side `sb.failChain` counter and the third-failure offer, so PRD §11.4 is
      satisfied in shipped code and this row buys only durability.)*
- [x] `auth-and-classroom` → **decomposed into four specs; all four built including S3's 33-test Tier-A isolation suite** *(docket
  `docs/specs/auth-and-classroom-docket.md`, DONE 2026-08-06. 42 binding constraints. The four ship
  as one unit: `0007` and `0008` deploy together or neither does (S3-1), and the route move is
  meaningless without them.)*
  - [x] `auth-identity-and-classroom-schema` (S1)   *(**built 2026-08-06** — students are real
    `auth.users` rows via `{nickname}@{code}.students.storybuddy.invalid`; role in `profiles.role`;
    migration `0007` creates `classrooms` + `profiles` with RLS on and zero policies.)*
  - [x] `auth-session-model` (S2)   *(**built 2026-08-06** — one mechanism for all three roles,
    cookie via `@supabase/ssr`. `supabaseClient.ts` migrated to `createBrowserClient`;
    `get_current_user` wired into `POST /storybooks` and `/confirm`.)*
  - [x] `auth-authorization-surface` (S3)   *(**built 2026-08-06** — migration `0008` replaces both
    legacy policy surfaces; Storage joins back to `jobs` rather than changing the path shape; 33-test
    Tier-A isolation suite (`backend/tests/test_rls_isolation.py`, 31 automated + 2 skip). Next free
    migration is `0009`.)*
  - [x] `auth-routes-and-account-ux` (S4)   *(**built 2026-08-06** — `docs/specs/auth-routes-and-account-ux.md`;
    `middleware.ts` path-shaped guard (never reads role, validates `?next=`), `/join` + `/join/[code]`
    three-step wizard (code → nickname → password), `/s/[profileId]` bookshelf with explicit
    `.eq('profile_id')` guard (S4-4), student settings page (no current-password field). 144 tests across
    17 test files. Review fixes: hard violations (async `cookies()`, canonical `supabaseClient`, params type),
    wrong impls (redirect on login, always-check-email on signup), missing deliverables (all five pages).
    Teacher-initiated password reset moved to `teacher-dashboard` by docket amendment 1.)*
- [x] `teacher-dashboard` → **decomposed into three sessions; all three built** *(docket
  `docs/specs/teacher-dashboard-docket.md`, DONE 2026-08-07. **S1** privileged writes & teacher identity
  → **S2** provisioning & the teacher shell → **S3** review & approval. Migrations `0009`–`0011` claimed;
  next free is **`0012`**. Two decomposition gaps both closed: **teacher signup** fixed in S1 (trigger
  coalesces absent `role` to `'teacher'`, `/signup` repaired); **"rejected" as a distinct state** landed
  in S3 (`0011` adds `rejected_at` + `jobs_review_exclusive` CHECK, no `review_status` enum). S3 also
  moved the review write to `POST /jobs/{id}/review`, making auth-docket S3-7 exceptionless with no
  RLS write path anywhere in the system.)*
  - [x] `teacher-privileged-writes-and-identity` (S1)   *(**built 2026-08-07** — `docs/specs/teacher-privileged-writes-and-identity.md`;
    trigger coalesced to `'teacher'`, `require_teacher` + `owned_classroom` on `teacher_router` (service_role),
    reads via RLS. Migration `0009` ADR-flagged.)*
  - [x] `teacher-provisioning-and-shell` (S2)   *(**built 2026-08-07** — `docs/specs/teacher-provisioning-and-shell.md`;
    classroom creation + code minting, bulk student creation (cap 60, idempotent), generated-once passwords,
    `removed_at` + auth ban for removal, `TeacherShell` server component. Migration `0010` ADR-flagged.)*
  - [x] `teacher-review-and-approval` (S3)   *(**built 2026-08-07** — `docs/specs/teacher-review-and-approval.md`;
    three states from two timestamps (`approved_at`, `rejected_at`) + `jobs_review_exclusive` CHECK,
    `POST /jobs/{id}/review` on `teacher_router`, six bidirectional transitions, undo without dialog.
    Revokes `0009`'s column grant and drops `0008`'s approval policy — S3-7 now holds with zero exceptions.
    Migration `0011` ADR-flagged.)*
- [x] `classroom-sharing`   *(**built 2026-08-09** — gallery page + StudentTabBar; `/s/[profileId]/gallery` live; tab bar covers Bookshelf / Gallery / Profile; logout moved to settings)*
- [ ] `narration`   *(ADR-020; `providers.narrate()` not yet implemented. The book reader ships in S4 without a play button. TTS narration is `narration`'s deliverable.)*
- [ ] `export-pdf`   *(D-2 decided → ADR-013: WeasyPrint)*
- [ ] `rate-limiting`
- [ ] `data-deletion`   *(must own ADR-029's ⚠️: a job can sit in `awaiting_confirm` forever. The sweep is one
      line over the existing `jobs.updated_at`; must name the swept-pause status value — S4 maps it to `asleep` FailureScreen kind. Until named, unknown status falls to `retry`. See `kid-flow-reader-and-wait-states.md` §4.4.4.)*
- [x] `kid-flow-ui` → **decomposed into four specs, all built** *(docket `docs/specs/kid-flow-ui-docket.md`,
      DONE 2026-08-04; MASTER_SPEC §7 carries the four rows). The **multi-page persistence gap** `compose`
      flagged is **closed**: `run_job.py`'s `_finish` is the only writer of `pages`/`reveal`, and
      `/book/[jobId]` reads the ordered `jobs.pages` array. `export-pdf` is the second reader of that
      same shape.*
  - [x] `kid-flow-book-persistence` (S1)   *(**built 2026-08-02** — `docs/specs/kid-flow-book-persistence.md`;
        `supabase/migrations/0004_jobs_pages.sql` adds the ordered JSONB `{scene_id, caption, image_path}`
        array, durable Storage paths only. One writer, one write, atomic with `status='complete'`;
        `compose` stays pure. Access is capability-link (the job UUID); kid routes stay flat until
        `auth-and-classroom`. `contracts/` untouched.)*
  - [x] `kid-flow-pause-lifecycle` (S2)   *(**built 2026-08-02** — `docs/specs/kid-flow-pause-lifecycle.md`;
        ADR-029's `reveal` node ships — `backend/pipeline/reveal.py` (effect-free, one `interrupt()`,
        pure projection), `supabase/migrations/0005_jobs_awaiting_confirm.sql`, and
        `POST /jobs/{id}/confirm` as the only exit from a pause (404 → 422 → CAS). The 3-tap cap is
        enforced in `route_reveal`. `SUPER_STEP_PRELUDE = 15`.)*
  - [x] `kid-flow-failure-semantics` (S3)   *(**built 2026-08-02** — `docs/specs/kid-flow-failure-semantics.md`;
        three verbs only — `redraw` / `revise` / `retry`. A terminal job is immutable; recovery is always a
        new job. Four render buckets on every URL-reachable surface. The child never sees a moderation
        category or `jobs.error`. N=3 is a client-side, reason-blind, non-gating counter.)*
  - [x] `kid-flow-reader-and-wait-states` (S4)   *(**built 2026-08-04** — `docs/specs/kid-flow-reader-and-wait-states.md`;
        the multi-page reader over `jobs.pages` with sign-at-read-time, the Realtime-driven wait stepper
        off `current_stage`, the inline reveal on `/process/[jobId]`, and the four `FailureScreen` kinds.
        `useJob` subscribes **and** seeds from a `SELECT`, so a child returning to a paused job sees it.
        No orientation lock — CSS `landscape:` only. No new policy surface.)*
- [x] `job-failure-reason`   *(**built 2026-08-04** — `supabase/migrations/0006_jobs_failure_reason.sql`
      adds a nullable `failure_reason text` with **no check constraint** (an unknown future value must not be
      DB-rejected), plus the taxonomy map in `run_job.py`'s except blocks. ADR-025 Decision 5's shape is
      satisfied. Exactly one value — `child_text` — means *the child's own text was rejected*, written only
      where `moderation_router` raises for the input text; every other value, every unknown value and `null`
      map to `machine` → the `retry` screen, so a future value can never accidentally blame a child.
      `moderation_error`, a flagged canonical reference, an output-moderation failure and a provider error
      all take the `machine` path. Consumed by S4's `FailureScreen`. (`0007` and `0008` are now claimed
      by the auth specs; next free is **`0009`**.)
      `FailureReason` in `contracts/` is untouched — frozen at 7 by ADR-028, a *different*, scene-identity
      taxonomy; conflating them would corrupt Objective 4's F1 denominator.)*

### ⏸ Deferral watch — rows with no trigger yet

Added 2026-08-02 alongside `self-refusal-fallback`'s deferral. Same test applied to every open row:
**does the thing this builds have anything to fire on, or anyone to read it, today?** A row here is
*not* cancelled and *not* re-decided — it is sequenced behind a named condition, so it stops competing
for a session until that condition is real. Rows are listed above as normal; this is the reason index.

| Row | Why it has no trigger yet | Reopen when |
|---|---|---|
| `self-refusal-fallback` | ⏸ **Deferred** (see row above). Fires only on a *false* refusal; open weights refuse least. | Any of (a)–(d) in the row above. |
| `repeated-failure-offramp` | ⚠️ **Possibly deletable.** S3 satisfies PRD §11.4 with a client-side counter, so this row now only buys *durability* of the count. | The count must survive a device switch or reach a teacher. Then `jobs.parent_job_id` first (`CLAUDE.md §2`). |
| `job-failure-reason` | ✅ **Built 2026-08-04** — migration `0006` + the map in `run_job.py`. Row closed; kept here only so the reopen note above is not re-derived. | — |
| `metrics-export` | ⚠️ **Scope undefined** — it appears only in MASTER_SPEC §7's roster with no description anywhere, and `functional-verification-matrix` (Tool A) already covers Objectives 1–2 as an offline script over tracing exports. Possibly not a deferral but a **deletion**. | Someone names a metric that Tool A + `judge-finetune` do not already produce. If no one can, delete the row. |
| ADR-029's `reveal` node | ✅ **Built 2026-08-02** by `kid-flow-pause-lifecycle` (docket S2) — the condition below fired: `pipeline/reveal.py`, migration `0005`, `POST /jobs/{id}/confirm` and S4's reveal surface all landed. Row closed. | — |
| `rate-limiting` | ⚠️ **Judgement call, flagged not decided.** ADR-025 D4's per-book cost breaker is already live, and ADR-017 means no self-serve signup — every account is teacher-issued, so the abuse surface is a known classroom, not the internet. That is *mitigation*, not absence of risk. | Any public or self-serve path appears, **or** a measured cost overrun. Do **not** defer this silently past a public deployment (`CLAUDE.md §7`). |

**Considered and rejected as deferrals** — recorded so the next session does not re-derive them:
- **`narration`** — tempting (ADR-020 itself says it is *"not a research variable"*), **but it is inside a
  measured category**: `functional-verification-matrix.md:65` scores "assembled + **narrated** + exported"
  as a Tool A row, and MASTER_SPEC CC-6 names it as the accessibility mechanism. Deferring it narrows a
  reported evaluation row and drops an accessibility claim — a documented cost, not a free win. Defer only
  as a deliberate trade, with the Tool A row narrowed in the same change.
- **`auth-and-classroom`** — MASTER_SPEC §6 already flags the missing RLS as *"a **child-facing** gap, not a
  paperwork one"*. Not deferrable.
- **`data-deletion`** — Data Privacy Act (RA 10173) + ethics clearance. Not deferrable.
- **`kid-flow-ui`** — the multi-page persistence gap meant Phase 1 produced books **nothing could read**.
  It was the bottleneck, and it is now **built** as four specs (S1–S4, 2026-08-02 → 2026-08-04).
- **`teacher-dashboard`** — carries the manual approval gate that `ethics_and_safety.md` §4 rests on.

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

> ✅ **`consistency-checker` is built (2026-07-31).** See `docs/specs/consistency-checker.md`.

> ✅ **`regeneration-controller` is built (2026-08-02).** See `docs/specs/regeneration-controller.md`.

> ✅ **`compose` is built (2026-08-02).** See `docs/specs/compose.md`.

> ✅ **`moderation-stack` is built (2026-08-02).** See `docs/specs/moderation-stack.md`.

> ✅ **`input-gate-hardening` is built (2026-08-02).** See `docs/specs/input-gate-hardening.md`.

> ⏸ **`self-refusal-fallback` spec written, then DEFERRED (2026-08-02).** See
> `docs/specs/self-refusal-fallback.md` and the ⏸ deferral-watch table above.

> ✅ **`auth-and-classroom` fully built (2026-08-06) — all four specs plus S3's 33-test isolation suite.**
> S4: `middleware.ts` guard, `/join` + `/join/[code]`, `/s/[profileId]` bookshelf, student settings —
> 144 tests across 17 test files. S3: `test_rls_isolation.py` (31 automated + 2 skip). ADR-017's
> "real, testable boundary" is now enforced and verified.

> ✅ **`kid-flow-ui` is built as four specs (2026-08-02 → 2026-08-04).** See
> `docs/specs/kid-flow-ui-docket.md` (DONE) and S1–S4: `kid-flow-book-persistence.md`,
> `kid-flow-pause-lifecycle.md`, `kid-flow-failure-semantics.md`, `kid-flow-reader-and-wait-states.md`.
> ADR-029's `reveal` node and `job-failure-reason` (migration `0006`) landed with it.

**Phase 1 is complete. Phase 2 is in progress** — `moderation-stack`, `input-gate-hardening` and
`kid-flow-ui` (S1–S4) are built.

**`auth-and-classroom` is complete.** The docket `docs/specs/auth-and-classroom-docket.md` is DONE
throughout (2026-08-06). `0007` and `0008` are applied, the child-facing RLS gap is closed, S4 is
fully built (144 tests, 17 files), and S3's Tier-A isolation suite (`test_rls_isolation.py`, 31 + 2)
is written — ADR-017's "real, testable boundary" is now verified.

**`teacher-dashboard` is complete.** The docket `docs/specs/teacher-dashboard-docket.md` is DONE
throughout (2026-08-07). All three sessions done: S1 (`teacher-privileged-writes-and-identity.md`),
S2 (`teacher-provisioning-and-shell.md`), S3 (`teacher-review-and-approval.md`). Migrations `0009`–`0011`
claimed; **next free migration is `0012`**. RLS write path is fully revoked (S3-7 holds with no
exceptions). The e2e teacher flow — signup → create classroom → provision students → review books — is
now fully specified.

> ✅ **`classroom-sharing` is built (2026-08-09).** Gallery page + `StudentTabBar`; `/s/[profileId]/gallery`
> live; tab bar covers Bookshelf / Gallery / Profile; logout moved to settings. Display-only per ADR-021;
> no pipeline or worker involvement. Closes the full e2e loop: teacher creates classroom → student writes →
> teacher approves → peers see the gallery.

**Priority stack (e2e user flow first, updated 2026-08-09):**

~~1. **`classroom-sharing`** — ✅ **built 2026-08-09**.~~

1. **`data-deletion`** — non-deferrable (RA 10173 + ethics clearance), but doesn't unblock anything else.
   Owns ADR-029's ⚠️: the `awaiting_confirm` sweep and the `asleep` status value S4 is waiting for.
2. **`narration` + `export-pdf`** — both independent; can run in parallel sessions. Together they satisfy
   the Tool A evaluation row ("assembled + narrated + exported"). Deferring narration narrows a reported
   Objective row and drops an accessibility claim — defer only as a deliberate trade with the row narrowed
   in the same change.
3. **`rate-limiting`** — must not silently slip past any public deployment.

**No open decision blocks Phase 1 or Phase 2 entry, and the decision backlog has no open rows.** Tiers 1, 2, 2b,
2c, and 3 are all resolved. D-I closed 2026-07-31 → ADR-029; it builds in Phase 2 behind the moderation gate
(now live).
