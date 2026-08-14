# pipeline-consistency — session docket

> **Agent: read this before anything else.**
> This docket governs a multi-session design. You are working ONE session.
> - Do not widen scope past the current session's cluster, and do not
>   re-decompose it. If it should split, append an amendment — don't split it
>   in-session.
> - "Binding constraints" are decided. To challenge one, append a NEW session.
>   Never edit a DONE session.
> - Something real but outside this session's cluster: if it belongs to a later
>   session, add it to that session's open questions; otherwise one line under
>   `## Found & parked`. Never fix it. Never open a file or a tracker for it.
> - Stop at an approved spec. Do NOT continue to writing-plans or implementation.
> - To end the session, in this order: record the spec path, propose the
>   constraints it establishes, wait for the user to confirm them, write them in.
>   Only then set the session to DONE, and flip every session blocked on it to
>   READY. A session is not DONE until its constraints are confirmed.

**Goal:** raise output quality and consistency of the image pipeline, and make the raise
*measurable*. Five weeks of consistency fixes have landed on reasoning alone — `AGENTS.md`
carries the line "⚠️ **No job has been run against this code**" **five separate times**, on
`scene-setting-and-subject-binding`, `lettering-suppression`, `reference-moderation-retry`, the
`483056e0` hardening, and the reference-angle change. Each was individually well-argued. Together
they are an unmeasured stack, and the next change cannot tell whether it is fixing the pipeline or
one of them.

**Cut rationale:** clustered by which open questions constrain each other.

- **Measurement is not last.** It has no dependencies and everything downstream wants it, so it
  goes first and is the one session **built** before the others are specced. A baseline taken after
  four changes land measures nothing.
- **S2, S3 and S4 are the same question asked three times** — what does a page inherit, and from
  where — but they do not collapse into one session. S2 asks it about attributes the story never
  stated, S3 about a *view* the single reference cannot show, S4 about *place*, which has no
  reference artifact at all. Each has a different artifact class and a different cost shape; merging
  them lets the largest eat the other two.
- **Economics is genuinely last, not conventionally last.** `IMAGE_BUDGET = MAX_SCENES * 2 + 15`
  and `RECURSION_LIMIT = MAX_SCENES * 5 + 17`. The `* 2` and `* 5` are retry multipliers and the
  `+ 15` / `+ 17` are the prelude. S2, S3 and S4 can each add a term to that prelude (a second
  reference view is +3 draws per character; a location reference is a new artifact entirely), so
  fixing the page count first would fix a number whose formula three later sessions still change.
  Cutting 15 → 10-12 pages **funds** the extra retries; they are one currency, so they are one
  session.

**The trade being made, stated once so no session re-litigates it:** pages are being spent to buy
retries and reference coverage. A shorter book with pages that are right is the bet. S5 is where the
exchange rate is set; S2–S4 decide what there is to buy.

**Spec path convention:** `docs/specs/<topic>.md` — flat, beside the specs it sequences, per
AGENTS.md ("one canonical location per artifact type", no new folders). This docket lives at
`docs/specs/pipeline-consistency-docket.md` for the same reason, matching `kid-flow-ui-docket.md`
and `auth-and-classroom-docket.md`. The skill's default `docs/dockets/` would have been a new
top-level folder for one file.

**Workflow (confirmed with the user, 2026-08-14):** one session = one spec = one or more plans in
`docs/specs/plans/`. Plans are disposable and deleted once built + tests green + spec updated.
**Build timing is split:** S1's replacement spec was built and its targeted fixed-image rescore was
taken before S2. S2 was then waived because that work had already absorbed its chosen mechanism.
S3–S5 are all specced first, then built — so a later session amending an earlier one's open
questions is a text edit, not a refactor.

**Engine (writes the spec, exactly one per session):** `superpowers:brainstorming` — installed.
**Hardener (optional, after the engine, writes nothing):** `grilling` — installed. Run it on the
draft spec before the constraint extract, so constraints come off the final text.
`grill-with-docs` is not installed; skip it.

