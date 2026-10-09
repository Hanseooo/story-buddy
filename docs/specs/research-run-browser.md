# Feature Spec — Research run browser

**Status:** design approved 2026-10-09; ADR-064 accepted 2026-10-09; not built.
**Issues:** #107 (run list), #104 (run detail), #103 (Langfuse warning and env flag). One PR.
Sub-issue #111 (annotate/adjudicate demo mode) follows after merge and is out of scope here.
**Derived from:** [ADR-064](../product/adr/ADR-064-the-run-viewer-reads-checkpoint-history-through-a-researcher-only-endpoint.md),
ADR-033 (checkpoint store), ADR-006 (signed URLs), ADR-059 (titles),
`supabase/migrations/0008_authorization_surface.sql`.

## 1. Purpose

`/research/metrics` becomes our own run browser. A reader sees what happened in a run without
reading Langfuse's span tree: a public log of runs with research aggregates, and, for signed-in
researchers, a page per run built around the pipeline graph with the path that run took. Langfuse
stays one click away, behind a warning.

**Term.** A **run** is one execution of the pipeline for one submitted story: one `jobs` row and its
checkpoint thread (`thread_id = job_id`). Corpus bundles under `data/judge/corpus/runs/` are not
runs in this sense and never appear here.

## 2. Routes and access

| Route | Signed out | Annotator (`researcher`, not adjudicator) | Adjudicator (`is_adjudicator`) |
| --- | --- | --- | --- |
| `/research/metrics` | list, short ids, no titles | list; titles on approved runs | list, all titles |
| `/research/metrics/[jobId]` | redirect to `/login?next=…` | approved runs; others show "Not approved yet" | every run |
| `GET /research/runs/{job_id}` (backend) | 401 | 200 if approved, else 403 | 200 |

Teachers and students get 403 from the backend route and the detail page shows "Researchers only".
One rule decides both the title and the link: **a viewer sees a run's title exactly when they can
open it.** It lives in one helper, `canOpenRun(viewer, job)`, used by the list. The backend
enforces the same rule on its own (ADR-064 rule 2); the frontend helper only decides what to render.

Middleware adds `/research/metrics/:path*` to its matcher, and `guardRequest` redirects a signed-out
request for any path under `/research/metrics/` to `/login?next=<path>`. The list itself stays
public. The login page today follows `next` for a researcher only under `/annotate` or
`/adjudicate`; it also accepts `/research/metrics` paths, so "Sign in to view" lands on the run.

## 3. Shared research header

New `(research)/_shared/components/ResearchHeader.tsx`. A server part loads the viewer (user,
`role`, `is_adjudicator`, `display_name`), and a client part renders the tabs and marks the active
one with `aria-current="page"`.

