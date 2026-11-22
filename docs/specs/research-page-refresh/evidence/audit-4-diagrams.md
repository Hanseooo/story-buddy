# Audit 4: diagrams vs code (2026-11-21, HEAD 47ed5f7)

Read-only. No repo file edited. Labels: **M** measured (read code or ran a command), **I** inferred, **X** inconclusive.

Bottom line: every diagram is stale. The pipeline SVG ("after 2026-10") matched the 11-node graph of 2026-10-09 but the graph now has 14 nodes, a second `interrupt()`, and the magic-pencil reveal routes. The system architecture diagrams (drawio + excalidraw, 2026-09-06) still say Railway and "Qwen" text, and omit Auth, OpenRouter/fal.ai, moderation, Presidio, Langfuse/Sentry and every post-October API surface. The frontend run-viewer map (`pipelineGraph.ts`) is missing the same 3 nodes. No PNG tool is installed except Playwright browsers, which can render the `.drawio.svg` files; the plain `.drawio` and `.excalidraw` files cannot be rendered locally without draw.io desktop or the Excalidraw app.

How the diagrams were parsed (M): a scratch script `decode.py` (in the scratchpad) unescapes the SVG `content=` attribute, inflates the `<diagram>` payload when compressed (these were not: plain `mxGraphModel`), and prints vertices and edges. Excalidraw parsed as JSON (bound text + arrow bindings).

Code ground truth (M): `backend/pipeline/graph.py:152-193` `build_graph()`:
- 14 nodes (`graph.py:154-167`): input_gate, optional_themes, analyze, segment, char_bible, char_ref_mod, reveal, generate_scene, consistency_check, regenerate, output_mod, moderation_review, moderation_replace, compose.
- Edges: `input_gate -> route_after_input` (analyze | optional_themes | moderation_review | raise) `:170`, `:71-77`; `optional_themes -> moderation_router` `:171`; analyze->segment->char_bible->char_ref_mod `:172-174`; `char_ref_mod -> moderation_router` (reveal | char_bible redraw | moderation_review | raise) `:175`, `:23-55`; `reveal -> route_reveal` mapping try_again/choose_version/pencil/pencil_choice -> char_bible, moderation_review, generate_scene, output_mod, compose `:176-184`, `:118-133`; generate_scene->consistency_check `:185`; `consistency_check -> route_after_check` (regenerate | route_next_scene) `:186`, `:136-149`; regenerate->consistency_check `:187`; `output_mod -> route_after_output_mod` (moderation_review | raise | route_next_scene) `:188`, `:58-68`; `moderation_review -> route_moderation_review` (moderation_replace | reveal | return_node from an 11-name allow-list | self) `:189`, `:80-91`; `moderation_replace -> char_ref_mod | consistency_check` `:190`, `:94-95`; compose->END `:191`.
- Interrupts: `pipeline/reveal.py:144`, `pipeline/moderation_review.py:15`.
- Caps: `MAX_RETRY_TAPS = 3` (`reveal.py:24`, shared by "Draw again" and the magic pencil per comment `reveal.py:23`), `MAX_MOD_REDRAWS = 1` (`char_ref_mod.py:19`), `max_scene_attempts = 3` (`app/config.py:101`; finalize rule `consistency_check.py:375`), so up to **two** regenerations per page; `MAX_SCENES = 10`, `MIN_SCENES = 3` (`config.py:186`, `config.py:204`).
- Review mode on by default: `enable_teacher_moderation_review: bool = True`, `enable_magic_pencil: bool = True` (`config.py:90,92`; CHANGELOG.md:17-22).
- Outside the graph: page magic pencil runs as its own RQ job `worker.page_pencil.run_page_pencil` (`app/page_pencil.py:115`, `worker/page_pencil.py:28`); teacher hold resumes run `worker.run_job.run_review_storybook_job` (`app/moderation_hold.py:356,1173,1257`); PDF is an API route (`app/pdf_export.py:20,100`).