**Frozen decisions any session may hit.** Each is an ADR. Hitting one is not a blocker — it means
the session writes a new ADR and flags it, per AGENTS.md "Architecture is locked". Named here so
no session discovers them at implementation time:

| ADR | What it freezes | Which session is likely to hit it |
|---|---|---|
| ADR-010 | **one** corrected scene retry (`len(scene.attempts) >= 2` finalizes) | S5 |
| ADR-004 | ≤2 canonical references; reason-then-score field order on every judge call | S3, S4 |
| ADR-028 | `FailureReason` frozen at **7** values; `MAX_DRAWS = 3` | S3, S5 |
| ADR-003 | conditional edges ONLY at moderation pass/fail and consistency pass/fail | S2, S4 (any new node) |
| ADR-025 | D4 image-budget breaker; no partial book | S5 |
| ADR-019 | judge moves to self-hosted vLLM after Phase 2.5 | S1, S3 (judge model swap) |
| ADR-023 | `contracts/` is the only inter-module channel; additive fields declared LAST | S2, S3, S4 |

---

## Binding constraints

Decided in earlier sessions. Later sessions treat these as given, not open.

| # | Constraint | From |
|---|---|---|
| BC-1 | **No population-level consistency rate exists and none may be claimed.** Verification is per-observed-defect (`visual-continuity` §7), never corpus-level. A later session states pass/fail against a named, reproduced defect — never against a percentage. | S1 (paid baseline waived) |
| BC-2 | **Single rater by design.** Do not propose multi-rater workflows or inter-rater agreement inside this docket. | S1 |
| BC-3 | **The judge is the instrument, and its error bar is now named rather than unknown.** See *S1 outcome* below. Every number a later session reports inherits it. | S1 |
| BC-4 | **`settings.vlm_judge_model` is frozen for this docket.** Prompted `gemma-3-27b-it` is a pre-registered baseline — `judge-finetune.md` §7.3 calls it *the product gate*, and `PREREGISTRATION_OBJ4.md` was frozen 2026-08-14. Swapping it after seeing S1's results is a moved goalpost by that document's own definition. Judge calibration belongs to Objective 4, not to any session here. | S1 |
| BC-5 | **The verification harness is `backend/spikes/`, invoked by a human, never CI.** `backend/evals/` was considered and deliberately not created. Closes two of S1's open questions. | S1 |
| BC-6 | **A reworded judged prompt requires a version bump, and counts never cross versions.** | S1, ADR-034 |
| BC-7 | **S2 covers rostered characters only, including reference-capped `c2`.** Entities that `analyze` did not roster remain out of scope. | S2 |
| BC-8 | **`Character.description` is the sole persisted character canon.** `analyze` fills missing attributes once using the existing complete-profile floor; no source-provenance metadata is stored. | S2 |
| BC-9 | **An unreferenced character is checked against its frozen text canon on every page where it is visible.** Its first generated image never becomes a reference. | S2 |
| BC-10 | **Character canon remains style-independent.** ADR-035's transient projection is the only mechanism that removes style-conflicting rendering terms. | S2 |
| BC-11 | **S2 preserves the existing retry and failure semantics.** A concrete scene contradiction buys the existing single corrected redraw; judge failure ships unchecked; the second failed attempt uses existing best-of. S2 adds no node, provider call, retry, or budget term. | S2 |
| BC-12 | **S2 receives deterministic verification only.** No real-model run was taken, so it makes no measured visual-quality claim. | S2 |

---

## Sessions

Statuses: DONE (spec linked **and** constraints confirmed) · PARTIAL (stopped early,
resumable) · READY · BLOCKED (needs Sn) · WAIVED (owner explicitly removed the session's
deliverable; never treat it as measured)

### S1 · Verification contract — WAIVED (paid baseline waived by the owner; replacement spec shipped and verified)

**Replacement spec:** `docs/specs/visual-continuity.md`

