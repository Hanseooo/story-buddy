# Feature Spec — Annotation Surface

**Status:** draft · **partially built 2026-08-14** — migration `0014_annotations.sql` + its Tier-A suite
are in; **D-K and D-L resolved** (2026-08-19, via migrations 0016/0017 and explicit backend fetching);
**single-rater test-retest adopted 2026-08-28** (migration `0018`, §4.1) · **Phase:** 2.5 ·
**Owner node:** `frontend/app/(research)/` (route group, not a pipeline node) + `annotations` table (Supabase)
**Derived from:** MASTER_SPEC §2 (system map), §7 (spec index) · **Rationale:** ADR-026 (decision), ADR-017 (auth/roles), ADR-004 (non-circularity), ADR-008 (Objective 4)

> Read ADR-026 first. This spec is the *how*; the ADR is the *why* and it is where the binding decisions
> live. It supersedes the `labels/` raw-CSV mechanism sketched in `docs/specs/judge-finetune.md` §5.3/§5.4 —
> that directory is now historical.

---

## 1. Purpose

Give two researchers a resumable, blinded web surface to label every materialized reference/scene image pair
`same_character` (plus closed-taxonomy reasons) for Objective 4, and give a third researcher an adjudication
view over only the disagreements. It exists because Objective 4's human-established reference labels have no
other legitimate path to a laptop or a spreadsheet — see §3.

⚠️ **"Two researchers" and "a third" describe the mechanism, not the staffing.** One rater operates
all of it, twice over, plus a third pass to adjudicate — see §4.1, which is the protocol actually run
and the honest account of what the resulting agreement number measures.

---

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

This surface does not touch `StoryMemory`. It reads already-generated, already-moderated assets and writes to
a new table, not the pipeline's contract.

- **Reads:** `Character.canonical_ref_image`, `Scene.final_image_ref` (both durable Storage **paths**, per
  `story-memory-contract.md` §2, §5) — resolved to short-lived signed URLs at render time, never persisted.
- **Writes:** rows in the new `annotations` table (§2.1). Nothing in `StoryMemory` changes.
- **Invariants:** an annotator sees a pair exactly once per session state (resumable, §4), never sees another
  annotator's rows (RLS, §2.1), and never sees provenance or a model prediction (§4).

### 2.1 The `annotations` table

