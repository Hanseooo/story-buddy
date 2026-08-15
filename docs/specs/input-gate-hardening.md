# Feature Spec — input-gate-hardening

**Status:** draft · **Phase:** 2 · **Owner:** `backend/app/length.py`, `backend/app/main.py`,
`backend/ph_recognizers.py`, `backend/providers.py` (`redact_pii`, `_presidio`)
**Derived from:** MASTER_SPEC §7 · **Rationale:** ADR-011 (mech. 2), ADR-012, ADR-025
**Supersedes:** the `filipino-pii-recognizers` stub spec (deleted; git keeps it)

> **This spec is not a node.** It hardens the two things that must be true of a story's text
> *before* the first graph node runs: it is a sane length, and its PII is gone. Both were deferred
> to Phase 2 by four Phase-1 specs. One spec because both live at the same seam and neither
> touches `graph.py` or `contracts/`.
>
> Closes two `DECISION_BACKLOG` rows: `length-guard` and `filipino-pii-recognizers`.

## 1. Purpose

Two guarantees, both owed to earlier specs:

1. **Length.** ADR-012's word cap, enforced at the API boundary with truncate-at-boundary and no
   summarization — plus the **minimum**-length gate that `story-analyzer` (§4 edge table),
   `scene-segmentation` (§4 edge table), and `compose` (§4 edge table) each explicitly handed to
   `length-guard` by name. The floor closes a *currently reachable* crash: empty or whitespace-only
   input produces zero scenes and `compose` raises.
2. **PII.** ADR-011 mech. 2 names the stock Presidio configuration as a known leak, with
   *"Ako si Juan dela Cruz, taga Purok 3, Barangay San Isidro"* as the expected case it misses. This
   spec ships the custom Filipino recognizers that close it and deletes
   `providers.py`'s `# ponytail: stock Presidio, Filipino names leak` comment.

Non-goals: the N=3 repeated-failure off-ramp (→ `self-refusal-fallback`, see §8), the kid-facing
copy for either guard (→ `kid-flow-ui`), and any change to moderation classification.

## 2. Contract slice (Story Memory — MASTER_SPEC §3)

**`contracts/` is untouched.** `Input` already reserves both fields this spec needs
(`story_memory.py:82-83`); nothing writes them today. This spec activates them.

- **Reads:** `jobs.input_text`, `jobs.truncated` (new column)
- **Writes:** `Input.word_count`, `Input.truncated` — populated by `run_job.py` from the row,
  before `graph.invoke`
- **Writes (unchanged shape):** `Input.redacted_text`, via `input_gate`'s existing call to
  `providers.redact_pii`

**Invariants:**
- Every `jobs` row reaching the queue satisfies `MIN_STORY_WORDS <= word_count <= MAX_STORY_WORDS`.
  Enforced at the trust boundary; no node re-checks.
- `jobs.input_text` stores the **already-clamped** text. The discarded tail is never written to the
  database, never sent to a provider, and is not recoverable — deliberate (see §5, CC-4).
- `redact_pii` is **total**: it returns a string for any input, and no detected entity's original
  value appears in its output.
- **`input_gate` writes `input` with `model_copy`, never a fresh `Input(...)`.** `input` has no
  reducer, so the node's partial return replaces the model outright and any field it does not
  restate reverts to its pydantic default. **Violated in production until 2026-08-11** — all four
  return paths built a fresh `Input`, so `word_count` was 0 and `truncated` was False for every
  job the pipeline had ever run. Nothing downstream reads either field yet, which is exactly why
  it survived: this spec activated the fields and the activation was silently undone one node
  later. Guarded by `tests.state_invariants.assert_no_fields_dropped`, parametrized over all four
  paths in `test_input_gate_node.py`.

## 3. Position in the system map

```
POST /storybooks
  ├─ reject  (word_count < MIN)          → 422, no job row, nothing queued
  └─ clamp   (word_count > MAX)          → jobs.input_text = clamped, jobs.truncated = true
                                              │
                                    enqueue → run_job.py
                                              │  Input(raw_text=<final>, word_count, truncated)
                                              ▼
                                          input_gate ──► redact_pii  ← recognizers land here
                                              │
                                              ▼  (unchanged from moderation-stack)
                                           analyze → ...
```