**Outcome (2026-08-14).** WAIVED, never DONE — no baseline was taken, so nothing here may be
treated as measured in the population sense. What *was* taken is a targeted §7.1 rescore of the
three `sample-dataset/` scene pages against their two checked-in references, using
`backend/spikes/visual_continuity_7_1.py` and one rater's labels. ~20 judge calls, no fal spend.

What it established about the **incumbent prompted `gemma-3-27b-it` judge**:

- **Correct on gross identity substitution.** The Shadow Wizard renders as three different people
  across the three pages; `same_character=False` on every completed identity call, gating via
  `wrong_colour` / `wrong_body_feature` on all three. Zero false gates from the correctly-drawn
  subject. This is `visual-continuity` §1's failure 3, detected.
- **Prose and contradiction list agreed on every run.** The ADR-034 pattern — prose naming a defect
  the list then omits — did not reproduce at the scene judge.
- **The new object channel works.** The missing wooden sword was caught on both village pages; the
  duplicated crystal was caught under prompt v1.
- **It hallucinates attribute-level contradictions on a correct subject.** Ana drew contradictions
  on every page, including braided hair, a white sash and a beaded necklace, none of which are on
  the page. `SCENE_CONSTRAINT_PROMPT` was bumped v1 → v2 to exclude unstated detail; that moved the
  nitpick class out of the gating list but did **not** reduce the total, because the dominant cause
  is misperception, not prompting.
- **It is blind to movement direction.** The story ends "the wizard ran away"; both village pages
  show him moving toward Ana. Missed 4/4 across both prompt versions, despite
  `SCENE_CONSTRAINT_PROMPT` asking for movement direction explicitly.
- **Reliability is poor.** 3 of 6 identity calls failed in one run — one 120s timeout, two null
  responses — each degrading to `identity_available=False`.

Read this as **baseline characterization for Objective 4**, not as a defect list to fix here. The
gap it describes is the gap `judge-finetune.md` exists to close (BC-4).

**Cluster:** what "the pipeline got more consistent" means as a number; what corpus it is measured
over; what the current value of that number is; how a later change is attributed to itself rather
than to the four unmeasured changes underneath it.

**Explicitly out:** any change to the pipeline's behaviour. This session measures what exists. It
does not improve it, and a finding that something is broken goes to `## Found & parked` or to a
later session's open questions — not into a fix.

**Stance:** measurement session — done means a corpus, a metric per axis, and a **baseline number
already taken**, such that a later session can state a pass/fail against it in advance. Not a list
of things that would be worth measuring. The distinguishing test: if the spec ships and someone
cannot say "S3 succeeded" or "S3 failed" from it, the session is not done.

**Former open questions (resolved or waived by the S1 outcome and BC-1…BC-6; retained as planning history):**
- No eval harness exists. `backend/spikes/phase_05.py` is a one-off probe script and
  `spikes/out/` is its scratch. Does the harness live in `backend/evals/`, extend `spikes/`, or
  ride Langfuse (`settings.langfuse_*` are wired but nothing appears to emit traces)?
- MASTER_SPEC §6's bright line: the harness calls real models and must never enter CI. What
  invokes it, then — a human, a cron, a Northflank job?
- What is the corpus? Real prod stories are the only honest input and they are child-authored
  and PII-bearing. Are redacted prod stories usable as fixtures, or is a synthetic corpus written?
  How many stories is enough to move a rate?
- Metrics per axis. The judge already emits `same_character`, `anatomy_intact`, `text_free`,
  `subjects_unique`, `style_match` and a 7-value `failure_reasons`. Is the metric a pass rate over
  these, or something a human scores? **Single rater by design** — do not propose multi-rater
  workflows.
- **The judge is the instrument and it is uncalibrated.** ADR-034 exists because
  `matches_description` went TRUE on a verdict whose own prose read "This is a contradiction". Is
  judge–human agreement itself measured here? Without it, every downstream number inherits an
  unknown error bar, and S3's "use a better judge model" cannot be evaluated at all.
