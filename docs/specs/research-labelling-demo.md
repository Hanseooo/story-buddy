# Feature Spec — Annotation and adjudication demo

**Status:** approved 2026-10-11, implemented with browser acceptance pending · **Phase:** defense preparation · **Issue:** [#111](https://github.com/Hanseooo/story-buddy/issues/111)
**Owner:** `frontend/app/(research)/annotate/`, `adjudicate/`, and `_shared/`.
**Derived from:** [MASTER_SPEC](../MASTER_SPEC.md) §5–7, [annotation-surface](annotation-surface.md),
[research-run-browser](research-run-browser.md) §3.
**Rationale:** ADR-026 (research surfaces), ADR-065/066 (approved synthetic examples), epic #102.

## 1. Purpose

Let a signed-in researcher demonstrate how annotation and adjudication work after their queues
are empty. Both demos render the existing clients and controls with committed synthetic images.
Demo submissions affect only the current browser view and cannot reach the research write path.

The owner chose to retain researcher sign-in on 2026-10-11. Images and demo progression do not
depend on Supabase Storage or research tables. Authentication and profile authorization still
depend on Supabase, so this feature does not provide a demo during a Supabase outage.

## 2. Contract slice

This feature does not read or write `StoryMemory`.

- **Reads:** the approved examples in
  `frontend/app/(research)/research/(reference)/dataset/data.ts` (`EXAMPLES`) and their existing
  images under `frontend/public/research/dataset/`.
- **Writes:** component state only: current example, form selections, and demo completion count.
  No database, Storage, browser storage, cookie, or research evidence is written by demo submission.
- **Presentation:** project only the two image URLs and a demo identifier into the existing
  `ResearchPair` shape. The fields `canonical_signed_url` and `scene_signed_url` carry local
  `/research/dataset/*.webp` paths in demo mode. This is an internal presentation use, not a
  change to a signed-URL contract or a public API.
- **Invariants:** synthetic examples only, no donated material, no research predictions or frozen
  answers shown in the annotation form, and no live submission callback available in demo mode.

## 3. Position and scope

Demo mode lives on the existing `/annotate` and `/adjudicate` routes. No new route, middleware
rule, role, backend endpoint, database schema, provider call, or dependency is introduced.

Existing layouts keep their authorization rules: `/annotate` admits a researcher who is not an
adjudicator, and `/adjudicate` admits a researcher. Header tab visibility stays as specified in
`research-run-browser` §3. Demo mode does not broaden either route's access.

Implementation stays within the annotate, adjudicate, and shared research modules. Update this
spec, link it from `annotation-surface.md`, and add the issue's implementation entry to
`CHANGELOG.md` in the implementation PR.

## 4. Behavior and edge cases

### 4.1 Entry and exit

- Keep the normal route as the live queue. Its existing empty message remains visible.
- Add **Try annotation demo** linking to `/annotate?demo=1` and **Try adjudication demo** linking
  to `/adjudicate?demo=1` in the corresponding empty states. Add **Back to Research Lab** there
  alongside the existing logout action.
- Only the exact, single query value `demo=1` requests demo mode. Missing, other, or repeated
  values use the ordinary queue. The query never bypasses layout authorization.
- In demo mode, branch before calling `getNextPair` or `getConflictedPair`. Do not query
  `research_pairs`, read `annotations`, or mint signed image URLs for the demo.
- The explicit demo URL works independently of whether the live queue is empty. Queue errors
  remain errors and never silently become demo data.
- Show **Exit demo** linking to the same route without the query, plus the existing research-home
  link. Exiting or reloading discards local selections. Reloading starts with the first example.

### 4.2 Example selection

Use two existing, owner-approved pipeline examples in this order on both surfaces:

| Example | Source pair | Synthetic character | Role |
| --- | --- | --- | --- |
| 1 | `033b8372e89e4c06` | `syn-025:c0` | A human character whose identity is retained |
| 2 | `1843d7d4835a8397` | `syn-016:c0` | A creature whose face differs |

Resolve these by source pair ID from `EXAMPLES`, not by array position. Reuse the committed
image paths. Do not copy frozen records, extract new corpus images, query the freeze, or include
the constructed example, which no rater annotated. A shared demo data module may project the
examples; the existing dataset module remains the source of truth for their images.

Demo identifiers are `demo-syn-025-c0` and `demo-syn-016-c0`, distinct from research pair IDs.
This naming is bookkeeping, not the protection against writes.

Every committed pipeline example has agreeing identity answers. The adjudication demo therefore
uses deliberately illustrative answers, never claims to replay actual rater disagreement, and
never substitutes these answers into dataset records. Use these fixed examples:

| Example | A1: same / reasons / anatomy intact / text free | A2: same / reasons / anatomy intact / text free |
| --- | --- | --- |
| 1 | `true / [] / true / true` | `false / [different_face] / true / true` |
| 2 | `false / [different_face] / true / true` | `false / [different_face, wrong_body_feature] / false / false` |

Together these exercise the existing identity, reasons, anatomy, and text conflict indicators.
They illustrate disagreement mechanics and are not judgments about defects actually visible in
the examples. Each answer follows the existing Same/Different payload rules.

### 4.3 Local interaction and submission boundary

Render the real `AnnotationClient` and `AdjudicateClient`, keeping their layouts, taxonomy,
verdict bar, lightbox, and shortcuts guide. Add the small mode-specific copy and controls needed
below. Do not create a separate demo imitation of either form.

Bind each live submit action in its existing route page and pass it to the client as
`submitAction`. Use an explicit live-or-demo props union: `mode: "live"` requires `submitAction`,
and `mode: "demo"` supplies the samples and forbids `submitAction`. The client must not import a
submit server action or fall back to one when a callback is absent. Keep the existing live
payload, error handling, and refresh behavior. Do not add a demo flag to either server action.
These mode props are internal component interfaces. The existing route pages bind live actions;
demo props carry only local samples.

Both button and Enter submission use the same handler. A valid demo submission increments the
demo count, advances to the next example, clears every form selection and error, and closes the
lightbox. It does not invoke a server action, refresh the route, fetch a queue, or revalidate a
page. Do not introduce an artificial network delay. Repeated Enter cannot submit the newly
advanced blank form.

After the second submission, show **Demo complete — nothing was saved**, with **Restart demo**
and **Exit demo**. Restart returns to example 1 with a blank form and a zero count. Do not loop
silently. The completion state retains the demo notice and a link back to the research home.

### 4.4 Copy, states, and keyboard behavior

- Display **Demo · Synthetic samples · Nothing is saved** throughout the demo, with
  **Example 1 of 2** or **Example 2 of 2**. Counts describe demo examples, not research labels or
  completed annotation rounds.
- In adjudication also display **Illustrative disagreements — not recorded rater answers** next
  to the comparison summary. Do not describe a demo choice as saved ground truth.
- Use **Submit demo answer** and **Submit demo decision** for the respective verdict-bar actions.
  Keep validation: no initial choice, Different requires at least one reason, Same clears reasons,
  and anatomy/text choices are independent. Preserve the Clothing/Style-only warning.
- Keep the existing route loading and generic error boundaries. While either sample image loads,
  communicate loading and disable submission. If an image fails, show a generic local sample
  error, disable submission, and offer retry and Exit demo. Retry reloads the current local images
  without fetching a queue or losing form selections. Never replace failed demo images with live
  or donated assets.
- All existing shortcuts work in demo mode: `0`, Shift+D, `1`–`7`, A, T, Space, `?`, Enter, and
  Escape. A taxonomy shortcut from the initial blank form selects Different and ticks that reason
  on the first press. Enter cannot submit while an inspection or guide dialog is open.
- Dialogs have accessible names, receive focus, contain keyboard focus while open, close with
  Escape, and return focus to their opener. On example advance or completion, move focus to the
  new example heading or completion heading and announce the change. Navigation and controls
  retain visible focus and accessible names.

## 5. Cross-cutting checklist

- [x] **CC-4 Security:** existing researcher authorization remains. Demo clients have no live
  submission capability. Public assets are only those already approved by ADR-065/066.
- [ ] **CC-6 Accessibility:** keyboard, focus, dialog, disabled, loading, and error behavior in §4.4.
  Covered by jsdom tests. Native focus containment and what a screen reader announces wait for the
  browser check.
- [x] **CC-8 Design language:** reuse the research controls and `DESIGN.md` tokens and layout.
- [x] **CC-9 Failure states:** local image failure and route errors have retry and exit navigation.
- **CC-1/2/3/5/7/10:** no new moderation, story text, paid generation, research measurement,
  seed behavior, or checkpoint state. Reload deliberately resets demo progress.

## 6. Acceptance and verification

Acceptance requires both surfaces to show the approved images, preserve working local controls,
complete and restart the two-example demo, and make no research write or queue call in demo mode.

Extend the existing Vitest suites, using the committed example data rather than invented image
fixtures. Write failing tests before implementation. Mock the server-action/network boundary,
not the clients or the controls whose behavior is asserted.

- **Client main path, each surface:** render the real demo client, make a valid choice, submit by
  button and by Enter across the two examples, and assert progression, blank next-form state,
  completion, and restart. Server-action spies must remain at zero calls and route refresh must
  remain at zero calls. Check the rendered demo identity and synthetic sample notice.
- **Client critical failure path, each surface:** an unselected form or failed image cannot advance
  or call a submit action. Retry retains selections and Exit demo remains available. Exercise
  loading and failure through image events at the browser boundary.
- **Route tests:** extend the existing live/empty/error tests for the links and exact query handling.
  A demo request renders the real client with sample props without calling its queue action.
  Existing layout authorization tests continue to cover the retained role rules.
- **Static data assertions:** both selected examples exist, are synthetic pipeline pairs, have
  committed local image files, and contain no donated identifier. Illustrative answers obey the
  closed taxonomy and differ in the declared fields. Their expected values are the table in §4.2.
- **Fresh browser evidence:** check both roles' permitted demo route at desktop and phone widths.
  Check every shortcut, modal focus and dismissal, completion/restart/exit, live empty states,
  loading, and failed-image recovery. The normal flow has a clean console and no submit-action
  request. For the intentional failure case record the induced image-load error separately.
  The browser user must sign in themselves if authentication is required.

Run from `frontend/`: `pnpm lint`, `pnpm build`, and `pnpm test`. These are implementation checks,
required before merge. Tests prove absence of submission calls; no insert
or queue update can be reached through that demo path. Do not claim a live database or RLS audit
from a mocked test, and do not test by submitting to the frozen campaign.

## 7. Eval / quality checks

N/A. No content is generated, no answers are graded, and demo interactions are excluded from
Objective 4. Demo copy follows the operative two-rater and owner-adjudication procedure in the
2026-09-23 amendment to `PREREGISTRATION_OBJ4.md`, with its later recorded deviations. The older
single-rater account in `annotation-surface.md` is historical context, not the demo's procedure.

## 8. Linked decisions and review

- [ADR-026](../product/adr/ADR-026-researcher-facing-surfaces-two-authenticated-routes-no.md).
- [ADR-065](../product/adr/ADR-065-the-research-docs-hub-and-dataset-page-are-static-and-show-synthetic-material-only.md).
- [ADR-066](../product/adr/ADR-066-the-dataset-page-shows-frozen-records-and-a-static-page-shows-the-partial-judge-result.md).
- [Pre-registration](../product/PREREGISTRATION_OBJ4.md), [runbook](../capstone/research_runbook.md),
  and [labelling rulebook](labelling-rulebook.md).

The owner approved sign-in, explicit entry, the two-example sequence, illustrative
disagreements, and the submission boundary on 2026-10-11. A public demo,
new route, new research contract, or altered role access requires a separate decision and the
applicable approval/ADR process.


### Implementation evidence (2026-10-11)

- `pnpm lint`: passed.
- `pnpm build` with placeholder public Supabase values: passed compilation, TypeScript and page
  generation. The existing middleware deprecation warning remains outside this change.
- `pnpm test --maxWorkers=2`: 73 files and 691 tests passed, including retained authorization
  and live submission suites. The count was 71 and 667 before the limitations page (ADR-067) and
  the review fixes below.
- Final focused acceptance run: 7 files, 34 tests passed.
- The initial client demo tests failed on missing demo behavior. The focused keyboard check also
  failed with `Wrong Color` unchecked when its key was pressed on a focused radio, then passed
  after correcting the input guard.
- Browser checks could not run because neither the in-app browser nor Chrome is connected.
  Desktop/phone presentation, native focus containment and a clean network/console still need
  verification after the user signs in. jsdom supplies only the native-dialog open/close boundary.
- Backend, live database and RLS checks were not run. This change does not alter their code.

### Review fixes (2026-10-11)

A two-axis review before the PR found these. Each got a test that failed first.

- **Keys were dead inside an open dialog, on the live routes too.** The first build returned early
  for every key while a dialog was open, and both dialogs stopped every key from reaching the page.
  Space no longer closed the inspector and `?` no longer closed the guide, which both did before
  this change. Now only Enter is stopped at the dialog. §4.4 asks for exactly that.
- **An image that failed before the page became interactive stayed "loading"** with no retry. The
  check after mount handled only an image that had loaded. Read from the code, not seen in a
  browser.
- **The demo comparison was still captioned "Blinded Dual Annotations (A1 vs A2)".** The
  illustrative-answers line moved from the banner to that caption (§4.4, "next to the comparison
  summary").
- **Both empty states had two filled buttons.** The demo link is now outlined (`DESIGN.md` §7).
- **Tests added:** the verdict and reasons reset on advance, the queue error branch on both routes,
  a repeated `demo` value on `/adjudicate`, the back link on `/annotate`, and the empty message on
  `/adjudicate`. Each went red when the behaviour it names was removed.

Left as they are, by choice:

- The demo state and banner are written twice, once per client. That is the second copy, and the
  project extracts on the third.
- `expect(submitAction).not.toHaveBeenCalled()` cannot fail, because the clients no longer import
  an action. §6 asks for the assertion. The props union is what prevents the call.
- The example heading takes focus when the demo first opens and is also a live region. Whether
  that is read twice needs a screen reader.
- The owner viewed the adjudication demo in a browser on 2026-10-11 and found it good. Still owed
  from §6: the annotation demo, phone width, every shortcut, and a failed image.
  `/annotate?demo=1` without a session redirects to `/login`, as §3 requires.