Providers (M, defaults in `backend/app/config.py`; prod env overrides not readable, so prod values are X):
- Text LLM `mistralai/mistral-small-3.2-24b-instruct` (`config.py:35`) via OpenRouter (`providers.py:42,185`).
- VLM judge `google/gemma-3-27b-it` (`config.py:36`), base URL OpenRouter by default (`config.py:56`), swappable to vLLM (ADR-019 comment `config.py:54-55`).
- Images: fal.ai `fal-ai/qwen-image` (references, `providers.py:402-415`) and `fal-ai/qwen-image-edit-2511` (scenes, `providers.py:431-445`) (`config.py:37-38`); reference upload to fal storage `providers.py:449`.
- Moderation: text primary `meta-llama/llama-guard-4-12b` (`config.py:61`, `providers.py:933-937`), text backstop `openai/gpt-oss-safeguard-20b` (`config.py:70`, `providers.py:945-955`), image primary `mistral-small-3.2-24b-instruct` (`config.py:68`, `providers.py:978-981`), image backstop `gemma-3-27b-it` (`config.py:73`, `providers.py:1010-1026`), optional-themes LLM check (`pipeline/optional_themes.py`).
- PII: Presidio + spaCy local (`providers.py:634-850`), called in the **web** service before the job row (`app/main.py:188-189`) and in `moderation_hold.py:1197`, `input_gate.py:54`, `optional_themes.py:53`.
- Observability: Langfuse (`worker/run_job.py:1`), Sentry (`pyproject.toml:19`).
- Queue: Redis queue `"storybook"` (`app/queue.py:11`, `worker/run_worker.py:141`). Checkpointer `PostgresSaver` on `supabase_db_url` (`worker/run_job.py:3,67,173,499,536`); research endpoint reads the same checkpoints (`app/research.py:44-47`).
- Hosting: Northflank (ADR-031 "supersedes ADR-009 (Railway)", `docs/product/adr/ADR-031-...md:3`); `backend/Procfile` web + worker. Region: docs say Singapore (`docs/TECH_STACK.md:42`, `docs/product/PRD_v2.md:428`); not checkable from the repo (X).

Supabase (M): tables jobs (`0001`), profiles, classrooms (`0007`), annotations (`0014`), research_pairs (`0016`), onboarding_private.password_operations (`0021`), job_moderation_reviews (`0022`), job_review_notes (`0026`), job_picture_records (`0027`, pencil columns `0029`, `replaced_path` `0031`); `classrooms.moderation_theme_ids` (`0025`), `classrooms.review_notes_enabled` default true (`0033`). Bucket `storybook-images` private (`0001_jobs_table.sql:27-28`). Bucket `private_assets` is used by `backend/finetune/materialize_pairs.py:28` and `scripts/clear_research_pilot.py:10` but created by no migration (M: grep of `supabase/migrations` finds no `private_assets`). Realtime publication on `jobs` only (`alter publication supabase_realtime add table jobs`); subscribers `frontend/lib/useJob.ts`, `components/NeedsHelpQueue.tsx`, `app/s/[profileId]/page.tsx`.

API surface (M, decorators in `backend/app/`): `/storybooks`, `/jobs/{id}/confirm` (main.py:167,267); teacher classrooms/students (`classrooms.py`); moderation settings, reviews, decision/withdraw/reveal, job state, versions open, reconcile-hold (`moderation_hold.py:42-1165`); pencil (`page_pencil.py:139-211`); notes (`review_notes.py`, `child_notes` routes); onboarding (`onboarding.py:44,70`); review approve (`review.py:31`); PDF (`pdf_export.py:100`); research runs (`research.py:130`).

Frontend routes (M, `find frontend/app -name page.tsx`): student `/s/[profileId]` (+ write, process/[jobId], book/[jobId], gallery, settings, introduction, change-password); teacher `/classroom` (+ [classroomId], add, books, settings); `/join`, `/join/[code]`, `/login`, `/signup`, `/welcome`, `/settings`, `/privacy`, `/terms`, `/auth/signout`; research `/annotate`, `/adjudicate`, `/research`, `/research/metrics`, `/research/metrics/[jobId]`, `/research/{dataset,docs,limitations,results}`.

---

## (a) Per-diagram element tables