- Attribution across the five unmeasured changes: is a baseline taken at HEAD (measuring the
  stack as one), or is anything bisected?
- Cost. A baseline run over N stories draws N × (2 refs × up to 3 draws + pages × up to 2) fal
  images at real money. What is the ceiling, and does the harness support a dry/cached mode?
- `Cost.image_count` counts fal draws but **not** judge calls (CC-3, still open, widened to up to
  4 per scene). Does the harness need that closed to report cost per book?

---

### S2 · Attributes for characters with no reference — WAIVED (absorbed by `visual-continuity`)

**Canonical spec:** `docs/specs/visual-continuity.md`

**Outcome (2026-08-14).** The owner waived a separate S2 deliverable because the approved and built
`visual-continuity` spec already implements the chosen mechanism: `analyze` freezes a complete text
canon for every rostered character, `build_prompt` repeats that canon for visible characters without
a reference, and the scene-constraint judge checks it on every attempt. S2 added no behavior, code,
test, provider call, or standalone spec. BC-7…BC-12 record the decisions later sessions inherit.

**Cluster:** what a character who has no canonical reference image inherits from page to page, who
invents the attributes the story never stated, and where those attributes persist so page 7 renders
the same shirt as page 2.

**Explicitly out:** anything about *pose or view* (S3 owns it, including for these characters);
anything about place (S4); any change to the ≤2-reference cap or the draw budget (S5). Also out:
the reference-bearing characters' own attribute quality — that is `char_bible`'s existing ADR-028
loop and it is not this session's cluster.

**Stance:** provenance session — done means every attribute a page can render has a named origin
and exactly one place it persists, *including* the ones nobody stated. A finished answer says where
"blue shirt" comes from when the story never mentioned a shirt, and why page 7 renders the same one.

**Former open questions (resolved by the S2 outcome and BC-7…BC-12; retained as planning history):**
- **Which population?** Two exist and they are different problems: (i) `c2` — in the roster, real
  `CharacterDescription`, but capped out of `char_bible`'s 2-reference slot by ADR-004, so it draws
  through `text_to_image`; (ii) entities the story mentions that `analyze` never rostered at all
  (`analysis.characters[:3]`). Decide scope explicitly; (ii) is a much larger change.
- The hole is **not** that these characters get no attributes — `build_prompt` already emits
  `_describe(...)` for every present non-referenced character (`prompt_optimizer.py:290-294`). The
  hole is that `analyze`'s `EXTRACTION_PROMPT` says *"leave them empty rather than inventing
  details"*, so an undescribed character has nothing to be consistent **to**, and the image model
  invents fresh on every page.
- So: who invents? Candidates — (a) relax `analyze` to invent and persist; (b) a new gap-fill node
  between `segment` and the scene loop; (c) capture-from-first-draw: caption the first image the
  character appears in and write the observed attributes back as a de facto textual bible.
  (b) and (c) are new nodes → ADR-003 and ADR-024.
- Invented detail is asserted to a child as their own story. Is there a floor on what may be
  invented (`THIN_DESCRIPTION_FILLER` is the existing precedent — deliberately vague, asserts
  nothing the story could contradict)?
- **These characters have zero consistency signal today.** `consistency_check` judges each present
  character against the canonical reference it was drawn from — a character with no reference is
  never judged on identity at all. Does judging extend to them, comparing page N against the
  persisted text? Against page 1's image? Not at all?
- Contract shape: a new field on `Character`, or reuse `CharacterDescription` and distinguish
  stated-from-invented some other way? If the origin is not recorded, S1's metrics cannot separate
  "the story said blue" from "we said blue".
- Interaction with `filtered_description` / ADR-035: invented attributes must be generated already
  compatible with the style fragment, or they get filtered out at render and the persistence is a
  no-op.
- Cost: does gap-filling spend an LLM call, an image, or neither?

---

### S3 · Pose, viewpoint & scene prompt composition — READY

