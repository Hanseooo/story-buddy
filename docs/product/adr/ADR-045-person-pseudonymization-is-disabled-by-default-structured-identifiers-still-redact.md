# ADR-045 — Person pseudonymization is disabled by default; structured identifiers still redact

**Status:** Accepted (2026-09-01) · **amends
ADR-011 mechanism 2** · **supersedes ADR-041's rejected alternative "Disable or context-gate
Presidio for fictional names"** · no `StoryMemory`, pipeline-shape, provider, model, or
retry-policy change · Presidio stays installed and wired

**Context:**

`redact_pii` does two unrelated jobs behind one name. It **pseudonymizes** person spans
(`PERSON`, `PH_PERSON` → a pool name) and it **hard-redacts** structured identifiers
(`PH_MOBILE`, `PH_ADDRESS`, `PH_TIN`, `PH_SSS`, `PH_PHILHEALTH`, `EMAIL_ADDRESS`,
`PHONE_NUMBER`, and the rest of `_IDENTIFIER_ENTITIES` in `providers.py:539`).

Every recorded production and corpus failure attributable to this function is a **person**
failure. None is an identifier failure:

| Observation | Effect |
|---|---|
| 16 of the 30 synthetic corpus records lost a declared name (`build_corpus.py:189`) | `declared_characters` no longer reconciles against the extracted roster |
| `Grace` tagged `PERSON` once and `ORGANIZATION` twice in one story | One child's character split into `Ana`, `Ben` *and* `Grace` |
| `bush` tagged `PERSON` at 0.85 after an article (prod, 2026-08-13) | A character named `Cielo` appeared in a caption |
| `Bolt` → `Leo` (ADR-041) | A robot drew with a human face; the pseudonym was a human-coded visual prior |

Three defensive mechanisms already exist solely to contain this one behaviour —
`_missed_mentions`, `_after_determiner`, `_story_rng` — and the failures continued anyway. The
research corpus resolved it by bypassing the rewrite outright (`307dd51`, `e76961d`,
`IntakeRecord.pii_already_handled` → `Input.synthetic_no_pii`). The product path never got the
same treatment.

The identifier half has caused zero recorded incidents. A phone number is not narrative, so
replacing it with `<PH_MOBILE>` cannot corrupt a story the way a renamed protagonist does. It is
also the half a data-privacy examiner will ask about: without it a real mobile number in a child's
story reaches OpenRouter, reaches fal.ai, and is written into the caption and the exported PDF.

The two halves therefore have opposite cost/benefit and should not share one switch.

**On the disclosure question.** The Stage-1 consent and assent forms
(`docs/capstone/story_donation_consent_and_assent_draft.md:19,31`) promise **manual** redaction by
the research team. They do not mention Presidio or any automated redaction. Turning off person
pseudonymization therefore contradicts no statement made to a guardian or a child. What it
contradicts is internal documentation — `ethics_and_safety.md` §1, `MASTER_SPEC` CC-2, ADR-011
mechanism 2 — which this ADR's implementation updates in the same change.

**What this does not claim.** ADR-011 mechanism 2 exists for a real risk: a child narrating real
life and writing their own name is the expected case, not the exception. This ADR accepts that a
first name may now flow to providers and into exports, and judges that risk lower than the
recorded, repeated corruption of the narrative the product exists to preserve. `input-gate-hardening.md`
§4c's argument still stands and is the reason this is a *switch* rather than a deletion: Presidio
cannot tell *"my name is Mia"* from a character called Mia, so there is no context gate to build —
the only choices are all-names or no-names.

**Decision:**

1. A new setting `pii_pseudonymize_persons: bool = False` in `backend/app/config.py`, env-overridable
   as `PII_PSEUDONYMIZE_PERSONS`. Default **off**.
2. When off, `redact_pii` drops `_PERSON_ENTITIES` from the entity filter and returns text with
   person spans untouched. `_missed_mentions`, `_after_determiner`, `_pseudonymizer` and `_story_rng`
   are not called and not deleted — they are the implementation of the on-path.