No new node, no new edge, no conditional routing. This satisfies `moderation-stack` §4a's standing
promise literally: *"`length-guard` truncates before `input_gate` runs; `input_gate` always sees the
final text."*

## 4. Behavior & edge cases

### 4a. `clamp_story` — `backend/app/length.py`

Constants live in `app/config.py` beside `MAX_SCENES`:

```python
MIN_STORY_WORDS = 5     # a book needs at least one scene's worth of text
MAX_STORY_WORDS = 300   # ADR-037 amends ADR-012's 500–800 range: length buys retries
```

```python
_WORD = re.compile(r"\S+")

def clamp_story(text: str) -> tuple[str, bool]:
    """Returns (final_text, truncated). Never raises; the floor is main.py's job."""
    text = text.replace("\r\n", "\n")
    spans = list(_WORD.finditer(text))
    if len(spans) <= MAX_STORY_WORDS:
        return text, False

    head = text[: spans[MAX_STORY_WORDS - 1].end()]   # slice the ORIGINAL string
    floor = MAX_STORY_WORDS // 2
    for cut in (_last_paragraph(head), _last_sentence(head)):
        if cut is not None and len(_WORD.findall(cut)) >= floor:
            return cut.rstrip(), True
    return head.rstrip(), True
```

`_last_paragraph` → text before the final `\n\s*\n`, else `None`.
`_last_sentence` → text through the final `[.!?]` followed by whitespace or end, else `None`.

Three details that are load-bearing, not style:

- **Slice the original string, not `" ".join(words[:cap])`.** Rejoining tokens destroys the very
  `\n\n` the paragraph rule then looks for. `finditer` gives the character offset directly.
- **The `floor` guard.** Without it, a story whose only blank line sits at word 10 truncates to 10
  words. A boundary cut is only taken if it keeps at least half the cap; otherwise fall through.
- **CRLF normalization first.** The API is reachable outside the browser; `\r\n\r\n` matches no
  `\n\n`.

| Edge case | Behavior |
|---|---|
| Empty / whitespace-only | 0 words → 422 at the API. Closes `compose` §4's reachable zero-scene raise. |
| Exactly `MIN` / exactly `MAX` words | Accepted; no truncation at `MAX`. Bounds are inclusive. |
| Under the cap | Returned unchanged, `truncated=False`. No allocation beyond the span scan. |
| No punctuation and no blank lines (one run-on) | Both boundary rules return `None` → hard cut at the `MAX`-th word. Knowingly blunt. |
| Single `\n` between paragraphs, no punctuation | Falls to the hard cut. Accepted: a lone newline is a line break, not a scene break, and adding a third tier for it is not worth the branch. |
| Punctuation inside the text (`Mr.`, `3.14`) | May cut early by one sentence. Harmless — the `floor` guard bounds the loss. |
| Text is one 900-word paragraph ending in `.` | `_last_paragraph` → `None`; `_last_sentence` → the final period before the cap. Correct. |

### 4b. Filipino recognizers — `backend/ph_recognizers.py`

A new module holding the name lists and one `ph_recognizers() -> list[EntityRecognizer]` factory.
`providers._presidio` registers them into the existing `AnalyzerEngine`. **No new dependency** —
`presidio-analyzer` is already in `pyproject.toml`.

| Entity | Mechanism |
|---|---|
| `PH_PERSON` | deny-list (PSA surnames + common given names) **+** Tagalog personal-name-marker patterns |
| `PH_MOBILE` | `+63 9xx` / `09xx`, spaced, dashed, or bare |
| `PH_ADDRESS` | `Barangay` / `Brgy.` / `Purok` / `Sitio` + the following token |
| `PH_TIN`, `PH_SSS`, `PH_PHILHEALTH` | fixed-format regex |