**Cluster:** what the scene prompt says about how a character is posed and from what angle, and
whether one canonical reference can serve every scene the story asks for.

**Explicitly out:** what the character looks like (S2 owns attributes); where the scene takes place
(S4); how many draws any of this costs (S5). Also out: the reference *framing* work already done —
`REFERENCE_PROMPT`'s slight-angle turn and `REFERENCE_NEGATIVE`'s crop terms are settled and
measured; this session may add views, not re-argue the default one.

**Stance:** instruction session — done means the pose axis has one chosen mechanism, one chosen
failure behaviour when a scene needs a view the reference cannot supply, and a stated rule for what
`build_prompt` says about pose. **Not** a catalogue of poses, and not a prompt-wording pass: a list
of better phrasings with no rule behind it is the shape that has failed here three times already
(spec `lettering-suppression` §1 — three wording attempts, then a detection channel is what worked).

**Open questions:**
- **The contradiction.** `REFERENCE_NEGATIVE` contains `"back view, seen from behind"`, added
  2026-08-13 to stop the slight-angle turn overshooting. A scene where a character runs away needs
  exactly that view. The one reference every page inherits therefore contradicts the page, and the
  judge — which compares the page to that reference — reads a correctly-drawn fleeing character as
  `same_character=False`. That is a **false negative buying a paid redraw that cannot succeed**.
  Is this measured before it is fixed? (S1 owns the measurement; this session owns the response.)
- Which mechanism: (a) the scene prompt states the pose and the judge is told to expect it;
  (b) a multi-view bible — a second/third canonical reference per character (front, side, back),
  which ADR-004's ≤2 cap and `MAX_DRAWS = 3` both constrain, and which S5 must fund;
  (c) the judge is asked "same character *allowing for a different view*", i.e. the fix is in the
  question, not the artifact; (d) suppress rear-view scenes at the prompt level and always draw
  the character facing the camera — cheapest, and a real cost in storytelling.
- Where does the pose come from? `segment` produces `text_excerpt` and `characters_present` and
  nothing about action. Is pose extracted (a new field, a new call) or inferred by the image model
  from the excerpt as it is today?
- **Judge model.** "Use a better judge model" is `settings.vlm_judge_model` (`google/gemma-3-27b-it`)
  and an env-var swap by ADR-001/ADR-019 — cheap to change, impossible to *justify* without S1's
  agreement measurement. Does this session choose a model, or state the criterion S1's harness must
  clear before one is chosen?
- Does a view/pose failure need a signal to correct on? `FailureReason` is frozen at 7 (ADR-028)
  and none of them is "wrong view". The precedent for adding an axis without touching the enum is a
  **boolean on `VlmVerdict`** (`text_free`, `subjects_unique`) plus a `correct_prompt` clause driven
  by that boolean — three fields have now taken that shape. Gate or record-only? `subjects_unique`
  is the record-only precedent, `text_free` the gating one.
- Scene prompt composition generally: `build_prompt` currently emits roll → descriptions → guards →
  setting → excerpt → style. Is that order load-bearing (the setting-before-excerpt ordering is
  deliberate and documented), and does a pose clause have a correct slot in it?

---

### S4 · Setting consistency — READY

**Cluster:** what makes the same place look like the same place across pages, given that a location
today reaches the canvas only as `build_prompt`'s `Setting:` line and is never checked.

**Explicitly out:** characters, in every sense — attributes (S2), pose (S3). Also out: how many
images a location artifact costs (S5 sets the budget; this session names the cost shape).

**Stance:** artifact-class session — done means a location has one named artifact (text, image, or
neither), one named place it persists, and a **named gating decision**. The gating decision is the
part that gets skipped: `subjects_unique` and `text_free` are the two live precedents and they went
opposite ways for stated reasons. Say which one this follows and why.

