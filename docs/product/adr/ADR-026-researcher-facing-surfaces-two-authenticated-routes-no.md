# ADR-026 — Researcher-facing surfaces: two authenticated routes, no dashboard

**Status:** Accepted (2026-07-28) · first decision covering the **research track's software**, as opposed to
its design · rides ADR-017's auth · bounded by ADR-014 (observability) and ADR-004 (non-circularity)

**Context:** The study design is thoroughly documented — five objectives, four instruments, ethics staging,
analysis plan (`docs/product/RESEARCH_PROTOCOL.md`, `docs/capstone/evaluation_instruments_brief.md`). The
*software the researchers actually operate* is not. The gap was invisible because each doc assumed a tool the
next one would specify: `docs/specs/judge-finetune.md` §5.4 says "the same **interface** that shows a human a
reference and a scene and asks 'same character?'" while §5.3 sketches `labels/` as "raw annotator CSVs, one per
researcher" — an interface that was never specified and a CSV mechanism that was never checked against the
storage rules. Meanwhile Tool A (the Functional Verification Matrix, Objectives 1–2) is new in the 2026-07-25
instrument realignment and appears in **zero** product documents.

Two constraints decide this ADR, and both were discovered by reading the ethics docs rather than the product
docs. First, **no durable asset URL is ever stored**: every generated image lives in a private bucket and is
reached only through a short-lived signed URL minted on read (`docs/capstone/ethics_and_safety.md` §Access).
Second, **training data must not sit resident on a shared lab PC** (`docs/capstone/hardware_and_hosting.md`
§Data care). Objective 4 needs ~750–1000 labelled pairs from two annotators working over multiple days.

**Decision:**

1. **Two routes, in the existing frontend, gated on the Phase-2 auth work.** A `frontend/app/(research)/` route
   group behind a new **`researcher`** role added to `auth-and-classroom` (ADR-017). Built in **Phase 2.5**,
   beside the labelling work it exists to serve — not earlier, and never before Phase 0.5 has passed.
   - **`annotate/`** — one blinded pair at a time (reference + scene), `same_character` plus zero or more
     reasons from the closed 7-item taxonomy frozen in Phase 1 (`judge-finetune.md` §4). Resumable.
     `adjudicate/` shows the third annotator **only** the disagreements.
   - **`books/`** — lists approved books with provenance stripped and order shuffled per validator, opening the
     existing book renderer. Objective 3's responses stay on paper: the instrument is open-ended prose, not a
     form (`docs/capstone/research_instruments.md` §Tool B).

2. **One new table, `annotations`** — `(pair_id, annotator_id, same_character, failure_reasons[], created_at)`.
   RLS scopes reads so **an annotator cannot see another annotator's rows**, which puts independent labelling
   under a database policy instead of under a promise. The adjudicator role reads all. This **supersedes** the
   `labels/*.csv` mechanism in `judge-finetune.md` §5; `build_dataset.py` reads the table instead.

3. **Blinding is enforced in code, not by discipline.** Opaque item IDs and shuffled order on both `annotate/`
   and `books/` (`research_instruments.md` §Blinding; `methodology.md` §Reproducibility of stimuli). Neither
   surface ever renders a model prediction next to a pair a human is about to label — that would contaminate
   the reference labels Objective 4 is measured against.

4. **No metrics dashboard.** Tool A is a **script over tracing exports**, specified in
   `docs/specs/functional-verification-matrix.md`. MASTER_SPEC §4 already commits the eval harness to "offline
   scripts + tracing exports" and CC-5 already requires traces to carry generation time, regen count, cost, and
   VLM score — so the data layer exists and only the spec was missing. **No `run_events` table is added.**

**Consequences:**
- The research track gains exactly two screens and one table. Identity, RLS, and the component library are
  inherited from Phase 2 rather than built for an audience of five.
- `judge-finetune.md` §5's `labels/` directory is now historical; the spec is updated in the same change.
- Objective 4's labels become durable, queryable, and access-controlled. Adjudication and inter-annotator
  agreement become queries rather than a spreadsheet merge — the failure mode this replaces (silent row
  misalignment across ~1500 rows) is undetectable after the fact and would invalidate the objective.
- **Consequences to build** (not this session): the `researcher` role in `auth-and-classroom`; the `annotations`
  migration + RLS; the two route groups; `build_dataset.py`'s new read path.
- MASTER_SPEC §7's Phase-3 spec index loses the stale `tier1-rating-harness` entry (Tier-1/Tier-2 vocabulary
  was retired with the Fun Toolkit) and gains `annotation-surface` and `functional-verification-matrix`.

**Alternatives:**
- **A static local HTML labeller + CSVs** — rejected, and it was the initial recommendation. It cannot mint
  signed URLs without embedding a Supabase client (at which point it is a worse web app with no session and no
  resumable state), and the alternative — bulk-downloading ~1500 child-derived images to a laptop — is
  precisely what the data-care rule forbids. The `phase_05.py` spike's `key.csv`/`scores.csv` pattern is right
  at 20 items and one rater; it does not survive 1500 items and three.
- **A full researcher app: metrics dashboard + per-run trace viewer + eval-run browser** — rejected on scope.
  The trace viewer duplicates LangSmith, already bought in ADR-014. The metrics dashboard renders a table that
  is read into the manuscript a handful of times.
- **Collecting Objectives 3 and 5 in-app** (interview form, ISO-25010 Likert) — rejected: three validators and
  a small evaluator pool, one sitting each, and Tool C additionally needs a pilot administration for CVI and
  Cronbach's α that a built form would not accelerate. Paper and forms export fine.
- **A `run_events` table for Tool A** — rejected: re-implements tracing the project already pays for, against
  MASTER_SPEC §4's stated harness design.