### A1. `docs/diagrams/drawio/langgraph_pipeline_after_2026-10.drawio.svg` (title "as built 2026-10-09")

At 2026-10-09 the graph had 11 add_node calls (M: `git show 1146498:backend/pipeline/graph.py | grep -c add_node` -> 11), so the diagram was right on its date. Status now:

| Element | Verdict | Evidence |
|---|---|---|
| Subtitle "11 nodes" | wrong (now 14) | graph.py:154-167 (M) |
| START -> input_gate | correct | graph.py:169 (M) |
| input_gate "flag -> job fails" | wrong for default mode: in `teacher_review_v1` a flagged story text is held for the teacher (moderation_review) | graph.py:39-46, input_gate.py:26,83-85, config.py:90 (M) |
| input_gate -> analyze "pass" | correct, but incomplete | graph.py:71-77 (M) |
| optional_themes node + edges | missing | graph.py:155,171,71-77 (M) |
| analyze -> segment -> char_bible -> char_ref_mod | correct | graph.py:172-174 (M) |
| char_ref_mod "second flag -> job fails" | wrong for default mode: reference held for teacher (kind `character_reference`) | char_ref_mod.py:24-33,155-165, graph.py:47-48 (M) |
| char_ref_mod -> char_bible "flagged: one redraw" | correct (MAX_MOD_REDRAWS=1) | char_ref_mod.py:19, graph.py:49-52 (M) |
| char_ref_mod -> reveal "pass" | correct | graph.py:53-54 (M) |
| reveal "interrupt(): waits for the child" | correct, but no longer the only interrupt | reveal.py:144, moderation_review.py:15 (M) |
| reveal -> char_bible "try again (up to 3 taps)" | incomplete: same edge now also carries `choose_version`, `pencil`, `pencil_choice`; the 3-tap budget is shared with the magic pencil | graph.py:176-184, 118-133, reveal.py:23-24 (M) |
| reveal -> route_next_scene "accepted" | correct | graph.py:133 (M) |
| reveal -> moderation_review (held pencil text) | missing | graph.py:126-128 (M) |
| route_next_scene drawn as a router, not a node | correct | graph.py:98-115 (M) |
| route_next_scene -> generate_scene / output_mod / compose | correct | graph.py:111-115 (M) |
| generate_scene -> consistency_check | correct | graph.py:185 (M) |
| consistency_check -> regenerate "fail, retry left" | correct | graph.py:146-148 (M) |
| regenerate "one redraw with the judge's reasons" | wrong: up to two redraws (3 attempts) since 2026-08-27 | config.py:101, consistency_check.py:375; `git log -S"max_scene_attempts: int = 3"` -> ef37fdb 2026-08-27 (M) |
| regenerate -> consistency_check "judge again" | correct | graph.py:187 (M) |
| consistency_check "keeps the better attempt" | correct | changes note 3; consistency_check.py:376-379 (I: read only the finalize block) |
| consistency_check -> route_next_scene "page final" | correct | graph.py:149 (M) |
| output_mod "flag -> job fails, no partial book" | wrong for default mode: scene image held for teacher (kind `scene_image`), replace path via moderation_replace | output_mod.py:131-163, graph.py:58-66 (M) |
| output_mod -> route_next_scene "passed" | correct | graph.py:68 (M) |
| moderation_review node (2nd interrupt) + its 11 return targets | missing | graph.py:165,189,80-91 (M) |
| moderation_replace node -> char_ref_mod / consistency_check | missing | graph.py:166,190,94-95 (M) |
| compose -> END | correct | graph.py:191 (M) |
| "Changed since July" box items 1-5 | correct as history; item 3 "the better of the two attempts" now "the best of up to three" | config.py:101 (M) |
| Page magic pencil on a finished book | missing (out of graph, separate RQ job; diagram should note it as a side path) | app/page_pencil.py:115, worker/page_pencil.py:28 (M) |

### A2. `docs/diagrams/drawio/langgraph_pipeline_before_2026-07.drawio.svg` (and the identical `docs/diagrams/excalidraw/langgraph_pipeline.excalidraw`)

Both have the same 10 nodes and 10 edges (M: parser output identical). They are a historical comparison and are referenced as such by the docs hub (`frontend/app/(research)/research/(reference)/docs/entries.ts:92`).