**Open questions:**
- Reference *image* for a location, or a frozen canonical *text* description? An image is a new
  artifact class: it spends from `IMAGE_BUDGET`, and it collides with the fal payload's numbered
  roll — `REFERENCE_CLAUSE` says "Image N is <character>" and a location image is not a character.
  `referenced_characters` is the single ordering source for three consumers (`generate_scene`,
  `regenerate`, `output_mod`); a fourth kind of image in that list touches all three.
- Text-only is the same invent-and-freeze question S2 answers for characters. **Does S4 inherit
  S2's mechanism, or is place different enough to need its own?** (This is why S4 is downstream of
  S2 and not parallel to it.)
- How many locations? `analyze` caps characters at 3 and deliberately leaves locations **uncapped**
  ("neither costs an image, so neither is a CC-3 lever" — `analyze.py:128`). An image artifact
  falsifies that comment and re-opens the cap.
- `Scene.location_id` is `Optional` and `segment` can leave it null. What does a page with no
  location inherit — nothing, or the previous page's? (Note the cast-carry-forward precedent from
  2026-08-13: carry-forward was *considered and rejected* for characters, because an empty cast is a
  pronoun beat or a scenery page. Whether that reasoning transfers to place is this session's call.)
- A location that legitimately changes — day to night, before and after the storm. Consistency and
  correctness point opposite ways here.
- Is the judge asked about place at all? It is not today. A wrong background is less visible to a
  child than a wrong character, which is an argument for record-only.
- `filtered_location` already exists (ADR-035 surface 5) and filters the description word-level
  while never filtering the name. Whatever artifact is chosen inherits that rule.

---

### S5 · Spend & retry economics — BLOCKED (needs S2, S3, S4)

**Cluster:** how many pages a book has, how many retries each failure axis buys, and the two
constants that both of those resize.

**Explicitly out:** *what* a retry corrects — S2, S3 and S4 each decide their own correction
mechanism and this session only prices them. Also out: any new failure axis.

**Stance:** economics session — done means every budget constant is a **formula with its terms
named** (the existing ones already are, and the comments explaining each term are why the
2026-08-13 resize was safe), and every retry loop has a stated stopping rule. A finished answer
survives someone asking "why 12 and not 11", and survives a later session adding a term.

**Open questions:**
- `MAX_SCENES` 15 → 10-12. Constant, or a function of story length? `MIN_SCENES = 3` and
  `MIN_SCENE_WORDS = 12` are the existing floor, and `MIN_SCENE_WORDS`'s comment warns that a floor
  above the story's mean sentence length "stops being an outlier guard and becomes the pagination
  policy". A lower ceiling forces more merging, so excerpts get **longer** — does a denser excerpt
  make the page harder to draw coherently, cancelling the gain? (S1 should be able to answer this.)
- **Which retry budget?** Four exist, and "increase retries for character consistency" could mean
  any of them:
  | Constant | Where | Today | What it buys |
  |---|---|---|---|
  | `MAX_DRAWS` | `char_bible.py:29` | 3 | reference draws per character |
  | ADR-010's retry | `consistency_check` `len(attempts) >= 2` | 1 | corrected scene redraw |
  | `MAX_MOD_REDRAWS` | `char_ref_mod.py` | 1 | redraw cycles after a moderation flag |
  | `MAX_RETRY_TAPS` | `reveal.py` | 3 | child-initiated reference redraws |
- ADR-010 is **frozen at one retry**. Raising it needs a new ADR — expected, not a blocker.
- **At N > 1, `correct_prompt` accumulates.** It appends clauses to `last.prompt`, which already
  carries attempt 2's correction (`regenerate.py:66-74`), so attempt 4's prompt carries three
  stacked corrections. Intended, or does a later attempt re-correct from `scene.prompt`? Nobody has
  had to answer this because N has always been 1.
- Fixed N, or stop when `_rank` stops improving? `consistency_check._rank` is already a 7-term
  lexicographic tuple and best-of already keeps the least-bad attempt, so a strictly-improving
  stopping rule is available for free. Does attempt 3 ever pass when attempt 2 failed? Unmeasured —
  and this is the single question most worth spending S1's baseline on.