**The marker patterns are the point of this spec.** Tagalog marks personal names grammatically —
`si` / `ni` / `kay` / `sina` / `nina` / `kina` — a signal English NER structurally cannot see. It
catches names in no gazetteer, which is exactly ADR-011's expected-miss case.

Three implementation traps that must not be discovered in review:

- **Presidio spans the whole regex match, not a capture group.** A naive
  `r"\b(?:si|ni)\s+([A-ZÑ]\w+)"` redacts `"si Maria"` including the marker, corrupting the sentence.
  Use an alternation of **fixed-width lookbehinds** (Python `re` permits these individually, but not
  one variable-width lookbehind): `(?:(?<=\bsi )|(?<=\bni )|(?<=\bkay )|(?<=\bsina )|(?<=\bnina )|(?<=\bkina ))[A-ZÑ][\w'-]+`
- **Diacritics.** `[A-Z]` misses `Ñ` (Niño, Peña). Character classes are explicit about it.
- **Multi-token names with particles.** `dela`, `de`, `del`, `delos`, `delas`, `San`, `Santa` join a
  name; the pattern extends through up to two following tokens that are capitalized or in the
  particle set, so *"Juan dela Cruz"* is one span rather than a redacted `Juan` beside a bare
  `dela Cruz`.

**False-positive control.** The marker rule over-fires on two real constructions, and a `MARKER_EXCEPTIONS`
set suppresses them:

- **Kinship terms**, routinely capitalized in Filipino writing: `Lolo`, `Lola`, `Nanay`, `Tatay`,
  `Ate`, `Kuya`, `Ninong`, `Ninang`. *"si Lolo"* is "grandpa", not a name.
- **`kay` as an intensifier**, not the dative marker: *"kay ganda ng araw"* is "how beautiful the day
  is". The capitalization requirement already blocks the common lowercase form; the exception set
  covers the sentence-initial case.

The deny-list is similarly curated: Filipino surnames that are also common English or Tagalog nouns
(`Cruz`, `Luna`, `Rosa`, `Angel`, `Flores`, `Mercado`) are **excluded** from the deny-list and left to
the marker rule, which has the grammatical context the bare list lacks.

| Edge case | Behavior |
|---|---|
| Built-in `PERSON` / `PHONE_NUMBER` overlaps a `PH_*` span | Presidio's analyzer keeps the highest-confidence result per span. Both map to the same operator, so the output is identical either way. |
| Taglish sentence | Analyzed as `language="en"` — the recognizers are regex and deny-list, not NLP-engine-bound, so they fire regardless of the sentence's dominant language. |
| A name that is also a deny-list *and* marker hit | One span, one replacement. |
| Text with no PII | Returned unchanged. |

### 4c. `redact_pii` — consistent pseudonyms for persons

`analyze.py:105` and `segment.py:141` both build the story from `redacted_text`. Redaction output
**is** the narrative. Replacing a protagonist with `<PH_PERSON>` mints a character roster of
placeholders and captions that read as redaction artifacts — and it cuts against ADR-012's own
rationale, that the book must reflect the child's narrative.

So person entities are **pseudonymized, not placeholdered**: each distinct detected name maps to a
stable stand-in for the duration of the call.

```python
redact_pii("Si Maria ay pumunta sa bukid. Tinawag ni Maria si Juan.")
       →  "Si Ariel ay pumunta sa bukid. Tinawag ni Ariel si Alex."
```

**Amended 2026-08-13 — pool is bucketed by inferred gender.** Assignment used to be positional
(`pool[n % len(pool)]`), which gave a boy a girl's stand-in while the surrounding pronouns kept
saying *he*. Since `redacted_text` is what the analyzer, the character reference, and every scene
prompt read, a name that contradicts its pronouns is a consistency defect and not a cosmetic one.
`_infer_gender` now votes on the nearest pronoun after each mention (`they/them/it` are not
evidence — plural or non-discriminating antecedents), and the mapping draws from a feminine,
masculine, or neutral pool. The example above has no English pronoun, so both names land neutral.
Measured on the donated sample stories: 4 correct, 0 misgendered, 3 abstentions to neutral. It
fails by abstaining, which is the only direction that cannot rename a child's girl into a boy.