| Element | Verdict | Evidence |
|---|---|---|
| 10 nodes incl. "char-ref moderation", "output image moderation" | not the July as-built graph: code at end of July (c253074) had 7 nodes and straight edges, no moderation nodes, no regenerate | `git show c253074:backend/pipeline/graph.py` lines 16-31 (M). The diagram matches the planned design (I) |
| regenerate -> generate_scene | removed from code (now -> consistency_check) | graph.py:187 (M) |
| consistency_check -> output image moderation "pass (each scene)" | removed: routing now via route_next_scene; moderation runs per page inside the loop | graph.py:98-115 (M) |
| Labels "fail (1 targeted)" | wrong for today (up to 2), was ADR-010's design (I) | config.py:101 (M) |
| As a "before" diagram | acceptable only if captioned "planned design, July 2026", not "as built" | I |

The excalidraw copy carries no date or "before" label in its elements (M: no free text elements other than node labels), so a reader cannot tell it is historical (I).

### A3. `docs/diagrams/drawio/system_architecture.drawio` (and the identical `docs/diagrams/excalidraw/system_architecture.excalidraw`)

Same 9 boxes and 9 edge labels in both (M). Excalidraw arrows have no start/end bindings (parser printed `None -> None`), so connections are only visual (M).

| Element | Verdict | Evidence |
|---|---|---|
| Next.js (Vercel) | correct | AGENTS.md Project Context; paper Table 8 (M) |
| FastAPI Web (Railway) | wrong host: Northflank | ADR-031:3, backend/Procfile, docs/capstone/system_architecture.md:30 (M) |
| RQ Worker (Railway) | wrong host: Northflank | same (M) |
| Redis Broker -> RQ "pulls job" | correct | app/queue.py:11, worker/run_worker.py:141 (M) |
| FastAPI -> Redis (enqueue) edge | missing (diagram has no edge into Redis) | app/main.py:251,317 (M) |
| Next.js -> FastAPI "POST /storybooks" | correct but one of ~40 endpoints; teacher review, pencil, notes, PDF, onboarding, research runs all go through FastAPI too | app/main.py:167, routers main.py:81-87 (M) |
| FastAPI -> Postgres "creates job row" | correct | app/main.py:167-265 (M) |
| FastAPI -> OpenRouter (input moderation) and Presidio before the job row | missing | app/main.py:171-200 (redact at :188-189, 503 moderation_unavailable at :200) (M) |
| Next.js -> Supabase direct reads under RLS | missing | docs/capstone/system_architecture.md:21; frontend/lib/supabaseClient.ts (I: file name, not read) |
| Postgres -> Realtime "updates", Realtime -> Next.js "subscribes" | correct (jobs table only) | migration publication line; frontend/lib/useJob.ts (M) |
| RQ -> Postgres "checkpoint / status" | correct; checkpointer is PostgresSaver over the direct connection | worker/run_job.py:67 (M), ADR-033 per AGENTS.md |
| RQ -> Storage "final images" | wrong label: every reference and every page attempt is uploaded, not only finals; pencil results too | char_bible.py:266, generate_scene.py:52, worker/page_pencil.py:94 (M) |
| RQ -> LangGraph "runs" | correct | worker/run_job.py (M) |
| AI Models "(Qwen, Gemma-3, Qwen-Image)" | partly wrong: text LLM is Mistral Small 3.2 since 2026-08-11; Gemma-3 and Qwen-Image correct; missing Qwen-Image-Edit-2511, Llama Guard 4, gpt-oss-safeguard-20b, Mistral as image guard | config.py:29-38,61-73 (M) |
| Providers OpenRouter / fal.ai | missing (paper Table X names them) | providers.py:42,452 (M) |
| Supabase Auth | missing | profiles/classrooms migrations 0007-0009; app/auth.py:84 (M) |
| Langfuse, Sentry | missing (paper Table 8 lists them) | worker/run_job.py:1, pyproject.toml:19,42 (M) |
| Research endpoint reads checkpoints | missing | app/research.py:1-4,44-47 (M) |
| Teacher-held moderation, review notes, magic pencil, PDF export | missing (all shipped after 2026-09-06) | CHANGELOG.md:17-29; ADR-071, ADR-080, ADR-081, ADR-082 (M) |
| Separate RQ jobs: review resume, page pencil | missing | moderation_hold.py:356, page_pencil.py:115 (M) |
| `fal` CDN upload of references | missing (images leave Supabase for fal) | providers.py:447-449 (M) |

