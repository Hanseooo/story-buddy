# Feature Spec — Annotation Surface

**Status:** draft · **partially built 2026-08-14** — migration `0014_annotations.sql` + its Tier-A suite
are in; **both routes are blocked on D-K** (and `adjudicate/`'s policy on D-L), see §2.1 · **Phase:** 2.5 ·
**Owner node:** `frontend/app/(research)/` (route group, not a pipeline node) + `annotations` table (Supabase)
**Derived from:** MASTER_SPEC §2 (system map), §7 (spec index) · **Rationale:** ADR-026 (decision), ADR-017 (auth/roles), ADR-004 (non-circularity), ADR-008 (Objective 4)

> Read ADR-026 first. This spec is the *how*; the ADR is the *why* and it is where the binding decisions
> live. It supersedes the `labels/` raw-CSV mechanism sketched in `docs/specs/judge-finetune.md` §5.3/§5.4 —
> that directory is now historical.

---

## 1. Purpose

Give two researchers a resumable, blinded web surface to label ~750–1000 reference/scene image pairs
`same_character` (plus closed-taxonomy reasons) for Objective 4, and give a third researcher an adjudication
view over only the disagreements. It exists because Objective 4's human-established reference labels have no
other legitimate path to a laptop or a spreadsheet — see §3.

---

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

This surface does not touch `StoryMemory`. It reads already-generated, already-moderated assets and writes to
a new table, not the pipeline's contract.

- **Reads:** `Character.canonical_ref_image`, `Attempt.image_ref` (both durable Storage **paths**, per
  `story-memory-contract.md` §2, §5) — resolved to short-lived signed URLs at render time, never persisted.
- **Writes:** rows in the new `annotations` table (§2.1). Nothing in `StoryMemory` changes.
- **Invariants:** an annotator sees a pair exactly once per session state (resumable, §4), never sees another
  annotator's rows (RLS, §2.1), and never sees provenance or a model prediction (§4).

### 2.1 The `annotations` table

> **⚠️ Amended 2026-08-14 — this shape gained two columns, and `build_dataset.py` is now the
> authority.** The DDL below is what migration `0014_annotations.sql` ships. The two additions are
> `anatomy_intact` and `text_free`: `VlmVerdict` declares them, **both gate `Attempt.passed`** in
> `pipeline/consistency_check.py`, and a judge trained to emit `true` for them unconditionally would
> break the control loop while scoring well (`judge-finetune.md` §5.2, amended the same day).
> `subjects_unique` and `style_match` are **not** annotated — non-gating, so a human label on them buys
> nothing the loop acts on. `judge-finetune.md` §4's *"extend before annotation begins, never during"*
> makes this the last free moment; the taxonomy itself is untouched and stays frozen at 7 (ADR-028).

```sql
create table annotations (
  pair_id         text not null,
  annotator_id    uuid not null references auth.users(id) on delete cascade,
  same_character  boolean not null,          -- true = Same Character. Maps to manuscript label 0.
                                             -- false = Different Character = manuscript label 1 = POSITIVE class.
  anatomy_intact  boolean not null default true,   -- GATES passed(); human-annotated (§2.1 amendment)
  text_free       boolean not null default true,   -- GATES passed(); human-annotated (§2.1 amendment)
  failure_reasons text[] not null default '{}',
  created_at      timestamptz not null default now(),
  primary key (pair_id, annotator_id),
  constraint annotations_failure_reasons_closed check (failure_reasons <@ array[/* the 7 */]::text[])
);
```

- ⚠️ **`same_character` is polarity-inverted against the manuscript's integer label, and this is the single
  easiest place in the project to introduce a silent, total error.** The column follows its own name — `true`
  means the two images show the same character — which matches `VlmVerdict.same_character` in
  `story-memory-contract.md`, so the human label and the judge's prediction share one serialization and can be
  compared without a translation step. The manuscript reports the *positive class* as
  `1 = different_character` (`judge-finetune.md` §1, `methodology.md` §7). **The mapping is therefore
  `label = not same_character`, and it belongs in exactly one place — `build_dataset.py`'s export — never
  re-derived at a call site.** Inverting this flips precision and recall for Objective 4 while every number
  still looks plausible.
- `failure_reasons` is constrained to the closed 7-item taxonomy in `judge-finetune.md` §4 — Postgres `check`
  or an app-level Pydantic model, not free text. Extending it after annotation starts invalidates every label
  already collected (§4 below).
- **RLS:** an annotator role can `select`/`insert` only rows where `annotator_id = auth.uid()`. This is what
  makes "independent labelling" a database policy instead of a promise — CC-4. Annotators are `researcher`
  profiles; `0007`'s role check has no separate `annotator` value and `profiles.role` is the only role source
  (ADR-017). There is deliberately **no `update` and no `delete` policy** — §4's forward-only rule makes a
  submitted row final, so the client resolves a double-submit with `on conflict do nothing` (first write wins)
  rather than a true upsert, which would need an `update` grant and would hand an annotator a self-revision
  path.
  ⚠️ **The adjudicator's read-all policy is NOT written.** "The `researcher` role with the adjudicator flag"
  has no schema representation — `profiles` carries no such column — and adding one is a schema decision.
  Logged as **D-L** in `docs/product/DECISION_BACKLOG.md`; `0014` grants read-all to no one, and the §6 test
  for it is skipped naming that row.
- `pair_id` is opaque — minted by `build_dataset.py`'s pairing step, never a filename or a `char_id`. Blinding
  depends on this (§4).
  ⚠️ **Where the pairs themselves live is UNDECIDED (2026-08-14).** This spec never says how `annotate/`
  gets from a `pair_id` to two Storage paths. `annotations` stores only the label; `pairs_from_memory`
  derives pairs from a `StoryMemory` that exists only inside the LangGraph checkpoint blob (default-deny
  RLS) and is unreachable from a browser; `jobs.pages` carries neither the canonical reference nor
  per-attempt images; `build_corpus.py` writes no `jobs` row at all, so `0008`'s researcher storage policy
  (`approved_at is not null`) does not reach corpus images. Logged as **D-K** in
  `docs/product/DECISION_BACKLOG.md`. **Both routes in §4 are blocked on it** — it decides the fetch query,
  the props, the RLS/storage grants and the blinding boundary all at once.

---

## 3. Position in the system map

Not a LangGraph node. It sits beside the pipeline, downstream of Phase 1 image generation and upstream of
`build_dataset.py` (`judge-finetune.md` §5.3):

```
Phase 1 pipeline output (ref + scene images, already moderated)
        │
        ▼
annotation-surface: annotate/  ──►  annotations table  ──►  adjudicate/ (disagreements only)
        │
        ▼
build_dataset.py  ──►  manifest.jsonl  ──►  judge-finetune training/eval (Phase 2.5)
```

It is gated on the Phase 2 `auth-and-classroom` work: a new **`researcher`** role must exist before either
route can be built. Built in **Phase 2.5**, alongside the labelling weekend it exists to serve — not earlier.

**Why a route group in the existing Next.js app, not a static HTML file or a separate app** (ADR-026):

- Every image lives in a **private Supabase bucket**, reached only through a **short-lived signed URL minted
  on read** — no durable asset URL is ever stored (`docs/capstone/ethics_and_safety.md:62`). A static file has
  no session to mint one from; the only alternative is embedding a Supabase client in it, at which point it is
  a worse web app with no resumable state.
- **Training data must not sit resident on a shared lab PC** (`docs/capstone/hardware_and_hosting.md:209`).
  Bulk-downloading ~1,500 child-derived images to a laptop so a local labeller can open them is exactly what
  that rule forbids.
- Both constraints are satisfied for free by reusing the frontend's existing auth, RLS, and component library
  — the research track gains two screens and one table, not a second application.

---

## 4. Behavior & edge cases

**`annotate/`** — one blinded pair at a time:

1. Fetch the next unlabelled pair for the signed-in annotator (a pair they have no row for yet).
2. Render reference + scene side by side via freshly minted signed URLs. **Opaque item IDs, shuffled order,
   no provenance** — no story title, no character name, no filename that could leak identity
   (`research_instruments.md:38`, `:159`; `methodology.md:238-240`).
3. Annotator ticks `same_character` (radio: Different Character / Same Character) and zero or more reasons
   from the closed taxonomy (checkboxes, only enabled when `same_character` marks a difference).
4. Submit writes one row to `annotations`; the next pair loads. No back button that lets an annotator revise
   after seeing the next item — a submitted row is final for that annotator (adjudication is the only
   correction path, not self-revision).

**`adjudicate/`** — a third annotator, shown **only** the pairs where the two annotators' `same_character`
values disagree. Same blinded rendering; the adjudicator's row is a third `annotations` entry, keyed as any
other annotator so `build_dataset.py` can resolve ties without special-casing the schema.

**Resumability.** ~750–1000 pairs per annotator cannot be labelled in one sitting. The "next unlabelled pair"
query is the entire resume mechanism: closing the tab and returning later re-derives position from the
`annotations` table, no separate progress cursor to keep in sync.

**Edge cases:**
- Annotator reloads mid-pair before submitting — no partial row exists; they see the same pair again (no
  data loss, no duplicate).
- Two annotators are assigned the same pair concurrently by design (that is the point — independent labels);
  the composite primary key (`pair_id`, `annotator_id`) makes a double-submit by the *same* annotator a
  conflict, not a duplicate row. Resolved `on conflict do nothing` — **first write wins**, not a true
  upsert: an upsert would overwrite the submitted label, which is the self-revision this section's
  forward-only rule forbids, and it would need an RLS `update` grant `0014` deliberately withholds.
- Annotator has no pairs left — a plain "you're done" state, not an error.

---

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] CC-4 Security (RLS + signed URLs) — §2.1's RLS policy is the independence mechanism; every image
      access goes through a signed URL minted on read, never a stored URL.