**Amended 2026-08-13 — the pool is shuffled per story, seeded from the story.** Ordered selection
made the first girl in every book Ana. `_story_rng` seeds a `random.Random` with a SHA-256 of the
text, so names vary between stories while the *same* text always redacts identically. That
stability is the point, not a side effect: `input_gate` does not normally re-run (a resume enters
at the interrupt point, `run_job.py:228`), but `build_graph` falls back to an in-memory
checkpointer (`graph.py:127`), and a clock-seeded shuffle would rename every character on a
re-queued job while the images already in storage kept the old names. It also keeps the test suite
deterministic. **`hashlib`, not `hash()`** — `str.__hash__` is salted by `PYTHONHASHSEED`, so
`hash()` would vary per worker process and still pass every test on a single machine;
`test_redact_pii_seed_survives_process_hash_randomization` pins one output against that
substitution.

The real name never reaches storage, export, or any provider; the story survives with a protagonist
an illustrator can actually draw. It also **inverts the cost of a marker false positive** — an
over-eager match yields a wrong name, not a hole in the child's book, which is what makes the
aggressive marker rule safe to ship.

Structured identifiers are **not** pseudonymized — `PH_TIN`, `PH_SSS`, `PH_PHILHEALTH`, `PH_MOBILE`,
`PH_ADDRESS` all hard-redact to `<ENTITY>` placeholders. A plausible-looking fake TIN is worse than
an obvious hole.

**Everything else is left alone (amended 2026-08-11).** As first written this section passed every
Presidio result to the anonymizer, so spaCy's free-text NER categories — `ORGANIZATION`,
`LOCATION`, `DATE_TIME`, `NRP` — hit the default operator and became placeholders too. That
contradicts this section's own premise. Prod job `e94cc400` opened with the title *"The Lost Little
Star"*; spaCy called it an `ORGANIZATION`, and `<ORGANIZATION> upon a time` was written into a book
caption. The same run turned *"Manila"* into `<LOCATION>`.

The set is therefore an **allowlist**, not a denylist: an entity type is redacted only if it is a
person (pseudonymize) or a structured identifier (hard-redact). A Presidio upgrade that ships a new
free-text recognizer must not silently start eating captions; a new *identifier* recognizer has to
be added to `_IDENTIFIER_ENTITIES` explicitly, which is the safe direction to fail because an
unlisted identifier is caught by §2's totality test.

Generic `LOCATION` is narrative, not identity — the structured Philippine address form
(`Barangay`/`Purok`/`Sitio`, §4b) is what `PH_ADDRESS` exists to catch, and it still hard-redacts.

```python
def redact_pii(text: str) -> str:
    analyzer, anonymizer = _presidio()
    detected = analyzer.analyze(text=text, language="en")
    results = [r for r in detected if r.entity_type in _REDACTED_ENTITIES]
    person = OperatorConfig("custom", {"lambda": _pseudonymizer()})   # fresh mapping per call
    return anonymizer.anonymize(
        text=text, analyzer_results=results,
        operators={"PERSON": person, "PH_PERSON": person},
    ).text
```

`_pseudonymizer()` returns a closure over a fresh `dict`, keyed on the casefolded surface form,
assigning from a fixed pool in first-appearance order.

**`_presidio()` gains `@lru_cache(maxsize=1)`.** It currently constructs an `AnalyzerEngine` and
loads `en_core_web_sm` on *every* `redact_pii` call. One decorator, and it is squarely in this
spec's blast radius. The pseudonym mapping is built in `redact_pii`, **not** inside the cached
factory — caching the mapping would leak names between stories.