### A4. Frontend run-viewer map `frontend/app/(research)/research/metrics/[jobId]/pipelineGraph.ts`

| Element | Verdict | Evidence |
|---|---|---|
| Comment "Hand-placed copy of build_graph (checked 2026-10-09)" | stale | pipelineGraph.ts:13 vs graph.py (M) |
| 11 nodes | missing optional_themes, moderation_review, moderation_replace; any run that enters them counts them as "not on this map" | pipelineGraph.ts:18-30, 56-58 (M) |
| main-line and loop edges (18) | correct for the 11 nodes | pipelineGraph.ts:31-52 vs graph.py (M) |
| reveal -> char_bible labeled "try again" | incomplete (choose_version, pencil, pencil_choice use the same edge) | graph.py:180 (M) |
| edges into/out of moderation_review / moderation_replace, reveal -> moderation_review, output_mod -> moderation_review | missing | graph.py:189-190, 126-128, 64-65 (M) |
| "Waiting for the child" ended text | incomplete: a run can also wait on the teacher (moderation_review interrupt) | pipelineGraph.ts:70-74, moderation_review.py:15 (M) |

### A5. Research docs hub entry

`entries.ts:88-89` describes the after-2026-10 SVG as "What does the pipeline look like as it runs today?" Wrong since 2026-10-27 (first moderation_review commit de939a3) (M: `git log --since=2026-10-09 -- backend/pipeline/graph.py`).

---

## (b) Diagrams the paper and research page need that do not exist

The paper lists only Figure 1 (IPO) and Figure 2 (LangGraph) plus Appendix A/B copies of them (paper.md:36-37, 78-79, 494-509); both figure slots are empty in the draft (M). No IPO, user-flow, ER, dataset or evaluation diagram exists under `docs/diagrams` (M: `ls`).