- Left: the StoryBuddy logo, linking to `/research` (the methodology page).
- Tabs come from one list, `RESEARCH_TABS` in `(research)/_shared/constants.ts`. Each entry has
  `label`, `href` and `visibleTo(viewer) → boolean`. Today: **Runs** (everyone), **Annotate**
  (researcher, not adjudicator, matching `annotate/layout.tsx`), **Adjudicate** (adjudicator).
  Future pages (#106 Dataset, #105 Docs) are one entry each.
- Right: signed in, `display_name` plus a role chip ("Adjudicator" / "Annotator") and a Log out
  form posting to `/auth/signout`, as the annotate empty state does. Signed out, a
  "Researcher sign in" link to `/login?next=<current path>`.
- On phones, the three tabs fit in one row, the name collapses to the role chip, and nothing
  scrolls sideways.

It renders in a new `research/metrics/layout.tsx` and at the top of `annotate/layout.tsx` and
`adjudicate/layout.tsx`. It is not sticky: the annotate and adjudicate task bars below it already
are (`sticky top-0`), and two sticky bars would stack. `AnnotationClient` and `AdjudicateClient` are not changed: their own
sticky task bars, including their back link, stay as they are. #111 relies on that.

## 4. Run list — `/research/metrics`

**Data.** The server component keeps the service-role read of `jobs` and selects:
`id, status, created_at, style_preset_id, failure_reason, regen_count, image_count, scenes_total,
scenes_passed, scenes_unchecked, usd_estimate, langfuse_trace_url, approved_at, title`. It never
selects `input_text`. Before the rows reach the client, `title` is set to `null` on every row the
viewer cannot open, so a hidden title never reaches the browser. Newest first, no pagination.

**Aggregates**, computed over all runs (filters apply to the list only). Each tile has a one-line
note of what it means, replacing today's "How are these calculated?" block:

- Existing: Total runs, Job pass rate, Page pass rate (today's "Scene pass rate", renamed in the UI
  only), Est. total cost, and the Complete / Failed / In progress row.
- **Failed** shows its split, for example "4 pipeline error · 1 content blocked", using
  `failureLabel`.
- **Unchecked pages:** sum of `scenes_unchecked`. Note: "pages the judge gave no answer on".
- **Images per page:** sum of `image_count` ÷ sum of `scenes_total`, over runs where both are
  set. Note: "1.0 means no redraws".
- **By style:** a small table, one row per `style_preset_id`: runs, job pass rate, page pass rate,
  average cost. Runs with no style are grouped as "No style".

**Filters.** Status chips (All / Complete / Failed / In progress) and a native `<select>` of styles
present in the data. Both live in the URL (`?status=failed&style=cel`) and update with
`router.replace`, so back from a run restores them and a filtered view is shareable. A filter with no
matches shows "No runs match these filters" and a "Clear filters" button.

**Rows.** Desktop table, cards below `md`, as now. Columns: title (or `Run 3f9a1c2e`), status pill,
style, pages `passed/total`, redraws, failure reason in words, cost, date, and the Langfuse button
when the flag is on. A row the viewer can open is one link with the accessible name
"Open run <title or short id>", and the whole row is clickable. Otherwise the title cell shows a lock
and either "Sign in to view" (a link to `/login?next=/research/metrics/<id>`) or "Not approved yet".

**States.** `loading.tsx` skeleton (existing, updated to the new layout), "No runs recorded yet",
the filtered-empty state above, and `error.tsx` with a Retry button.

## 5. Run detail — `/research/metrics/[jobId]`

### 5.1 Backend route

`GET /research/runs/{job_id}` in a new `backend/app/research.py`, registered in `main.py`. Auth
reuses `get_current_user`; a new `require_researcher` dependency returns the profile
(`id, role, is_adjudicator`). Access per §2. The route reads the job row (display fields only), then
the checkpoint history per ADR-064 rule 1, and returns:

```
job:        id, title, status, style_preset_id, created_at, failure_reason, approved (bool),
            langfuse_trace_url, cost columns from the row
checkpointed: bool                      # false → the page shows the row summary only
story:      redacted_text, word_count, truncated
steps:      [{node, started_at, duration_ms | null}]    # history order; "__start__" dropped
ended_on:   {node, kind: "failed" | "waiting" | "running"} | null  # last snapshot's `next`
moderation: input (ModerationResult)
characters: [{char_id, name, description, ref_image_url, ref_moderation_status,
              ref_verdict, ref_verdict_prompt_version}]
scenes:     [{scene_id, text_excerpt, caption, visual_direction, characters_present,
              objects_present, moderation_status, regeneration_count, shipped_attempt (index|null),
              attempts: [{image_url, prompt, passed, failure_reasons, vlm_verdict,
                          scene_contradictions}]}]
cost:       StoryMemory.cost
state:      the projected StoryMemory, for the raw JSON viewer
```

Projection is a pure function, `project_run(job_row, snapshots, sign) → dict`, so it is tested
without a database. `raw_text`, `profile_id` and `classroom_id` are dropped from `state` and appear
nowhere else. `duration_ms` is the gap to the next snapshot's `created_at`; the failing step's is
`null`. `shipped_attempt` is the index of the attempt whose `image_ref` equals `final_image_ref`.
`kind` is `"failed"` for status `failed`, `"waiting"` for `awaiting_confirm`, `"running"` for
`queued` or `running`, and `ended_on` is `null` for `complete`. `story`, `moderation`, `cost` and
`state` come from the newest snapshot whose values are not empty, and are `null` when there is
none. A router that raises (the input gate, page moderation) discards the writes of the node it
follows (checked on langgraph 1.2.8, 2026-10-09), so a run blocked at the input gate has no input
safety result in its state; the page says "not recorded" and `ended_on` names the node.
`get_signed_url(path, expires_in=300)` gains the argument; this route passes 3600.

Only the final reference and its verdict are in the state. Reference draws that were rejected are
not stored, so the page does not claim a draw count.

### 5.2 Page

A server component fetches the route with the session's access token
(`NEXT_PUBLIC_API_BASE_URL`, as `write/page.tsx` does). Top to bottom:

1. **Header.** "← All runs" (back to the list with its filters, falling back to
   `/research/metrics`), title, status pill, style, date, Langfuse button (§6).
2. **Summary strip.** Pages passed, redraws, reference retries, cost, total time (sum of step
   durations, labelled "includes time waiting for the child"), failure reason.
3. **Pipeline graph** (§5.3).
4. **Characters.** A card each: reference image (opens the lightbox), description chips (species,
   colours, body features, clothing), reference safety check, judge verdict with its
   contradictions in plain words.
5. **Pages.** One block per scene: excerpt, drawing direction and cast on the left; attempts side by
   side on the right. The shipped attempt wears a **Shipped** ribbon; each attempt shows a pass or
   fail badge, its failure reasons as labels, the scene contradictions, and a collapsed "Prompt".
   Images open a single-image viewer (`ImageViewer`, a native `<dialog>`). `LightboxModal` is not
   reused: it is built for a reference-and-scene pair with tabs. A shield badge shows the page's
   safety check.
6. **Safety checks.** Input gate (passed, categories), reference checks, page checks, in one row.
7. **Run details.** Prompt versions where recorded; "Models: not recorded for this run"; a
   per-step timing table.
8. **Raw JSON.** `<details>`, collapsed, pretty-printed `state`, with a Copy button.

Failure reasons and verdict fields get readable labels from one map in `utils/metrics.ts`, beside
`FAILURE_LABELS`. An unknown value shows as is.

### 5.3 Pipeline graph

A hand-placed SVG of the 11 nodes, laid out like
`docs/diagrams/drawio/langgraph_pipeline_after_2026-10.drawio`: the main line top to bottom, loops
beside it. Positions and edges are one constant, `PIPELINE_GRAPH`, in
`(research)/research/metrics/[jobId]/pipelineGraph.ts`, with a comment citing
`backend/pipeline/graph.py:build_graph` as the source. Edges:

- Fixed: `input_gate→analyze→segment→char_bible→char_ref_mod`, `generate_scene→consistency_check`,
  `regenerate→consistency_check`.
- `char_ref_mod→char_bible` (reference redrawn after a moderation flag, `moderation_router`) and
  `char_ref_mod→reveal`.
- `reveal→char_bible` (the child tapped try again, `route_reveal`), plus the `route_next_scene`
  targets below.
- `consistency_check→regenerate` (judge failed the page, `route_after_check`), plus the
  `route_next_scene` targets.
- `output_mod`: the `route_next_scene` targets.
- `route_next_scene` targets, from each of `reveal`, `consistency_check`, `output_mod`:
  `→output_mod` (a finished page awaits its safety check: the usual step after a passing judge),
  `→generate_scene` (draw the next page), `→compose` (every page done).

A moderation flag on a page never loops: it fails the job (ADR-025), shown through `ended_on`.

From `steps`: a node's visit count, and an edge's traversal count from consecutive pairs
(`pathCounts(steps)`, a pure function in the same file). Rendering:

- Visited nodes solid with a `×N` badge when N > 1. Taken edges thick with a count label
  ("redraw ×3"). Untaken nodes and edges faded.
- `ended_on`: red outline and "Failed here" for `failed`; amber and "Waiting for the child" for
  `waiting`.
- A step whose node is not in `PIPELINE_GRAPH` is still listed in the panel and the timing table,
  and the graph shows a small "1 step not on this map" note instead of failing.
- Each node is a `<button>` with an accessible name such as
  "consistency check, ran 7 times, 3 redraws". Tab moves in flow order.

Clicking a node opens a panel, a native `<dialog>` styled as a right-hand sheet on `md+` and a bottom
sheet on phones. Escape or the close button dismisses it, and focus returns to the node. It shows
the node's visits with their times, plus what that node produced, in words:

- `input_gate`: safety result, whether text was redacted or truncated.
- `analyze`, `segment`: characters, objects and places found; pages and their directions.
- `char_bible`, `char_ref_mod`: each reference and its verdict and safety result.
- `reveal`: "waited for the child", and the try-again count (`cost.ref_retry_count`).
- `generate_scene`, `consistency_check`, `regenerate`: attempts per page with verdicts.
- `output_mod`: page safety results.
- `compose`: pages shipped.

Each panel ends with a link that scrolls to the matching section below.

### 5.4 States

- `loading.tsx`: skeleton of header, graph block and two page blocks.
- 404: "Run not found", with a link back to the list.
- 403: "Not approved yet" or "Researchers only", with the back link.
- Backend unreachable or 5xx: `error.tsx`, "Couldn't load this run", Retry (`reset()`) and the back
  link.
- `checkpointed: false`: header and summary from the row, plus "No recorded steps for this run".
- An in-progress run: everything recorded so far, with a note that the run is still going.
- A run blocked at the input gate: "Input safety result not recorded", and the graph marks
  `input_gate` "Failed here".
- A broken image: a placeholder with the alt text. Every image's alt names the page and attempt.

## 6. Langfuse link (#103)

- `NEXT_PUBLIC_SHOW_LANGFUSE_LINKS`: the buttons render only when it equals `"true"`. Off by
  default; added to `frontend/.env.local.example`.
- Clicking opens `ConfirmDialog`: title "Open the full Langfuse trace?", description "This trace
  is the full raw record of the run, including the story text before redaction. Open it only when
  you need that detail." Buttons: Cancel (first, so it takes focus; Escape and backdrop click also
  cancel) and "Open in new tab" (`window.open(url, "_blank", "noopener,noreferrer")`).