> **⚠️ Amended 2026-08-14 — this shape gained two columns, and `build_dataset.py` is now the
> authority.** The DDL below is what migration `0014_annotations.sql` ships. The two additions are
> `anatomy_intact` and `text_free`: `VlmVerdict` declares them, ~~**both gate `Attempt.passed`**~~
> in `pipeline/consistency_check.py`, and a judge trained to emit `true` for them unconditionally would
> break the control loop while scoring well (`judge-finetune.md` §5.2, amended the same day).
> **Amended 2026-09-02:** `anatomy_intact` gates; `text_free` is **rank-only** since
> `lettering-suppression.md` §4.6 risk 2 was taken. Both columns stay and both are still
> human-annotated — a judge that emits `true` for `text_free` unconditionally no longer breaks the
> retry loop, but it still corrupts best-of page selection, which is why the label is still needed.
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
  text_free       boolean not null default true,   -- ranks best-of (gated passed() until 2026-09-02); human-annotated (§2.1)
  failure_reasons text[] not null default '{}',
  round           integer not null default 1,       -- 1|2 = test-retest passes, 3 = adjudication (4.1)
  created_at      timestamptz not null default now(),
  primary key (pair_id, annotator_id, round),
  constraint annotations_failure_reasons_closed check (failure_reasons <@ array[/* the 7 */]::text[]),
  constraint annotations_round_range check (round between 1 and 3)
);
```

> **Amended 2026-08-28 - `round` added and the primary key widened (migration
> `0018_annotation_rounds.sql`).** The two-researchers-plus-adjudicator staffing this spec was
> written for never existed; the capstone has **one rater, permanently** (settled 2026-07-29).
> Under `primary key (pair_id, annotator_id)` one human can write at most one ordinary row per
> pair, so `annotation_truth.resolve_annotations` raised `"Pair <id> has <2 ordinary annotations"`
> for **every** non-pilot pair and `build_dataset.build_records` raised before emitting a single
> manifest record - the entire freeze -> train -> evaluate chain for Objective 4 was unreachable.
> That was a schema hole, not a labelling backlog. `round` is what makes the single-rater
> test-retest protocol in 4.1 expressible; nothing else about the table changed, the taxonomy is
> still frozen at 7 (ADR-028), and the RLS policies below still say exactly what they said.

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
  ⚠️ **The adjudicator's read-all policy is NOT written in 0014.** However, migration `0016` adds `is_adjudicator` to `profiles` and implements the read/update policies (resolving **D-L**).
  ⚠️ **`0018` changed the key, not the policies.** Both policies gate on `annotator_id = auth.uid()`
  and `auth_role()`, never on the key shape, so an annotator still reads and inserts only their own
  rows - across every round. The still-absent `update` grant does more work after `0018` than
  before it: round 2 is the one place this design could decay into the self-revision §4 forbids,
  and having no `update` policy is what makes a round-2 submit necessarily a *new row beside*
  round 1 rather than an overwrite of it. `on conflict do nothing` still resolves a double-submit
  of the **same** round as first-write-wins.
- `pair_id` is opaque — minted by `build_dataset.py`'s pairing step or the seed script, never a filename or a `char_id`. Blinding
  depends on this (§4).
  ⚠️ **Where the pairs themselves live (D-K)** is resolved via the `research_pairs` queue table (migrations `0016` and `0017`). Direct `SELECT` by ordinary researchers is revoked; the Next.js server actions bypass RLS via the service role to fetch pairs and mint short-lived signed URLs from `canonical_storage_path` and `scene_storage_path`, stripping all identity/metadata before passing the blinded pair to the browser.

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

1. Fetch the next unlabelled pair for the signed-in annotator (a pair they have no row for **at the
   currently open round** - §4.1).
2. Render reference + scene side by side via freshly minted signed URLs. **Opaque item IDs, shuffled order,
   no provenance** — no story title, no character name, no filename that could leak identity
   (`research_instruments.md:38`, `:159`; `methodology.md:238-240`).
3. Annotator ticks `same_character` (radio: Different Character / Same Character) and zero or more reasons
   from the closed taxonomy (checkboxes, only enabled when `same_character` marks a difference).
4. Submit writes one row to `annotations`; the next pair loads. No back button that lets an annotator revise
   after seeing the next item — a submitted row is final for that annotator (adjudication is the only
   correction path, not self-revision).

**`adjudicate/`** — a third *label*, shown **only** the pairs where the two annotators disagree on `same_character`, `failure_reasons` taxonomy checkboxes, `anatomy_intact`, OR `text_free`. Same blinded rendering; the adjudicator's row is the **authoritative final label**, not merely a third vote. `build_dataset.py` uses this adjudicator row exclusively when it exists to resolve conflicts.

### 4.1 Single-rater test-retest (the protocol actually run)

**This project has one rater and always will** (settled 2026-07-29; the "two researchers" of §1 and
ADR-026 never materialized). Everything above still describes the mechanism; this subsection
describes who operates it and what the resulting numbers do and do not mean.

**The protocol.** The single rater labels every pair **twice**, cold: a full pass over the queue at
`round = 1`, then a second full pass at `round = 2`. The two rounds are the two ordinary labels the
consensus resolver already expected. Where they agree, the pair resolves with no adjudication; where
they disagree, the pair is `conflicted` and needs a **round 3**.

**What "cold" means and who enforces which part:**

- *Enforced in code* - `getNextPair` does not open round 2 until round 1 covers the **entire** queue,
  so every pair gets a full pass over the corpus between its two looks and the rater is never handed
  the same image twice in a row.
- *Enforced by the schema* - the rater is never shown their round-1 answer. There is no `update`
  policy, no read-back of a submitted label into the form, and no back button (§4). Round 2 starts
  from a blank form every time.
- *Process discipline, NOT enforceable* - the calendar gap between the two passes. Like the held-out
  "read once" rule in §8, this is a scheduling obligation on whoever runs the labelling, flagged here
  rather than silently assumed. A round 2 run the same evening as round 1 is a weaker measurement
  than one run a fortnight later, and nothing in the database can tell the difference.

**Adjudication with one human.** §4 says a third annotator adjudicates. With one rater that can only
mean the same human looking a third time, knowing the two passes disagreed - so **round 3 is the
adjudication slot**, and `annotation_truth.is_adjudication` treats a `round >= 3` row exactly as it
treats a distinct adjudicator profile's row: authoritative, used exclusively, never unioned with the
ordinary labels. Two properties make this safe rather than a laundered self-revision:

1. It is a **new row**. Rounds 1 and 2 stay in the table exactly as submitted and remain the *only*
   evidence `annotation_agreement.jsonl` is built from, so adjudication can never retroactively
   inflate the agreement statistic. The adjudication rate is reported separately in
   `freeze_report.json`.
2. It is **bounded**. `check (round between 1 and 3)` closes the range in the database; a 4th round
   would be the self-revision path §4 forbids, so there is no way to write one.

It is **not** independent, and it is not claimed to be. An adjudicated pair's label is one person's
considered third judgment, and the honest reading of a high adjudication rate here is *"this rater
found these pairs genuinely hard"*, not *"two people converged"*.

**Adjudication route authorization.** Both `/adjudicate` server actions authenticate any `researcher`
profile first, then authorize from server-read annotation state. Exactly two ordinary rows must exist.
The allowed shapes are: the same ordinary researcher authored rounds 1 and 2 and now writes round 3,
or a distinct `is_adjudicator = true` researcher authored neither ordinary row and writes the
authoritative row. Mixed self/other ordinary rows, prior adjudication evidence, a fourth label, and
malformed rounds fail closed. `/annotate` stays ordinary-only and still writes only rounds 1 and 2.

**Inter-rater agreement is UNDEFINED for this dataset, by design.** Cohen's kappa between two
annotators cannot be computed from one annotator's labels - not "not yet computed", not "pending a
second rater": undefined, permanently. What `judge-finetune.md` §7 reports instead is **intra-rater
(test-retest) agreement** - the same kappa arithmetic over round 1 vs round 2 - which measures the
rater's self-consistency and bounds label noise, and is a strictly weaker claim than inter-rater
agreement because it cannot detect a bias the rater holds consistently. Any manuscript sentence that
reports this number must name it test-retest and must state that limitation. The two-annotator
machinery is left intact in schema and code so a genuine second rater would work if one ever
appeared; that is contingency, not a plan.

**Resumability.** The achieved corpus may not be labelled in one sitting. The "next unlabelled pair"
query is the entire resume mechanism: closing the tab and returning later re-derives position from the
`annotations` table, no separate progress cursor to keep in sync.

**Edge cases:**
- Annotator reloads mid-pair before submitting — no partial row exists; they see the same pair again (no
  data loss, no duplicate).
- Two annotators are assigned the same pair concurrently by design (that is the point — independent labels);
  the composite primary key (`pair_id`, `annotator_id`, `round`) makes a double-submit by the *same* annotator
  **at the same round** a conflict, not a duplicate row - while leaving that annotator's *next* round free. Resolved `on conflict do nothing` — **first write wins**, not a true
  upsert: an upsert would overwrite the submitted label, which is the self-revision this section's
  forward-only rule forbids, and it would need an RLS `update` grant `0014` deliberately withholds.
- Annotator has no pairs left — a plain "you're done" state, not an error.
- Two distinct adjudicator profiles could both insert round 3 for the same pair concurrently because the key
  includes `annotator_id`. The active single-rater protocol never exercises that contingency; closing it
  atomically would require a new database constraint or transaction decision, so it remains an accepted risk
  unless a genuine second adjudicator is added.
- If `annotate/` or `adjudicate/` fails at runtime, its generic error boundary keeps provider and
  database details out of the UI and offers retry, the research lab, and `POST /auth/signout` for
  stale-session recovery.

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
- The composite primary key (`pair_id`, `annotator_id`, `round`) makes a resubmission *of the same round*
  an upsert, not a second row - while one rater's rounds 1, 2 and 3 are three distinct rows.
- `round` defaults to 1 for a client that omits it, and a value outside 1-3 is rejected by the check
  constraint.
- `annotate/` never writes round 3, and does not open round 2 until round 1 covers the whole queue.
- `adjudicate/`'s query returns exactly the pairs with two `annotations` rows disagreeing on
  `same_character`, `failure_reasons`, `anatomy_intact`, or `text_free` — no false positives from pairs with only one label so far.
  A solo ordinary researcher may see their own conflicting rounds 1 and 2; mixed self/other ordinary
  rows and already-adjudicated pairs are skipped.
- The pair-fetch query for `annotate/` never returns a pair the current annotator already has a row for.
- `build_dataset.py` paginates the `annotations` read beyond Supabase's default 1,000-row response cap;
  the full dual-annotation campaign cannot be exported from a truncated first page.
- No component under `frontend/app/(research)/` renders a filename, story title, character name, or model
  prediction alongside a pair awaiting a label (blinding, asserted at the component-test level).
- The `annotate/` and `adjudicate/` error boundaries expose the existing signout route without
  rendering the caught error message.

**Built 2026-08-14 — `backend/tests/test_annotations_rls.py`, 16 cases.** Covers own-rows isolation
(read, cross-annotator read, insert-as-someone-else, non-researcher), the no-`update` finality rule, the
closed taxonomy in all three directions (rejects an outsider, accepts all 7, accepts empty), the two
gating booleans' defaults and their `false` storage, the composite key (first-write-wins and
two-annotators-one-pair), and the disagreement query including the one-label-so-far false positive.
**Extended 2026-08-28 for `0018`** - round default, the closed 1-3 range, one rater's three rounds as
three rows, same-round-resubmission as first-write-wins, and round 2 as an insert that no `update`
policy can turn into a revision of round 1.
⚠️ **`skipif`-gated on `SUPABASE_DB_URL` and therefore not run in CI** — the same contract as
`test_rls_isolation.py`. The pair-fetch and blinding test cases are pending implementation of the Next.js server actions.

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
  whoever schedules the labelling weekend must not let the achieved held-out characters' pairs be looked at
  more than once end-to-end (the test set, once adjudicated and used, is read exactly one time). This spec's
  table has no way to enforce "read once" in code — it is a process discipline for whoever runs
  `build_dataset.py` against it, flagged here rather than silently assumed.
- `books/` (the Objective-3 book-review route also decided in ADR-026) is out of scope for this spec — it is
  a separate route in the same route group and gets its own spec when built.
- Exact achieved pair count, and whether adjudication runs continuously or in a single pass at the end,
  is a scheduling decision for the labelling weekend, not a build decision here. **Resolved for the
  rounds themselves (§4.1):** round 2 cannot start until round 1 covers the whole queue, because
  `getNextPair` enforces it; the calendar gap between the two passes stays a scheduling obligation.