| # | Diagram | Needed by | Source files to read |
|---|---|---|---|
| 1 | IPO model (Figure 1, Appendix A) | paper.md:159-170 | paper.md:159-170 (text to draw); `backend/contracts/story_memory.py` (inputs: title, text, style_preset_id); `backend/app/config.py:180-217` (MAX_SCENES=10, MIN_SCENES=3, MAX_STORY_WORDS=500, style presets); `docs/specs/story-titles.md`, `docs/specs/style-presets.md`; `backend/pipeline/compose.py` (output) |
| 2 | LangGraph pipeline, current (Figure 2, Appendix B; replaces A1) | paper.md:185-186; docs hub | `backend/pipeline/graph.py` (all), `pipeline/reveal.py`, `pipeline/moderation_review.py`, `pipeline/moderation_replace.py`, `pipeline/optional_themes.py`, `pipeline/char_ref_mod.py:19`, `app/config.py:90-101`; ADR-080, ADR-082; `docs/specs/magic-pencil.md`; `docs/specs/reference-moderation-retry.md`. Suggest two views: baseline mode (child path) and review mode overlay, since the paper's prose describes baseline |
| 3 | System architecture / deployment (replaces A3; paper "System Architecture" Table X) | paper.md:336-349 | `backend/Procfile`, `backend/Dockerfile`, `backend/app/main.py:81-87,167-265`, `app/queue.py`, `worker/run_worker.py`, `worker/run_job.py`, `providers.py`, `app/config.py:9-75`, ADR-031, ADR-033, ADR-006, `docs/TECH_STACK.md`, `docs/capstone/hardware_and_hosting.md` |
| 4 | User flow: student journey (write -> reveal with Draw again / magic pencil / other versions -> wait -> book, page pencil, read teacher note) | research page, paper Results 3.1 | `docs/specs/USER_FLOW.md`, `docs/specs/ROUTE_MAP.md` (both last changed 2026-10-29, so predate magic pencil 2026-11-0x: re-check), `docs/specs/magic-pencil.md`, `docs/specs/character-review-ux.md`, `docs/specs/kid-flow-*.md`, `docs/specs/account-onboarding.md`; `frontend/app/s/[profileId]/**`; ADR-073, ADR-081, ADR-082 |
| 5 | User flow: teacher journey (create classroom, issue students, review themes, held-moderation queue allow/stop/replace/withdraw, approve book, write note, PDF) | research page, paper | `docs/specs/teacher-review-and-approval.md`, `docs/specs/teacher-dashboard-docket.md`, `docs/specs/teacher-provisioning-and-shell.md`, `docs/specs/classroom-sharing.md`, `docs/specs/export-pdf.md`; `backend/app/moderation_hold.py`, `app/review.py`, `app/review_notes.py`, `app/classrooms.py`; `frontend/app/classroom/**`, `frontend/components/NeedsHelpQueue.tsx`; ADR-071, ADR-072, ADR-080, ADR-081 |
| 6 | Teacher-hold sequence (worker interrupt -> hold row -> teacher decision -> resume job) | paper safety section, defense | `pipeline/moderation_review.py`, `app/moderation_hold.py:325-1257`, `worker/run_job.py` (`run_review_storybook_job`), migrations 0022-0024, 0028, 0030; ADR-080; `docs/specs/moderation-stack.md` |
| 7 | ER / data model | paper, defense | `supabase/migrations/0001-0033` (tables: jobs, profiles, classrooms, annotations, research_pairs, annotation rounds 0018, job_moderation_reviews, job_review_notes, job_picture_records, onboarding_private.password_operations); `backend/contracts/story_memory.py` (checkpoint state, not a table); `docs/specs/auth-identity-and-classroom-schema.md`, `docs/specs/story-memory-contract.md` |
| 8 | Dataset build + annotation pipeline (corpus -> pairs -> blinding -> two raters -> adjudication -> freeze -> splits) | paper.md:240-272; research dataset page | `backend/finetune/build_corpus.py`, `corpus_synthetic.json`, `materialize_pairs.py`, `dataset_selection.py`, `annotation_truth.py`, `build_dataset.py`, `freeze_dataset.py`, `manifest.py`; migrations 0014, 0016-0018; `frontend/app/(research)/annotate`, `adjudicate`; `docs/specs/annotation-surface.md`, `docs/specs/labelling-rulebook.md`, `docs/specs/research-corpus-operations.md`, `docs/capstone/research_runbook.md`, `docs/product/PREREGISTRATION_OBJ4.md` |
| 9 | Fine-tune + evaluation flow (to_llamafactory -> QLoRA x3 seeds -> checkpoint selection on val F1 -> held-out test vs untrained) | paper.md:274-317, 538-568 | `backend/finetune/to_llamafactory.py`, `train.py`, `train_qlora.yaml`, `image_preprocessing.py`, `evaluate.py`, `evaluation_metrics.py`; `docs/specs/judge-finetune.md`, `docs/capstone/model_finetuning.md` |
| 10 | Expert / ISO 25010 evaluation flow (instruments, respondents, weighted mean) | paper.md:319-334, 411-421 | `docs/capstone/evaluation_instruments_brief.md`, `research_instruments.md`, `docs/specs/iso-25010-scope-freeze.md`, `docs/specs/expert-evaluation-decision-brief.md`, `docs/capstone/methodology.md` |
| 11 | Moderation layers (where each guard runs: API boundary, input_gate, char_ref_mod, output_mod, pencil text) | paper Table 8 rows, ethics | `providers.py:850-1026`, `app/main.py:171-200`, `pipeline/input_gate.py`, `char_ref_mod.py`, `output_mod.py`, `optional_themes.py`; ADR-011, ADR-032; `docs/specs/moderation-stack.md` |

Boehm spiral (Figure 3) is a generic figure, not a code diagram; out of scope.

---

## (c) PNG export: tooling finding and proposal