3. Structured-identifier hard-redaction is **unconditional**. `_IDENTIFIER_ENTITIES` is not behind
   the flag and there is no setting that disables it. Restoring the flagged-off behaviour for
   identifiers requires a superseding ADR.
4. Presidio, `en_core_web_sm`, and `ph_recognizers.py` stay installed, wired, and tested. The flag
   changes which entity types are acted on, nothing else. The `PH_PERSON` recognizer keeps firing
   and keeps being logged (Decision 6); only the rewrite is suppressed.
5. Moderation is untouched. `input_gate` runs both text classifiers on the raw text regardless
   (`input_gate.py:12`), and the char-ref / output image gates are unaffected. The CC-1 ordering
   guarantee is unchanged.
6. The existing `pii_redaction entity_counts=... ignored=...` log line keeps reporting **detected**
   person counts even when the rewrite is off, so the decision stays measurable. A separate
   `pseudonymize=off` field records the flag state. Values are never logged (ADR-025 D5, unchanged).
7. The corpus path is unchanged. `Input.synthetic_no_pii` already skips the whole rewrite for both
   synthetic and hand-redacted donated intake, which is strictly stronger than this flag on the
   person axis. That path passed its 30/30 roster preflight in its current form and is not modified
   during a live campaign. Product and corpus now agree that person spans are not rewritten.
8. `contracts/` is untouched. No schema version change, no migration, no checkpoint invalidation.

**Consequences:**

- A child's real first name, if written, now reaches the analyzer, the segmenter, the image
  providers, the stored captions, and the exported PDF. This is the accepted cost and it is stated
  in the ethics chapter, not hidden.
- Character rosters stop drifting between `declared_characters` and extracted characters on the
  product path, and pseudonyms stop acting as human-coded visual priors (the ADR-041 mechanism).
- Stories become reproducible across a re-queued job without depending on `_story_rng`'s hash
  seeding, because there is no name substitution to reproduce.
- Three docs become stale on merge and are corrected in the same change: `ethics_and_safety.md` §1,
  `MASTER_SPEC` CC-2 and the moderation row, `input-gate-hardening.md` §4c.
  `RESEARCH_PROTOCOL.md` §8 is already correct — it describes manual redaction and never claimed
  the automated stack covered the corpus.
- `docs/capstone/design_decisions_and_risks.md` gains this as a named, defended trade-off rather
  than an undocumented gap.
- Reverting is one env var. `PII_PSEUDONYMIZE_PERSONS=true` restores the pre-ADR behaviour exactly,
  with no code change and no data migration.

**Alternatives:**

- **Delete Presidio entirely.** Rejected. Identifier redaction is the half that works, costs
  nothing, and is the half an examiner asks about. Deleting it also discards `ph_recognizers.py`,
  which is capstone-visible original work.
- **One flag that disables all redaction.** Rejected. It buys nothing beyond this decision and makes
  the honest ADR sentence "a child's phone number now reaches three third-party providers and the
  PDF."
- **Context-gate person redaction** (keep it for self-disclosure, skip it for fictional names).
  Rejected, per `input-gate-hardening.md` §4c: no such classifier is reliable, and it fails in the
  unsafe direction — one missed disclosure sends a real name downstream anyway, so the cost is paid
  without the benefit.
- **Keep pseudonymization and fix the false positives.** Rejected. Three containment mechanisms
  already exist for exactly this and the failures continued; the remaining ones are spaCy NER
  errors, not logic errors we control.
- **Default the flag on, opt out per deployment.** Rejected. The default is what the capstone
  demonstrates and what the corpus was generated against; a default nobody runs is a default that
  is never tested.

**Escape hatch:** Making identifier redaction optional, removing Presidio from the dependency set,
or restoring person pseudonymization as the default each requires a superseding ADR and owner
acceptance before implementation.