- [x] CC-10 Checkpointing / resumability — §4; the "next unlabelled pair" query is the sole resume state.
- [ ] CC-1 Moderation ordering — N/A. Every image shown was already moderated in Phase 1/2; this surface adds
      no new moderation gate.
- [ ] CC-2 PII redaction — N/A. Images, not story text.
- [ ] CC-3 Cost control — N/A. No model calls; this is a CRUD surface over existing assets.
- [ ] CC-5 Observability — not instrumented beyond ordinary app logging; this is offline research tooling, not
      the production pipeline (contrast `functional-verification-matrix.md`, which lives entirely in traces).
- [ ] CC-6 Accessibility — N/A. Researcher-only surface, not the kid- or teacher-facing product.
- [ ] CC-7 Reproducibility (seed) — N/A. Human judgment, not a model call.
- [ ] CC-8 Kid vs parent design — N/A. Neither audience; a third, researcher-only surface.
- [ ] CC-9 Failure states = success states — N/A in the child-facing sense; ordinary empty/loading states only.

---

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

Models mocked (there are no model calls here). Assertions:

- RLS: an authenticated annotator's `select` on `annotations` returns only rows where
  `annotator_id = auth.uid()`; a `researcher`-adjudicator role's `select` returns all rows.
- `annotations.failure_reasons` rejects a value outside the closed 7-item taxonomy (mirrors
  `story-memory-contract.md` §6's `FailureReason` test).
- The composite primary key (`pair_id`, `annotator_id`) makes a resubmission an upsert, not a second row.
- `adjudicate/`'s query returns exactly the pairs with two `annotations` rows disagreeing on
  `same_character` — no false positives from pairs with only one label so far.
- The pair-fetch query for `annotate/` never returns a pair the current annotator already has a row for.
- No component under `frontend/app/(research)/` renders a filename, story title, character name, or model
  prediction alongside a pair awaiting a label (blinding, asserted at the component-test level).

**Built 2026-08-14 — `backend/tests/test_annotations_rls.py`, 16 cases.** Covers own-rows isolation
(read, cross-annotator read, insert-as-someone-else, non-researcher), the no-`update` finality rule, the
closed taxonomy in all three directions (rejects an outsider, accepts all 7, accepts empty), the two
gating booleans' defaults and their `false` storage, the composite key (first-write-wins and
two-annotators-one-pair), and the disagreement query including the one-label-so-far false positive.
⚠️ **`skipif`-gated on `SUPABASE_DB_URL` and therefore not run in CI** — the same contract as
`test_rls_isolation.py`. The adjudicator read-all case is **skipped** pending **D-L**; the pair-fetch and
blinding cases are **not written** — they belong to routes blocked on **D-K**.