Tooling on this machine (M, PowerShell):
- draw.io desktop: not installed. `Get-Command drawio, draw.io` -> nothing; `C:\Program Files\draw.io\draw.io.exe`, `Program Files (x86)`, `%LOCALAPPDATA%\Programs\draw.io\draw.io.exe` all `False`.
- VS Code extension `hediet.vscode-drawio-1.17.0` installed (`%USERPROFILE%\.vscode\extensions`). It edits `.drawio`, `.drawio.svg` and `.drawio.png`; export is manual in the editor (I: package.json lists `.drawio.png` and an `exportApi` kind; no CLI).
- `winget` present, so draw.io desktop could be installed (`winget install JGraph.Draw`) (I: package id not checked). Installing is a new tool, so ask first.
- Playwright: `playwright-cli` on PATH (`%APPDATA%\npm\playwright-cli`), commands `resize`, `screenshot`, `pdf` (M: `--help`). Browsers in `%LOCALAPPDATA%\ms-playwright` (chromium-1255 and older, firefox, webkit) (M). Playwright is not a `frontend/package.json` dependency (M: grep), and Python `playwright` is not installed (M).
- `sharp@0.34.5` is in `frontend/node_modules/.pnpm` (transitive via Next) (M). It uses librsvg: the `.drawio.svg` files wrap labels in `<switch><foreignObject>` with `<text>` fallbacks (M: 28 foreignObject / 31 text in the after SVG), and colours use `light-dark(...)` (M). librsvg ignores foreignObject and may not resolve `light-dark()` (X), so sharp output would use clipped fallback text. Not recommended.

Recommended method (I, not run): render each `.drawio.svg` in Chromium via Playwright with `colorScheme: 'light'`, a white page background, `deviceScaleFactor: 2`, viewport set to the SVG's `width/height` (932x851 for the after SVG), and screenshot the `<svg>` element. Chromium renders the foreignObject HTML labels exactly as draw.io does. Run it from a scratch script, not a repo dependency. Constraints:
- The plain `system_architecture.drawio` has no SVG render. Either redraw it as `.drawio.svg` (recommended, since it must be redrawn anyway, see A3) or install draw.io desktop and run `draw.io.exe -x -f png -s 2 -b 10 -o out.png in.drawio`.
- The `.excalidraw` files duplicate the stale drawio content. Retire them or leave them; do not export them (rendering needs the Excalidraw app).
- `light-dark()` plus `color-scheme: light dark` and a transparent background mean a dark-mode browser renders white text on transparent. Force light scheme and a white background for PNGs.
- Alternative: open the SVG in the VS Code drawio editor and use File > Export as PNG. Manual, one file at a time.

Where PNGs go (proposal, I): `frontend/public/research/diagrams/<name>.png`, next to the existing `public/research/dataset/` and `public/research/limitations/` image folders (M: `ls frontend/public/research`). Keep the editable source in `docs/diagrams/drawio/` as the one source of truth, and name each PNG after its source file so a drift check can pair them.

How the research page exposes them (proposal, I): the docs hub currently links each diagram to GitHub (`entries.ts:2`, `docs/page.tsx:36`) and renders no image. Add a diagrams section (on `/research/docs` or a new `/research/diagrams` reference page) that shows each PNG inline with alt text, a caption with its "as of" date and source path, a plain `<a href="/research/diagrams/x.png" download>` "Download PNG" link, and the existing GitHub link for the editable source. Extend `entries.test.ts` (which already fails on a renamed or deleted listed file, `entries.ts:7`) to also assert the PNG exists. A `public/` path is a static asset, consistent with ADR-065 (static research pages) (I: ADR title only).

---

## (d) Disagreements between diagrams, `docs/capstone/system_architecture.md`, the paper, and code