| Edge case | Behavior |
|---|---|
| More distinct names than the pool holds | **Amended 2026-08-13.** Was: pool wraps by modulo, two characters may share a stand-in. It shipped, and `"Robert watched Michael"` became `"Ana watched Ana"` — a silent rewrite of who did what, which the 3-character roster cap does not bound because the cap is applied *after* redaction. Now: first unused name from the gendered pool, then the neutral pool, then a numbered suffix. Never merges. |
| A stand-in collides with a real name in the same story | Excluded, by prefix containment in either direction — so a story about *Analyn* also cannot gain an *Ana*. |
| Two stand-ins are confusingly similar | Excluded by the same rule. `Alex` and `Alexis` are both in the neutral pool; ordered selection could never pick both, a shuffle can, and character binding matches by name. `Ana`/`Anna` still slips through — edit distance would catch it, and is not worth a dependency for a pair no donated story has produced. |
| Same story submitted twice | Identical names. The shuffle is seeded from the text. |
| One name detected at some mentions but not others | All occurrences replaced. spaCy tagged `"Grace"` `PERSON` once and `ORGANIZATION` twice in one donated story, so two thirds of her mentions survived and the book gained a third character. Case-sensitive, so the noun *grace* is untouched. |
| NER tags a common noun as a person | Dropped when preceded by `a`/`an`/`the`. spaCy scored `"bush"` `PERSON` at 0.85 in `"from behind a bush"`. Chosen over a title-case test, which caught the same false positive but also dropped genuinely lowercase names (`"juan and sam"`) — a privacy regression this avoids. |
| `"Maria"` and `"Maria Santos"` in one story | Different surface forms → different stand-ins. Knowingly blunt; coreference is out of scope. |
| Zero person entities | Operator never fires; no mapping allocated. |
| Same name in two different stories | Different calls, different mappings — no cross-story stability, and none is wanted. |
| A place, org, date or nationality is detected | Not in `_REDACTED_ENTITIES` → passes through untouched. Logged under `ignored=` so a real identifier landing there is visible. |
| Presidio ships a new recognizer | Free-text: ignored by default, prose is safe. Identifier: must be added to `_IDENTIFIER_ENTITIES`, and §2's totality test fails until it is. |

### 4d. API and frontend

**`POST /storybooks`** gains a validator and a clamp:

- `word_count < MIN_STORY_WORDS` → **HTTP 422**, no `jobs` row inserted, nothing enqueued.
- `word_count > MAX_STORY_WORDS` → clamp; insert the clamped text with `truncated = true`.

**Migration `000N_jobs_truncated.sql`** — `truncated boolean not null default false`. **Number is
"next free at merge time", not hard-coded:** `DECISION_BACKLOG` already earmarks `0003` for
`job-failure-reason`, and whichever lands first takes it.

**`frontend/app/write/page.tsx`** gains a derived word counter — no new state, ~4 lines — plus a fix
this spec is obliged to make because it introduces the 422: the handler currently does
`router.push(\`/process/${data.job_id}\`)` unconditionally, so a non-2xx response navigates to
`/process/undefined`. It must branch on `res.ok`.

`kid-flow-ui` still owns the copy for both the 422 and the `jobs.truncated` *"let's make a book of
the first part"* message. This spec ships the column, the counter, and the status code.

> Per `frontend/AGENTS.md`, read the relevant guide under `node_modules/next/dist/docs/` before
> touching the frontend — this Next.js version diverges from training data.

## 5. Cross-cutting checklist (MASTER_SPEC §5)

- [x] **CC-1 Moderation ordering** — untouched and reinforced. The guard runs strictly before
  `input_gate`, so the gate still sees final text; recognizers change *what* `redact_pii` finds,
  never *when* it runs.
- [x] **CC-2 PII redaction** — the spec's core. Persons pseudonymized, structured identifiers
  placeholdered, `redacted_text` remains what downstream nodes consume.
- [x] **CC-3 Cost control** — the floor prevents a job (and its image spend) being queued for a
  two-word input; the cap bounds the text `scene-segmentation` sees, upstream of `MAX_SCENES`.
- [x] **CC-4 Security** — 422 is a trust-boundary rejection *before* the insert. The truncated tail
  is never persisted, so over-length input reduces stored data rather than adding it. No signed URLs
  involved.
- [x] **CC-5 Observability** — log truncation events (`word_count` before/after) and **per-entity
  redaction counts**. **Never log a detected value** — that is the PII, and `run_job.py`'s raw
  `error` string is already dev-only for exactly this reason (ADR-025 D5).