---

## 7. Eval / quality checks (if fuzzy — MASTER_SPEC §6 Tier B)

N/A. This surface produces no generated content and is not itself measured — it is the instrument that
produces Objective 4's human reference labels, which `judge-finetune.md` §7 evaluates.

---

## 8. Linked decisions & open questions

**Depends on:** ADR-026 (this spec's binding decision), ADR-017 (the `researcher` role rides `auth-and-classroom`'s
auth), ADR-004 (non-circularity — no predicted verdict may appear beside a pair awaiting a human label), ADR-008
(Objective 4's framing of what these labels are for).

**Supersedes:** the `labels/` directory in `judge-finetune.md` §5.3 ("raw annotator CSVs, one per researcher") and
its implied CSV-merge mechanism. `build_dataset.py` reads the `annotations` table instead of a folder of CSVs —
`judge-finetune.md` is updated to reflect this in the same change that builds this surface, not left stale.

**Deliberately NOT built** (ADR-026 §Alternatives):

- **A live progress dashboard.** Progress is a `count(*)` query run by hand when someone wants it, not a
  standing UI. Building it duplicates the "metrics dashboard renders a table pasted into the manuscript a
  handful of times" argument `functional-verification-matrix.md` §1 makes about Tool A.
- **A cross-annotator agreement view during labelling.** Cohen's κ / adjudication rate is computed **after**,
  by the tally script (`judge-finetune.md` §5.4 step 3), not live. Showing agreement mid-labelling would let an
  annotator's later judgments drift toward or away from the other annotator's — the same contamination risk
  as showing provenance.
- **Any surface that shows an annotator a model's prediction.** This is the one that matters most: the labels
  produced here are the reference Objective 4 measures the fine-tuned judge *against*. If a predicted verdict
  ever renders next to a pair a human is about to label, the human label is no longer independent of the
  system being evaluated — ADR-004's non-circularity rule, applied to the labelling instrument itself rather
  than to the judge's own inference path.

**Open — do not guess (CLAUDE.md §1, §7):**

- Held-out test set discipline (`methodology.md:343-344`) is a labelling-order concern, not a schema concern:
  whoever schedules the labelling weekend must not let the twelve held-out characters' pairs be looked at
  more than once end-to-end (the test set, once adjudicated and used, is read exactly one time). This spec's
  table has no way to enforce "read once" in code — it is a process discipline for whoever runs
  `build_dataset.py` against it, flagged here rather than silently assumed.
- `books/` (the Objective-3 book-review route also decided in ADR-026) is out of scope for this spec — it is
  a separate route in the same route group and gets its own spec when built.
- Exact split of ~750–1000 pairs across the two annotators, and whether adjudication runs continuously or in
  a single pass at the end, is a scheduling decision for the labelling weekend, not a build decision here.