- `IMAGE_BUDGET = MAX_SCENES * 2 + 15` and `RECURSION_LIMIT = MAX_SCENES * 5 + 17`. The `* 2` and
  `* 5` move with the retry cap; the `+ 15` and `+ 17` move with whatever S2/S3/S4 added to the
  prelude. `test_config.py:94` asserts the two preludes stay **unequal** on purpose — they are
  different units and were only ever coincidentally equal. Resize both *with* their arithmetic.
- CC-3: judge calls are still uncounted by `Cost`, and every retry adds up to 4 more per scene.
  Does raising the retry cap force that closed?

---

## Found & parked

Turned up mid-session, belongs to no session here. Recorded so it is not lost, and not this
docket's work.

- **The scene judge cannot see movement direction** (found 2026-08-14, S1 §7.1). Missed 4/4 on a
  wizard moving toward the protagonist where the direction said he flees away, under both
  `SCENE_CONSTRAINT_PROMPT` v1 and v2, with the question asked explicitly both times. Parked rather
  than assigned: S3 owns pose and viewpoint composition, but this is the *judge's* perception, not
  the prompt's composition, and `judge-finetune.md`'s corpus labels `different_character` only — so
  Objective 4 will not close it either. It needs its own decision about whose problem it is.

---

## Amendments

- 2026-08-14 (from plan mode): added **S3 · Pose, viewpoint & scene prompt composition** at the
  user's request after the cut was approved; setting and economics shifted to S4 and S5. The
  approved 4-session cut had no home for it — it concerns characters that *do* have a reference,
  so it is not S2, and it is not place or money.
- 2026-08-14 (from the S1 session): the owner explicitly waived S1's paid corpus baseline. The
  immediate goal is targeted product improvement from observed failures, not a population-level
  consistency claim. The replacement `visual-continuity` design combines the observed portions of
  S2 (frozen text canon for every rostered character), S3 (visible cast, action and viewpoint), and
  a newly observed recurring-object continuity gap. It adds no node, model swap, reference view, or
  retry. S1 remains PARTIAL until the written replacement spec is reviewed and its constraints are
  confirmed; it must then become WAIVED, never DONE, because no baseline was taken.
- 2026-08-14 (S1 close-out): the replacement spec was reviewed on two axes (standards, spec
  conformance), its findings fixed, and `visual-continuity` §7.1 was run. **S1 → WAIVED**, **S2 →
  READY**, and `## Binding constraints` populated with BC-1…BC-6. Two prompt versions moved during
  close-out and are recorded so no later comparison treats them as one instrument:
  `char_bible.JUDGE_PROMPT_VERSION` 4 → 5 (§4.9's outstanding requirement) and
  `consistency_check.SCENE_CONSTRAINT_PROMPT_VERSION` 1 → 2 (unstated-detail exclusion, added in
  response to the §7.1 result). **`consistency_check.JUDGE_PROMPT_VERSION` remains 3** — that is
  `judge-finetune.md` §7.3's pre-registered baseline prompt and it was deliberately not touched.
  §7.2's paid exact-story rerun was **not** performed; the story text was supplied and used to
  build the §7.1 labels instead, so the rerun remains available and unspent.
- 2026-08-14 (S2 close-out): the owner chose the rostered-only, text-canon mechanism already built
  by `visual-continuity`, declined runtime provenance metadata and a real-model verification run,
  and waived a duplicate S2 spec. **S2 → WAIVED**, **S3 → READY**, and **S4 → READY**; BC-7…BC-12
  carry the decisions forward. No implementation changed.

---

## Roster note

`MASTER_SPEC.md` §7 and `docs/product/DECISION_BACKLOG.md` may carry the setting question as a
single queued row — `AGENTS.md` calls it "a queued architectural decision" as of 2026-08-13. It
becomes S4 here. Update both rosters when the docket reaches `DONE` throughout, **not before**, or
the index points at files that do not exist.