- [x] **CC-6 Accessibility** — the word counter is announced, not colour-only: `aria-live="polite"`
  on the count, and the over-cap state carries text, not just a red border.
- [x] **CC-7 Reproducibility** — recognizers are regex and deny-list, fully deterministic. Pseudonym
  assignment is deterministic given detection order, which is itself deterministic. No seed coupling.
- [x] **CC-8 Kid vs parent design** — the counter is kid-facing; `kid-flow-ui` owns tone and copy.
- [x] **CC-9 Failure states = success states** — truncation is **not** a failure: the job proceeds
  and `jobs.truncated` drives a positive message. The only failure is the 422, which carries a
  reason. No new `failure_reason` value; nothing here reaches `run_job.py`'s except block.
- [x] **CC-10 Checkpointing** — nothing to checkpoint; the guard is pre-graph. A resumed job re-reads
  the already-clamped `jobs.input_text`, so truncation is idempotent by construction.

## 6. Deterministic tests (CI — MASTER_SPEC §6 Tier A)

**`tests/test_length.py`** — `clamp_story` is pure; no mocks.
- Under cap → returned unchanged, `truncated=False`.
- Exactly `MAX` → unchanged, `truncated=False`.
- Over cap with a blank line in range → cut at the paragraph, `truncated=True`.
- Over cap, no blank line, sentence punctuation present → cut at the last sentence end.
- Over cap, blank line at word 10 → **floor guard fires**, falls through to sentence/hard cut.
- Over cap, no punctuation and no blank lines → hard cut, exactly `MAX` words.
- `\r\n\r\n` input → treated as a paragraph break.
- Assert the paragraph path never runs on a rejoined string: a fixture whose `\n\n` survives.

**`tests/test_ph_recognizers.py`** — run against **real** Presidio (CPU-local, fast, no mock), over
`tests/fixtures/pii_cases.py`:
- `MUST_REDACT` — ADR-011's *"Ako si Juan dela Cruz, taga Purok 3, Barangay San Isidro"* is case #1;
  ~30 Filipino/Taglish cases asserting the expected entity set is found.
- `MUST_NOT_REDACT` — the false-positive guard: `"si Lolo ay masaya"`, `"kay ganda ng araw"`,
  `"ang cruz sa simbahan"`, plus benign Taglish with no PII. Asserts an empty entity set.
- Marker span excludes the marker: `"si Maria"` → the span is `Maria`, and `si` survives the redaction.
- `Ñ` name (`Niño`, `Peña`) is detected.
- Particle name `"Juan dela Cruz"` is **one** span.

**`tests/test_providers.py`** (extends existing)
- Same name twice → **same** stand-in both times.
- Two different names → two different stand-ins.
- Two separate calls → independent mappings (no leakage across stories).
- `PH_TIN` / `PH_MOBILE` → `<...>` placeholder, **not** a pseudonym.
- `_presidio` is cached: two `redact_pii` calls construct one `AnalyzerEngine`.
- No original value appears anywhere in the output (the §2 totality invariant).

**`tests/test_main.py`** (extends existing)
- 4-word body → 422, **no** row inserted, **no** enqueue (assert both mocks uncalled).
- 900-word body → 201, stored text is clamped, `truncated=True` persisted.
- Normal body → 201, `truncated=False`.

**`tests/test_run_job.py`** (extends existing)
- `Input.word_count` and `Input.truncated` are populated from the row before `graph.invoke`.

**`frontend/app/write/page.test.tsx`** (extends existing)
- Counter reflects typed text.
- Non-`ok` response does **not** navigate (the `/process/undefined` regression).

## 7. Eval / quality checks (MASTER_SPEC §6 Tier B)

The recognizers produce no subjective content, so there is no Tier-B corpus metric and this feeds no
RQ directly. The fixture set in §6 is instead the **release gate**: the
`# ponytail: stock Presidio, Filipino names leak` comment at `providers.py:159` may be deleted only
when `MUST_REDACT` and `MUST_NOT_REDACT` both pass green in CI. Both directions are required —
passing only `MUST_REDACT` buys recall by punching holes in children's stories.

