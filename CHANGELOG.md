# Changelog

What changed in the repository, one entry per merged PR, newest first. The baseline at the bottom
is `main` as it stood before PR #101.

**How to add an entry.** In the PR itself, add a section at the top: the PR number and date, the
issues it closes or refers to, and what changed under Code, Docs and Checks. Sub-issues of the
defense-prep audit ([#102](https://github.com/Hanseooo/story-buddy/issues/102)) each add one when
their PR merges.

**What does not go here.** What a change means for the paper (findings, deviations, limitations)
goes in [`docs/capstone/research-changelog.md`](docs/capstone/research-changelog.md). Link to it
instead of repeating it.

---

## PR #115 · 2026-10-11

A research documents hub, a judge-dataset page and a judge-results page, all public and static.
Closes #105, #106 · Refs #102 · ADR-065, ADR-066

### Code

- `/research/docs` lists the research documents by repository folder. Each file links to its
  latest version on GitHub in a new tab, with the question it answers. The entries live in one
  array, and a test fails when a listed file is renamed or deleted.
- `/research/dataset` shows what the registered freeze holds (899 pairs by split and label), how
  a pair was labelled, how much the two raters agreed, and six hand-picked synthetic example
  pairs with their label and reasons. Every number names the tracked file it comes from.
  Donated material appears as whole-split counts only: a test fails if the page data or an image
  file name contains `don-`.
- Each example card opens to the pair's frozen manifest record and says what the two raters first
  answered. A new section explains every field of a record and shows one training record whole,
  prompt and target answer. The constructed example is now a tortoise pair that reuses the page of
  one of the Same examples (ADR-066). Where the freeze is on disk, a test compares each record with
  it; CI skips that test because the freeze is git-ignored.
- `/research/results` shows the partial judge comparison of 2026-10-08: F1, precision and recall
  for the four judges, what each did with the 47 Different and 282 Same test pairs, the unreadable
  answers, the registered seed 1 comparison, the ambiguous-reference check and the limits. The
  charts are HTML and CSS bars with no chart library. A test fails when a value on the page is not
  in the runbook table it cites.
- The results page also says how the judge was trained (the settings, why three seeds, which
  checkpoint was used) and what the project takes from the result: four readings with their
  sources, then four explanations under a heading that says none was tested (ADR-066 amendment
  (a)). A test checks each setting against the runbook and against `train_qlora.yaml`.
- The docs hub lists `docs/specs/judge-finetune.md` and `backend/finetune/train_qlora.yaml`.
- The three pages are prerendered and read no session, so the middleware matcher is unchanged. They
  share one layout (back link to `/research`) and one error page (Try again, back link).
- The research header gains Dataset, Results and Docs tabs. On the three static pages it hides the account
  block, because those pages do not know who is signed in. Its row now wraps, so on a phone the
  account block drops below the tabs instead of overlapping them.
- `/research` links to all three pages beside "View Live Metrics".
- Twelve 768 × 576 WebP example images under `frontend/public/research/dataset/`, 316 KB in all.

### Docs

- Accepted ADR-065: the two routes are static, link out to GitHub, and show synthetic material
  only.
- `research_runbook.md` gains "What the registered freeze contains": the per-split counts, drift
  reasons and artifact counts the dataset page cites, counted from the `obj4-v1` freeze report.
- Accepted ADR-066: the dataset page shows frozen records, and the results page shows the partial
  comparison from tracked numbers only. Amendment (a), same day, adds the training and reading
  sections.
- `research_runbook.md` gains "Registered training settings", copied from `train_qlora.yaml`, and
  the sentence that all 104 constructed pairs carry one reason and one script-written sentence.
- `research-changelog.md`: three more rows. The cause of the result is not established (four
  untested explanations), the two seeds selected at `checkpoint-40` are the two with the most
  unreadable answers, and training changed the judge's answers without improving F1.
- `research_runbook.md` gains "Exact values of the partial comparison": the confusion counts,
  intervals, exact McNemar p and validation F1 the results page cites, copied from the local
  result. It also records that two constructed training pairs contradict a rated pair.
- `research-changelog.md`: one finding (which way the McNemar p points) and three limitations
  (selection on four Different validation pairs, the two contradictory pairs, three constant fields
  in the training answer).
- The two pipeline diagrams are now `.drawio.svg` files, which GitHub draws and draw.io still edits
  (ADR-065 decision 3). The `.drawio` originals are removed. `research-run-browser.md` §5.3 and the
  note inside the 2026-10 diagram cite the new names.
- `ROUTE_MAP.md` lists the three static routes, their layout and their public access.
  `research-run-browser.md` §3 lists the six header tabs and says the row wraps on a phone.
- `methodology.md` §4.3 and `model_finetuning.md` §2.2 and §3: two statements that matched neither
  the registration nor the freeze are corrected. Training and validation pairs are synthetic and the
  donated stories are the test set only; constructed negatives raise the Different share of the
  training split without balancing it. `research-changelog.md` has the row.

### Checks

- Frontend: `pnpm lint`, `pnpm tsc --noEmit` and `pnpm build` passed. The build lists
  `/research/dataset`, `/research/docs` and `/research/results` as static. `pnpm test`: 68 files,
  653 passed. Before the two diagrams were exported, `entries.test.ts` failed on both.
- The diagrams were exported through draw.io's embed mode in a browser, because draw.io is not
  installed on this machine. Each file was then loaded as an image and compared with its source
  by eye. In the 2026-10 diagram the "accepted" label sits under the "page final" label; that
  comes from the diagram's own layout and is left alone.
- The `don-` guard went red on a planted `don-` file name before it was trusted.
- The freeze comparison went red on a changed `char_id` and on a changed `style_match` before it
  was trusted. The results tests went red on a wrong F1 planted in the page data, and
  on eleven planted changes the implementing agent reported, one at a time. The training tests
  went red on seven planted values, one at a time: epochs, scheduler, updates per seed, a
  checkpoint, the token cap, the Different count and the non-human share.
- Playwright, signed out, at 1280, 375 and 320 px: the three pages render with no console errors
  and no sideways page scroll. On the dataset page all 12 example images load, the split table
  scrolls inside its own box, and Tab reaches the header, the back link, the table and each
  source link with a visible outline. Enter on a focused "Frozen record" opens it. On the results
  page the wide table scrolls inside its own box. `/research` → "See the Judge Results" → "Back
  to Methodology" returns to `/research`.
- Header at 320, 375, 640 and 1280 px, signed out and with adjudicator markup injected into the
  page: nothing overlaps and nothing overflows. Before the wrap, the tabs ran 20 px under the
  sign-in link at 375 px. A real signed-in session was not driven.
- `/research` logs one console error from `PipelineMap.tsx` (an SVG path that uses `calc()`).
  It predates this change and is left alone.

---

## PR #113 · 2026-10-10

Run list, run detail with a pipeline graph, and a warned Langfuse link.
[PR #113](https://github.com/Hanseooo/story-buddy/pull/113) · Closes #103, #104, #107 · Refs #108, #111 · Plans A–E completed and retired

### Code

- `GET /research/runs/{job_id}` reads checkpoint history and returns a projection without raw
  story text or account ids. Annotators open approved runs, the adjudicator opens all (ADR-064).
  The route signs images for an hour through `get_signed_url(..., expires_in=3600)`.
- Public run list: failure split, unchecked pages, images per page, by-style totals, URL filters,
  and whole-row links for allowed viewers. Hidden titles are cleared before rendering.
- Run detail: a clickable 11-node pipeline graph with visit and traversal counts, ended-step
  markers and native node panels, before story, characters, page attempts, safety, timing and
  copyable JSON. Panels lead with the step's purpose and run result, with recorded results and
  timings in native disclosures, and link to each section. Drawing, checking and redrawing have
  distinct summaries. Unvisited, waiting and incomplete steps are described explicitly.
  Image checks use direct, reference-based descriptions and separate required-check issues from
  other warnings. The selected attempt is labeled "Used in the book".
  Image dialogs preserve keyboard dismissal and focus, including broken images.
- Selection clarity (2026-10-10): selected drawings say when no selection explanation was
  recorded, and explicitly acknowledge failed consistency checks. A small question-mark button
  explains the general fallback policy on hover, focus or tap. Consistency-check recorded results
  group each page once, with its drawing count, selection, attempt outcomes and warning lists.
- Shared research header on metrics, annotate and adjudicate. Researcher login can return to
  `/research/metrics/...`. Langfuse links require `NEXT_PUBLIC_SHOW_LANGFUSE_LINKS=true` and warn
  that traces contain the story before redaction. With the flag off, no trace URL reaches the
  browser: the pages no longer pass it to the hidden button.
- A run detail request whose session the backend rejects shows the error page (Retry, back link)
  instead of redirecting a signed-in user to `/login`, which sent them on to `/classroom`.

### Docs

- Accepted ADR-064, run-browser spec and route map describe the built routes and graph.
- The graph component is `PipelineGraphView.tsx` to avoid Windows resolving its import to
  `pipelineGraph.ts`. Drawing summaries include verdicts as required by the spec.
- Review fixes: readable graph/panel text contrast, mobile sheet indicator, and composition-only
  failures labeled Failed in both node summaries and page-attempt badges.
- Clarity review fix: a clean character verdict with a missing page-content result is Not checked,
  with an explanation, rather than a failed check. Its node summary counts the incomplete result
  separately. Recorded composition contradictions still count as failures.
- The spec records why the graph omits `output_mod→output_mod`: `output_mod` screens every
  finished page in one pass, so no run takes it.

### Checks

- Backend: `uv run ruff check .` passed; `uv run pytest -q`: 1,474 passed, 87 skipped,
  6 deselected. The skipped database/RLS and provider checks remain unverified.
- Frontend: `pnpm lint` and `pnpm build` passed; `pnpm test`: 61 files, 604 tests passed.
  The build used CI's placeholder public Supabase values. Next.js reports the existing
  middleware-to-proxy deprecation; that migration is outside this change.
  An earlier concurrent build/test run hit `Test timed out in 5000ms` in the gallery's first render
  test. All 10 gallery tests passed in isolation, then all 598 tests passed in a standalone run.
- Playwright: signed-out list at 1280 × 800 and 360 × 780, generic ids without titles, Langfuse
  hidden, filters survive reload, empty results clear, detail URLs redirect to login. No console errors.
- Code review fix (2026-10-10): with the flag off, the signed-out list page's HTML carried 47
  Langfuse trace URLs before the fix and 0 after, on the local dev server.
- Captured synthetic fixture: desktop graph, keyboard Enter/Escape and focus return, section
  links, phone graph scrolling within its box, 44.45 px node height, bottom sheet. No console errors.
- Clarity follow-up (2026-10-10): purpose/result and disclosure checks passed on desktop and
  360 × 780 fixtures, with 44 px disclosure targets, no horizontal overflow and no unexpected
  console errors during those checks. Judge fields captured from the supplied synthetic run
  cover a passing image with face and text warnings. The real run's new summary was inspected,
  but repeated live reloads stalled, so final layout and keyboard checks used a temporary preview,
  removed afterward. Waiting and missing-result states remain unit-checked.
- Selection follow-up (2026-10-10): the supplied synthetic run loaded successfully. Captured
  page 7 judge fields cover three failed drawings with attempt 2 selected. Regression tests first
  failed on missing selection copy, a missing page heading and Escape leaving hover help open,
  then passed. Live checks passed at 1280, 360 and 320 px: hover, focus, touch tap, Escape,
  hoverable tooltip content, 44 px help target, no horizontal overflow, eight distinct page
  headings, and panel dismissal with focus return. Browser console: 0 errors, 0 warnings.
  Backend checks were not rerun for this frontend-only follow-up.
- Traversal-count and section-link focus regressions were introduced deliberately, observed failing,
  and restored. Page integration failed before mounting the graph, then passed.
- Signed-in synthetic run: all sections, graph counts matching 39 steps, Enter/Escape/focus,
  phone scrolling and bottom sheet, image viewer, filter-preserving back link, malformed ids,
  backend outage and Retry recovery. The adjudicator header fits at phone width. No unexpected
  console errors in normal operation; the intentional outage produces the expected fetch errors.
- Browser regressions: moved visit badges away from redraw labels after a bounding-box assertion
  failed; replaced `reset()` with Next.js 16's `unstable_retry()` after Retry failed to refetch.
  Both have failing-before/passing-after evidence, including real outage/recovery.
- Local backend endpoint fetch: 5.172 s including JSON receipt/parsing for the 39-step synthetic
  run. Performance follow-up: [issue #112](https://github.com/Hanseooo/story-buddy/issues/112).
- Failed, waiting, input-blocked and checkpoint-free real runs were not identified as synthetic
  for this pass; those states and the annotator-only layout remain unit-tested. The owner approved
  pushing the branch and opening PR #113 on 2026-10-10.

---
## Direct to `main` · 2026-10-09 (agreement and sensitivity)

Objective 4's registered agreement and sensitivity analyses.
Refs [#94](https://github.com/Hanseooo/story-buddy/issues/94), #102

### Docs

- `research_runbook.md`: new section "Registered agreement and sensitivity analyses (2026-10-09)"
  with inter-rater κ, the guide-boundary split and the ambiguous-reference secondary analysis.
- `research-changelog.md`: Finding row and a κ line in §1; a Limitation row and §1 item 8 listing
  the label limitations #94 asks the write-up to carry. `group-guide.md` §5.2: κ and the secondary
  result in plain words; §6: the label limitations. `ROADMAP.md` C3-02: dated status.
- `adjudication-notes-2026-09.md`: rows 1 and 2, left as drafts, now record what was applied. Row 1
  from the round-3 labels (15 of 17 pairs Same); row 2 from the owner's recollection, unchecked.

### Checks

- Analysis script (local, git-ignored) verifies the signed lock, manifest and prediction hashes,
  and that database labels equal the freeze labels, before computing anything. No model calls.

---

## Direct to `main` · 2026-10-09

Retry count and Objective 4 table corrections from the defense-prep audit.
Closes [#109](https://github.com/Hanseooo/story-buddy/issues/109) · Refs #102, #94

### Code

- **`/research` page copy**: the pipeline map and the "Targeted Regeneration" bullet said one
  retry; the code allows three attempts with the best kept (`settings.max_scene_attempts = 3`,
  ADR-037).

### Docs

- `group-guide.md` §3: same retry correction. §5.2: the Objective 4 table adds unreadable
  (unparsed) answers per judge (3 / 40 / 44 / 8 of 329), says they score as "same character", and
  cites the local result JSON as the numbers' source.
- `research-changelog.md`: the 2026-10-08 finding row cites the same JSON and the unparsed counts.
- `system_architecture.md`: same retry correction.

### Checks

- Frontend `pnpm lint && pnpm build && pnpm test`.

---

## PR #101 · 2026-10-09

Segment species fix, Objective 4 resume, October probes, group guide.
[PR #101](https://github.com/Hanseooo/story-buddy/pull/101) · Closes #28 · Refs #65, #94, #98, #100

### Code

- **`segment`** adds a cast member when the drawing direction names it by a unique species noun
  ("the moth" adds Ashwing). `human` never matches, a noun two cast members share is skipped, and
  plurals stay groups. (`19cc743`, `docs/specs/scene-segmentation.md`)
- **`analyze`** drops a schema key that leaked into object axes. (`2b15d25`)
- **`providers`**: a fal image flagged inside an HTTP 200 is treated as a content flag. (`80ebd6f`)
- **Styles**: hidden `pixel` trial preset behind `ENABLE_PIXEL_STYLE` and
  `NEXT_PUBLIC_ENABLE_PIXEL_STYLE`, both off by default; migration `0020`; redrawn `cut_paper`
  card. (`9f9d166`)
- **Objective 4 evaluation** (`backend/finetune/evaluate.py`): validation and held-out capture
  reuse verified saved prediction files and capture only the missing ones; HTTP 401 aborts instead
  of scoring as malformed; the CLIP control reads `pooler_output`. (`4fe5072`)
- **`/research` page**: the pipeline map shows all 11 graph nodes and the models in use; it had
  said 10 nodes and named Qwen3-32B and qwen3-vl-32b, both replaced on 2026-08-11. (`a87dbfb`)

### Docs

- October model probes: findings ledger, klein probes and blinded screen, one-moment direction
  test, limitations table (`docs/capstone/model-probes-2026-10.md`). ADR-062 and ADR-063: klein
  rejected, Qwen-Image-Edit stays.
- Pipeline stage audit, provisional and AI-scored (`docs/capstone/pipeline-stage-audit-2026-10.md`).
- Plain-language start page (`docs/capstone/group-guide.md`) and research changelog
  (`docs/capstone/research-changelog.md`), both linked from `AGENTS.md`.
- Diagrams: the July LangGraph drawio renamed `langgraph_pipeline_before_2026-07.drawio`;
  `langgraph_pipeline_after_2026-10.drawio` drawn from `graph.py`, with a list of what changed.
- `ROADMAP.md`: dated status on C3-02, 04, 05 and 13; C3-10 and C3-11 closed. A stray cp1252 byte
  that made the file invalid UTF-8 replaced.
- Stale moderation text in `TECH_STACK.md`, `moderation-stack.md` and `AGENTS.md` (#28).
- `AGENTS.md` rewritten from 828 to 224 lines: wrong facts fixed (two raters plus adjudication,
  migration numbering, export cut), the build log and dated history cut, still-true gotchas moved to
  Project Invariants and a new Known Gaps section.
- Root `CHANGELOG.md` added (this file).

### Checks

- Backend: `ruff` clean; `pytest` 1457 passed, 87 skipped. CI green on `f2f8c0e`.
- Frontend: `eslint` and `tsc` clean; `vitest` 529 passed; `/research` checked in a browser.
- Fixed on the way: a checksum test only failed its file on Windows, where CRLF translation changed
  the bytes; it now writes a wrong digest instead. (`7fa2d53`)

---

## Baseline: `main` at `863a16f` · 2026-10-06

The state before PR #101, for comparison.

- **Pipeline**: 11 LangGraph nodes, the reveal included. Text `mistral-small-3.2-24b-instruct`,
  references `fal-ai/qwen-image`, scene editor `fal-ai/qwen-image-edit-2511`, product judge
  prompted `gemma-3-27b-it`. `segment` added cast members only by name.
- **Objective 4**: three Qwen3.5-9B seeds trained and backed up; no held-out result yet.
- **C3 follow-up**: the September gate audit and the C3-01 to C3-13 tasks in `ROADMAP.md`; no
  October probes, no stage audit.
- **Known stale**: `/research` said 10 nodes and named retired models; the only LangGraph diagram
  was from July and missed the reveal; #28 open.