| # | Topic | Diagram | system_architecture.md | Paper | Code | Label |
|---|---|---|---|---|---|---|
| 1 | Backend host | Railway (A3) | Northflank (:30) | Northflank (:337) | Northflank (ADR-031:3) | M |
| 2 | Host region | none | none | "Northflank (North America)" (:376) | docs say Singapore (TECH_STACK.md:42, PRD_v2.md:428) | X (dashboard not checkable) |
| 3 | Text LLM | "Qwen" (A3) | Mistral Small 3.2 (:83) | Mistral Small 3.2 (Table 8) | config.py:35 | M |
| 4 | Regenerations per page | "one redraw" (A1), "1 targeted" (A2) | "up to two retries (three attempts)" (:98) and "one targeted regeneration" (:44), contradicting itself | "up to two regeneration attempts" (:186) | max_scene_attempts=3 (config.py:101) | M |
| 5 | Output image moderation | Mistral+Gemma not shown | "an NSFW ViT and a safety rubric on gemma-3-27b-it" (:92) | "Mistral Small 3.2 24B + gemma-3-27b-it" (Table 8) | Mistral primary (config.py:68, replaced Falconsai per ADR-032 comment :62) + Gemma backstop (:73). Doc is wrong | M |
| 6 | Pipeline nodes | 11 (A1), 10 (A2) | 6 flow groups; no reveal, char_ref_mod, output_mod, or teacher-review nodes (:38-45); "ten logical modules" table (:51-62) | prose names reveal, ref moderation, output moderation (:186) but no teacher hold, optional themes, magic pencil | 14 nodes (graph.py:154-167); AGENTS.md says 14 | M |
| 7 | Flag outcome | "job fails" at every gate (A1) | not stated | "If validation fails, the process stops without producing a partial book" (:186) | default mode holds for teacher (config.py:90; graph.py:39-48,64) | M |
| 8 | Scene count | none | none | "storyboard of 10-15 scenes" (:169) | 3-10 pages (config.py MIN_SCENES=3, MAX_SCENES=10) | M |
| 9 | Interrupts | reveal only (A1) | none | child approval only | reveal + moderation_review (reveal.py:144, moderation_review.py:15) | M |
| 10 | Presidio location | none | "integrated into the worker" (:87) | "Northflank worker CPU" (Table 8) | also web service before the job row (main.py:188-189) | M |
| 11 | Storage contents | "final images" (A3) | "generated images via signed URLs" (:76) | "generated images and related files" | every draw uploaded (char_bible.py:266, generate_scene.py:52); `private_assets` bucket used by finetune with no migration | M |
| 12 | Checkpoint granularity | "checkpoint / status" | "after every completed scene" (:32) | "resume from a saved state" | PostgresSaver checkpoints after every node superstep; research.py reads the full history (research.py:44-47) | I (LangGraph default behaviour, not traced in code) |
| 13 | Moderation in the web tier | not shown | "the request never runs synchronously" (:13) | "returns a job identifier without running the generation pipeline" | POST /storybooks runs check_text (two classifier calls + Presidio) synchronously before the row (main.py:171-200) | M |
| 14 | Teacher review / notes / magic pencil / onboarding / research run viewer | absent everywhere | absent (doc changed 2026-10-21, before these shipped) | absent from System Architecture and Table X | shipped, on by default 2026-11-21 (CHANGELOG.md:17-22) | M |
| 15 | Judge model | "Gemma-3" (A3) | prompted gemma-3-27b-it shipped; Qwen3.5-9B QLoRA under evaluation (:83,96) | same (Table 8, :277) | config.py:36 default; prod env X | M / X |
| 16 | Run viewer map vs graph | n/a | n/a | n/a | pipelineGraph.ts 11 nodes vs 14 | M |
| 17 | Docs hub caption "as it runs today" | n/a | n/a | n/a | entries.ts:89, stale since 2026-10-27 | M |
| 18 | "Before 2026-07" label | 10-node design | n/a | n/a | July code had 7 nodes (c253074) | M |

Other notes:
- AGENTS.md `Last reviewed: 2026-10-09` (older than ~50 days, under 90) but its graph paragraph was updated for teacher review; it omits the magic-pencil reveal labels (`pencil`, `pencil_choice`, `choose_version`) (M: AGENTS.md Project Context vs graph.py:180).
- The paper's IPO lists inputs "story title, child-written story, illustration style" (paper.md:163). `enable_pixel_style=False` (config.py:87) and `SELECTABLE_STYLE_PRESET_IDS = {cel, gouache, cut_paper}` (config.py:182), so three selectable styles (M).