`moderation-stack` §7's offline nightly run is the natural home for a larger corpus later; this spec
deliberately does not build a second harness.

## 8. Linked decisions & open questions

**Depends on:**
- **ADR-011 (mech. 2)** — names the stock-Presidio leak and supplies the canonical expected-miss case.
- **ADR-012** — the hard word cap, truncate-at-boundary, and the explicit no-summarization rule.
- **ADR-025 (D5)** — why the raw `error` string is dev-only; this spec extends the same
  never-log-PII discipline to redaction logging (CC-5).
- **`moderation-stack` §4a** — the standing promise that `input_gate` sees final text.

**Resolved here, previously ambiguous:**
- **ADR-012's *"truncate at a scene boundary"*** is unimplementable as written: the cap is enforced
  at the API, and segmentation runs several nodes later, so **no scene exists at truncation time**.
  Resolved as paragraph-then-sentence, which is the honest pre-segmentation proxy. ADR-012 is **not**
  amended — the decision (cap, truncate, never summarize) is intact; only its illustrative wording
  was ahead of the pipeline. Recorded here so the next reader does not re-derive it.
- **N=3 repeated-failure off-ramp ownership.** `ROADMAP.md:174` files it under the Length guard
  bullet; ADR-025 twice assigns it to `moderation-stack` / `self-refusal-fallback`; PRD §11.4 defines
  it as a *moderation*-failure counter across story revisions. `moderation-stack` shipped without it.
  Assigned to `self-refusal-fallback`, and the ROADMAP bullet corrected. It is not a length concern and
  nothing here implements it. **Superseded 2026-08-02:** split into its own backlog row,
  `repeated-failure-offramp` — it counts across *job submissions*, which needs a cross-run counter that
  does not exist, so it does not belong to a single-run spec. The ROADMAP correction did land, later.

**Open / handed off:**
- ✅ **Deny-list provenance — resolved 2026-08-02.** Shipped without the deny-list: `ph_recognizers.py`
  ships the Tagalog marker patterns (`si`/`ni`/`kay`/`sina`/`nina`/`kina`) and the structured-format
  recognizers (`PH_MOBILE`, `PH_ADDRESS`, `PH_TIN`, `PH_SSS`, `PH_PHILHEALTH`) only, per this
  section's own escape hatch — the marker patterns are §4b's "the point of this spec," and a PSA
  surname list is a licensable data artifact this capstone hasn't sourced. `PH_PERSON` is therefore
  marker-triggered only: a bare name with no `si`/`ni`/`kay`/... nearby and no built-in-Presidio
  match is not redacted. A licensed deny-list is a follow-up change, additive to
  `ph_recognizers.py` — no other file changes when it lands.
- ⚠️ **`kid-flow-ui` owes two surfaces:** the 422 message, and the `jobs.truncated` *"first part"*
  message. Additionally — a child may notice their protagonist was renamed. Whether to explain that
  is a kid-facing copy decision, and it is **`kid-flow-ui`'s**, not this spec's.
- **Migration number contention** with `job-failure-reason` (both want `0003`). Resolve at merge.
- **Deferred entities:** UMID, PRC license, and passport numbers appear in the deleted stub's
  question list but in neither ADR-011 nor the ROADMAP. Cut deliberately — each added pattern is a
  false-positive surface on a child's story, and nothing has asked for them. Add on evidence.
- **Coreference is out of scope.** `"Maria"` and `"Maria Santos"` receive different stand-ins.
  Revisit only if the fixture set shows it corrupting stories.
- **`MAX_STORY_WORDS = 300`.** This spec originally took 800, the top of ADR-012's 500–800 range,
  and said to lower it if quality fell off before the cap bit. **ADR-037 lowered it (2026-08-15)**,
  not on that evidence but as a deliberate trade: a shorter book funds a third corrected scene
  attempt inside a smaller image budget. Still tunable in `config.py`, but it is now one term of a
  coupled policy — see `spend-and-retry-economics.md` before moving it.
