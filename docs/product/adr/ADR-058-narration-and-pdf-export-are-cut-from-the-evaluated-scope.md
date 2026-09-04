# ADR-058 — Narration and PDF export are cut from the evaluated scope

**Status:** Accepted (2026-09-04) · **supersedes ADR-020** ·
**retires the export half of ADR-013** (its caption decision is untouched) · **narrows CC-6**
(`MASTER_SPEC.md:264`) · **invokes `ROADMAP.md:372` de-scope rung 3** · **narrows the Tool A
"Picture book production" row** (`functional-verification-matrix.md:65`) · **does not amend
ADR-027, ADR-017, or ADR-011** · no migration, no provider change, no pipeline-shape change

## Context

Narration and PDF export are promised in the PRD, the roadmap, the master spec, the public terms
and privacy pages, the methodology, and the Tool A verification matrix. **Neither exists.**
`providers.narrate()` was never written, there is no PDF renderer in `backend/pyproject.toml`, and
`export` was never built as a pipeline node. The 2026-08-24 ISO/IEC 25010 readiness audit
classified both as "required but not demonstrated" and refused to score functional suitability
until the project decided which way they go.

Two things force the decision now rather than later.

**The Objective 5 instrument names them by name.** `research_instruments.md:94` and
`methodology.md:416` both read: *"Does the system do what it claims — analyze, segment, illustrate,
narrate, export?"* That item cannot go to content validation, pilot, or administration while it
asks evaluators to rate capabilities that do not ship, and relabelling after collection is not
available.

**The public policy pages were asserting them as fact.** `terms/page.tsx` told families a book
"can be downloaded as a PDF"; `privacy/page.tsx` disclosed a data flow to a named third-party TTS
host that never happens. Corrected ahead of this ADR (#71), because a consent-relevant document
should not wait on an architectural decision.

### What the project already decided about cutting narration

`DECISION_BACKLOG.md:440-444` considered deferring narration and **rejected it as a free win**,
permitting it only on one condition:

> Deferring it narrows a reported evaluation row and drops an accessibility claim — a documented
> cost, not a free win. **Defer only as a deliberate trade, with the Tool A row narrowed in the
> same change.**

This ADR is that deliberate trade. D4 is the condition, and it is not a follow-up.

### PDF export is already pre-authorised

`ROADMAP.md:372` carries rung 3 of the de-scope ladder: *"PDF export — the out-of-container escape
hatch; slideshow still works."* Cutting it invokes an existing decision rather than making a new
one.

## Decision

1. **PDF export is cut**, invoking `ROADMAP.md:372` rung 3. This retires **only the export half**
   of ADR-013. ADR-013's caption decision — the child's verbatim post-redaction text, never
   LLM-rewritten — is an independent decision on the same page and **survives untouched**.
   ADR-013 is not edited in place.
2. **Narration is cut.** ADR-020 is superseded in full: no Chatterbox, no Kokoro fallback, no
   `providers.narrate()`, no audio in Storage.
3. **CC-6 (Accessibility) is narrowed, not retired.** It becomes *"large targets; minimal text"*.
   The project keeps an accessibility concern; it loses the mechanism that was its main content.
4. **The Tool A row narrows in the same change.**
   `functional-verification-matrix.md:65`'s "Picture book production" category becomes `Compose`
   alone, and its success criterion becomes *"Scenes assembled as a complete book."* The category
   is not deleted.
5. **`NarrationEntry` and `StoryMemory.narration` are removed** from
   `backend/contracts/story_memory.py`. Verified 2026-09-04: the field is declared at `:267` and
   read or written **nowhere** in `backend/` — it is an orphan, not a live contract slice, so this
   is a deletion rather than a contract migration.

## Consequences

- **The accessibility surface is smaller, and this ADR is where that is recorded.** A Grade 5–6
  reading product ships with no read-aloud. This is a real cost to children who read below grade
  level, and it is the reason `DECISION_BACKLOG.md:440` refused to treat the cut as free.
- **A reported evaluation row narrows.** D4 touches Objectives 1–2, not only Objective 5. Tool A
  produces the functional-verification success rates, so the criterion must change *before* any
  run — a rate reported against "assembled + narrated + exported" would be measuring a product
  that was never built.
- **One third-party data flow never opens.** ADR-020 §Consequences flagged "one honest new data
  flow": the child's redacted text travelling to a TTS host. That boundary now stays closed. This
  is a genuine improvement, and it is **not** a reason to strengthen any privacy claim — ADR-015's
  position that no privacy guarantee is claimed is unchanged.
- **Narration's metered cost leaves the model.** `PRD_v2.md:517` and `TECH_STACK.md:220` lose the
  ~cents/book TTS line. Image generation remains the whole variable cost.
- **ADR-020's English-only limitation is moot**, not solved. No Taglish narration existed to lose.
- **ADR-027 is untouched.** It specified on-demand PDF generation with no stored PDF, so there was
  never a stored-PDF control to remove — and none may be invented to test one.
- **The teacher gate is unchanged** (ADR-017). Only the "or is exported" clause leaves its wording;
  the approval requirement itself is untouched.
- **Reversal cost is low and rises with time.** Nothing was built, so nothing is thrown away.
  Reinstating either feature means a new ADR plus re-widening the Tool A row — cheap now,
  expensive once Tool A has been run and reported.

## Alternatives

- **Build ADR-020 as written** (Chatterbox on fal.ai, MP3 per page behind signed URLs). Honours
  the accepted decision and delivers expressive prosody. Rejected: it is a backend build plus
  metered cost, sequenced ahead of Objective 4's unfinished corpus campaign, on a project whose
  research critical path is already the constraint.
- **Browser-native `speechSynthesis`.** ~15 lines, no dependency, no cost, and no new trust
  boundary — the text never leaves the device, which is strictly better than D2's alternative on
  privacy. Prosody is flat, i.e. exactly the tradeoff ADR-020 already accepted when it kept
  Kokoro as its fallback. It would have satisfied CC-6 in full. **Rejected by the owner on
  2026-09-04** in favour of a clean cut. Recorded here so it is not re-derived as a discovery.
- **Keep promising both and build them later.** Rejected: the Objective 5 instrument cannot be
  content-validated while it names unshipped features, and the promise is currently live in
  consent-relevant public text.
- **De-scope export only, keep narration.** Rejected: it leaves CC-6 pointing at an unbuilt
  mechanism, which is the state the audit flagged in the first place.