- One client component, `LangfuseButton`, used in the list rows and the detail header.
- Residual risk stays the owner's (#103): trace URLs remain public, and on a Langfuse Hobby plan a
  trace stops resolving after 30 days. The project's plan was not checked.

## 7. Files

New: `backend/app/research.py`, its test, `ADR-064` (already written),
`(research)/_shared/components/ResearchHeader.tsx`, `research/metrics/layout.tsx`,
`research/metrics/[jobId]/{page,loading,error}.tsx`, the graph, panel and section components
beside it, `components/LangfuseButton.tsx`.
Changed: `backend/providers.py` (`get_signed_url` argument), `backend/app/main.py` (router),
`frontend/middleware.ts`, `research/metrics/page.tsx` and `loading.tsx`, `utils/metrics.ts`,
`annotate/layout.tsx`, `adjudicate/layout.tsx`, `(research)/_shared/constants.ts`,
`frontend/.env.local.example`, `docs/specs/ROUTE_MAP.md` (it lists no research routes today; add the
two metrics routes), `CHANGELOG.md`.

## 8. Testing and done

Tests (each red first, for the intended reason):

- Backend: `project_run` on a hand-built two-scene history: step order and durations,
  `shipped_attempt`, `ended_on` for a failed and a waiting run, and a sentinel `raw_text` string
  absent from the serialized response. Access: signed out 401, teacher 403, annotator on an
  unapproved job 403, annotator on an approved job 200, adjudicator on an unapproved job 200.
  `get_signed_url` default stays 300.
- Frontend: one test per new aggregate in `utils/metrics.ts`; `canOpenRun` for all three viewers;
  `pathCounts` on a looping step list; the Langfuse button with the flag on (modal; Cancel and
  Escape close it; Open calls `window.open`) and off (no button); `guardRequest` for a signed-out
  detail path. The existing `metrics` tests still pass.

Done means:

- Signed out, the list shows no titles and no Langfuse button with the flag off, and a detail URL
  redirects to login.
- As adjudicator, a run of a synthetic story (submitted through a test student account; no donated
  story is opened for this check) renders every section in §5.2, the graph highlights its path, and
  a node panel opens and closes by keyboard.
- Each state in §4 and §5.4 is seen at least once.
- Checked in a browser with `playwright-cli`, at desktop and phone width, with a clean console. The
  owner signs in; the agent stops at the login wall.
- `CHANGELOG.md` entry.

## 9. Out of scope

#111 demo mode; pagination; model IDs per run (not recorded); rejected reference draws (not
stored); changing RLS on `jobs`; pruning or moving checkpoints; the donated-job check #103 leaves
to the owner.
