# Feature Spec — judge selector (identity judge per book)

**Status:** Ready — seams and OD-01 to OD-03 confirmed by the owner, 2026-11-27 (§7, §8). Not implemented.
**Owners:** `backend/app/main.py`, `backend/providers.py`, `backend/app/config.py`,
`backend/pipeline/consistency_check.py`, `backend/worker/run_job.py`, `backend/contracts/story_memory.py`,
`frontend/app/s/[profileId]/write/`, `supabase/migrations/`
**Derived from:** owner grilling session, 2026-11-26 (decisions Q1–Q10 below)
**Rationale:** ADR-004, ADR-015, ADR-018, ADR-019, ADR-061, `judge-finetune.md` §7.5; a new ADR is
required (SH-07)

## 1. Purpose and scope

### Problem

The project was asked to deploy the fine-tuned judge in the live product (Q1). Today every identity
check uses prompted `google/gemma-3-27b-it` over OpenRouter (`config.py:35`). The fine-tuned
Qwen3.5-9B adapter exists only as a research result, because OpenRouter cannot serve a custom LoRA
(ADR-019).

### Solution

Whoever writes a book picks which model runs that book's identity check: Gemma (the default), the
untuned Qwen3.5-9B base, or fine-tuned Qwen3.5-9B (seed 2). Both Qwen options come from one vLLM
server on a Vast.ai instance, which is turned on for rehearsal and the defense. If that server is
down, the Qwen options are disabled. If it fails partway through a book, that check falls back to
Gemma and the record says so.

### Users

Everyone who can create a book. There are no child users; StoryBuddy is demo-only (owner, 2026-11-25).
The owner chose a visible dropdown for UX (Q8). The dropdown is not role-gated.

### In scope

- A judge dropdown on the write screen, saved on the job.
- Routing the identity check to Gemma (OpenRouter) or Qwen (vLLM) by the job's choice.
- An availability check that disables the Qwen options when the server is down.
- Per-check fallback to Gemma, recorded.
- Showing the chosen judge and the fallback count on the research metrics job page (OD-01).
- A new ADR, and the serving config for the Vast instance.

### Out of scope

- Switching models for the scene-constraint check (`SCENE_CONSTRAINT_PROMPT`), the reference judge
  (`char_bible.py:292`, `:419`) or either moderation layer. They stay on their current models. The
  adapter was trained only on the identity task (`SceneVerdict`), and the fine-tuned model never sits
  on the child-safety path (`judge-finetune.md` CC-1).
- Modal, RunPod or any scale-to-zero host (Q3).
- Making a Qwen judge the default (Q7).
- Seeds 0 and 1 as product options (Q4).
- Re-running or changing the Objective 4 evaluation.

### Existing behaviour that constrains the change (verified)

- `POST /storybooks` (`main.py:163`) takes the optional `style_preset_id`, validates it in
  `CreateStorybookRequest`, and writes it to `jobs`. `worker/run_job.py:479` reads it back into
  `StoryMemory`. The judge choice follows the same path.
- `providers.judge()` (`providers.py:200`) accepts `model`, but always posts to the single
  `settings.judge_base_url`.
- `consistency_check.judge_attempt` (`consistency_check.py:184`) calls `judge(JUDGE_PROMPT…, SceneVerdict)`
  once per referenced subject, then calls the scene-constraint judge once. A failed identity call sets
  `identity = None`, which means "identity check unavailable" for that attempt.
- Every scene rerun (regenerate and later attempts) goes back through the `consistency_check` graph
  node. Page pencil (`worker/page_pencil.py`) runs outside the graph and makes no identity-judge call.
- `Attempt.identity_checks` (`story_memory.py:254`) was added additively, with no `schema_version`
  bump. This is the precedent for additive recording.
- The saved vLLM command (`data/judge/evaluations/obj4-v1/heldout-1/serving/selected-serving-v1.zip`,
  `server.json`) serves `Qwen/Qwen3.5-9B` at revision `c202236…` with `--enable-lora` and the adapter
  module `seed2_checkpoint140`. Requesting `model="Qwen/Qwen3.5-9B"` gets the untuned base.
  Requesting the adapter name gets fine-tuned seed 2.
- Measured on an earlier Vast host: adapter requests took 21.9 s and 46.6 s
  (`research_runbook.md:840`). The client timeout is 60 s (`providers.py`, `judge_with_metadata`).

### End-to-end acceptance journeys

- **J1, happy path.** The Qwen server is up. A user writes a story, picks "Qwen fine-tuned", and
  submits. Every identity check in the book is answered by seed 2. The record shows "Qwen fine-tuned
  (seed 2)" with 0 fallbacks.
- **J2, server down.** The server is off. The write screen shows both Qwen options disabled, with a
  reason. Gemma is selected, and the book is judged by Gemma.
- **J3, failure mid-book.** The user picks fine-tuned Qwen. The server stops partway through. The
  book still finishes. Checks after the failure are answered by Gemma, and the record shows the
  fallback count.

## 2. Shared behaviour

- **SH-01 Options.** There are three judge choices with stable ids: `gemma` (default),
  `qwen_base`, and `qwen_finetuned`. Each maps to a model id: `gemma` → `settings.vlm_judge_model`,
  `qwen_base` → `Qwen/Qwen3.5-9B`, `qwen_finetuned` → `seed2_checkpoint140`. Proposed labels are
  "Standard (Gemma)", "Qwen base" and "Qwen fine-tuned". The labels are owner-adjustable.
- **SH-02 Scope of the choice.** The choice affects only the identity call, `judge(JUDGE_PROMPT…,
  SceneVerdict)`. Every other `judge()` call keeps its current model and route.
- **SH-03 Route by model.** A Qwen choice posts to `settings.qwen_judge_base_url` with
  `settings.qwen_judge_api_key`, and sends no OpenRouter `provider` body. Gemma keeps the current
  OpenRouter route and provider pinning. vLLM rejects the unknown `provider` field (ADR-019).
- **SH-04 Fallback.** When a Qwen identity call raises (connection error, timeout, HTTP error, or no
  parseable `SceneVerdict`), that same check is retried once on Gemma. The model that actually
  answered is recorded in `IdentityCheck.judge_model` (OD-02). If the Gemma retry also fails, the
  existing behaviour applies: `identity = None`, and the attempt counts as identity-unavailable. The
  Qwen leg makes one attempt with no client retries. Its timeout is set from the §7.6 latency
  measurement and recorded in the runbook entry (OD-03).
- **SH-05 Availability.** Qwen is "available" when `qwen_judge_base_url` is set and the server
  answers a short check that lists both model ids. Otherwise both Qwen options are unavailable, with
  one reason.
- **SH-06 The choice is fixed per book.** The choice is saved on the job at submit. It applies to
  every `consistency_check` run for that job, including reruns. A later availability change never
  rewrites it. It only triggers SH-04 per call.
- **SH-07 ADR.** A new ADR (next free number, ADR-087 at the time of writing) amends ADR-019 and the
  deployment gate in `judge-finetune.md` §7.5. It must state four things:
  1. The judge ships as selectable, and Gemma stays the default.
  2. On the measured held-out result (untuned F1 0.472, seed 1 0.310, seed 2 0.417), the fine-tune is
     not promoted.
  3. Seed 2 was chosen after the test results, because it had the best F1 and the fewest unreadable
     answers. Seed 1 remains the registered result.
  4. Nothing hard-depends on the Vast server.

## 3. User stories and acceptance criteria

### US-01 Pick a judge when writing a book

As a person writing a book, I want to choose which model checks my pictures, so that I can show each
judge working in the real product.

Applies: SH-01, SH-05, SH-06

- **AC-01** When the write screen opens, a labelled judge control (native `<select>`, accessible name
  "Picture checker") shows the three SH-01 options with Gemma selected.
- **AC-02** While availability is loading, Gemma is selectable, both Qwen options are disabled, and
  the screen shows "Checking…". Submit is not blocked.
- **AC-03** When availability reports unavailable, or the request fails, both Qwen options stay
  disabled and one line under the control says "Qwen checker is offline. Standard is used." Gemma
  stays selected.
- **AC-04** When availability reports available, both Qwen options are enabled.
- **AC-05** On submit, the chosen id is sent as `judge_choice` with the existing payload. The
  existing write-screen draft restore (`page.tsx` prefill) restores the choice the same way it
  restores `style_preset_id`. A restored Qwen choice falls back to Gemma in the control if Qwen is
  unavailable when the screen opens.
- **AC-06** The control works with the keyboard in the existing focus order between the style picker
  and submit, and shows the project's focus ring.

### US-02 The server accepts and stores the choice

As the system, I want the choice validated and saved on the job, so that the worker and the record
agree on which judge was asked for.

Applies: SH-01, SH-06

- **AC-07** `POST /storybooks` with no `judge_choice` stores `gemma`.
- **AC-08** `POST /storybooks` with an unknown `judge_choice` returns 422, and no job row is written.
- **AC-09** `POST /storybooks` with `qwen_base` or `qwen_finetuned` stores it unchanged, without
  checking availability at submit time. A server that is down is handled per call by SH-04.
- **AC-10** Migration `0034` adds `jobs.judge_choice text not null default 'gemma'`, with a check
  constraint limited to the three SH-01 ids. Existing rows read as `gemma`.

### US-03 The identity check runs on the chosen judge

As the person demoing the book, I want every identity check in the book answered by the judge I
picked, so that "this book was judged by X" is true.

Applies: SH-02, SH-03, SH-04, SH-06

- **AC-11** `run_job` loads `judge_choice` into `StoryMemory` next to `style_preset_id`.
- **AC-12** With `qwen_finetuned`, each identity call posts to `qwen_judge_base_url` with
  `model="seed2_checkpoint140"` and the `SceneVerdict` response format, and sends no `provider` body.
- **AC-13** With `qwen_base`, the same request uses `model="Qwen/Qwen3.5-9B"`.
- **AC-14** With `gemma`, requests are byte-identical to today's (OpenRouter URL, `vlm_judge_model`,
  provider pinning).
- **AC-15** In the same attempt, the scene-constraint call goes to OpenRouter on its current model,
  whatever the choice.
- **AC-16** When a Qwen identity call fails, the same check is answered by Gemma, the attempt records
  Gemma as the model that answered, and the book continues.
- **AC-17** When both the Qwen call and the Gemma retry fail, the attempt behaves as today:
  `identity = None`, unavailable.
- **AC-18** Reruns of `consistency_check` for the same job (regenerate, later attempts, and resumes
  after a pause) use the stored choice.

### US-04 Tell whether Qwen is up

As the write screen, I want one cheap availability answer, so that I never offer a judge that cannot
answer.

Applies: SH-05

- **AC-19** An authenticated `GET /judges` returns the three options with
  `{id, label, available, reason}`. Gemma is always available. The Qwen entries share one result.
- **AC-20** With `qwen_judge_base_url` unset, both Qwen options return `available: false`. No
  network call is made.
- **AC-21** With the URL set, the backend calls the server's model list with a short timeout. Both
  Qwen options are available only if both model ids are listed. A timeout, an error or a missing id
  gives `available: false`.
- **AC-22** `GET /judges` never returns the Qwen URL or key.

### US-05 See which judge checked a book

As a teacher or researcher, I want to see the judge a book asked for and how often it fell back, so
that I can prove the fine-tuned model actually judged it.

Applies: SH-04, SH-06

- **AC-23** The book's record shows the requested judge label, for example "Qwen fine-tuned
  (seed 2)", and "Fell back to Standard: N of M identity checks". It is shown on the research metrics
  job page `/research/metrics/[jobId]`, next to the existing style field. N and M are counted from
  `IdentityCheck.judge_model` (OD-01, OD-02).
- **AC-24** A job created before migration `0034` shows "Standard (Gemma)" with no fallback line.
- **AC-25** Children's book views (reader, gallery) do not show this record.

### US-06 Serve the Qwen judge on Vast

As the owner, I want a repeatable way to bring the Qwen server up and down, so that I control the
cost and can rehearse.

Applies: SH-03, SH-05

- **AC-26** The serving config committed to the repo matches the saved `server.json`, with these
  changes. It serves only `seed2_checkpoint140`. It listens on a public interface, requires
  `--api-key`, and adds whatever vLLM needs to return the `SceneVerdict` structured response.
- **AC-27** A committed probe script sends one real identity pair to the server per Qwen model. It
  records latency and whether a `SceneVerdict` parsed. This is the go/no-go check in §7.
- **AC-28** The runbook entry lists start, health check, the env vars to set on Northflank
  (`QWEN_JUDGE_BASE_URL`, `QWEN_JUDGE_API_KEY`), stop and destroy. It also records the hourly price
  and bandwidth terms of the offer actually rented.

## 4. Edge cases

| Case | Expected behaviour | Home |
|---|---|---|
| No `judge_choice` sent (old client) | Stored as `gemma` | AC-07 |
| Unknown `judge_choice` | 422, nothing written | AC-08 |
| Qwen selected, server goes down before submit | Accepted. Each call falls back to Gemma, recorded | AC-09, SH-04 |
| Server dies mid-book | Remaining checks fall back to Gemma, book finishes | AC-16, J3 |
| Server slow but under the timeout | Qwen answers. The book is slower | SH-04 (OD-03), §7.6 go/no-go |
| Server slow past the timeout | One Qwen attempt, then Gemma answers, recorded | SH-04 (OD-03), AC-16 |
| Qwen returns unparseable output | Counts as failed, so Gemma answers that check | SH-04 |
| Qwen and Gemma both fail | Identity unavailable, as today | AC-17 |
| Server up but adapter not loaded | Qwen unavailable (model id missing from list) | AC-21 |
| `qwen_judge_base_url` unset in an environment | Qwen options disabled, no network call | AC-20 |
| Availability request fails on the write screen | Qwen stays disabled, offline line shown | AC-03 |
| Restored draft holds a Qwen choice while Qwen is down | Control shows Gemma | AC-05 |
| Book paused at the reveal, resumed after the server is destroyed | Stored choice kept, calls fall back | AC-18, SH-06 |
| Teacher-review mode job (`insert_review_job` path) | Same column and behaviour as the plain path | AC-07 to AC-10 |
| Old jobs before migration | Read as `gemma` | AC-10, AC-24 |
| Scene with no referenced subjects | No identity call, so nothing to route or count (M = 0) | AC-23 |
| Page pencil edits | No identity call is made today, so the choice does not apply | §1 verified behaviour |
| Two books submitted at once with different choices | Each uses its own stored choice | SH-06 |
| Qwen key or URL in a response or log | Never returned or logged | AC-22 |

## 5. Design decisions and rationale

- **Follow the `style_preset_id` path** (request field → `jobs` column → `run_job` → `StoryMemory`).
  The pattern already exists and is tested (`test_main.py`).
- **Choice ids, not raw model ids, on the API.** The client cannot point the worker at an arbitrary
  model or URL. Model ids stay in backend config. Labelled *inferred*: the owner did not discuss
  this; it follows the trust-boundary rule.
- **Routing lives in `providers.py`.** ADR-015 keeps every vendor call in one file. The route
  (OpenRouter vs Qwen URL) is picked from the choice inside `providers`. Pipeline nodes pass the
  choice, never a URL.
- **One vLLM server for both Qwen options.** LoRA multiplexing by `model` name is already verified in
  the saved serving config, so base and fine-tuned cost one GPU.
- **Vast.ai, on-demand, A6000 class (Q3).** The tested serving config ran there unchanged. There is
  no cold start while it is up. It cost $0.447/hr including a 100 GB disk on the last rental
  (`research_runbook.md:833`), against about $1.73–2.72/hr for RunPod Serverless 48 GB. The owner
  estimated about $5–6 for roughly 10 hours, plus disk while stopped.
- **Seed 2 (Q4).** It has the best held-out F1 of the three seeds (0.417) and the fewest unreadable
  answers (8 of 329). The selection is post-hoc and disclosed (SH-07).
- **Gemma default (Q7).** Matches the measured result and the registered gate.
- **Visible to everyone (Q8).** Demo-only product. The owner prioritised UX over role-gating.
- **The choice is fixed per book and covers reruns (Q9).** It keeps the record explainable.
- **Fallback plus a disabled option (Q6).** ADR-019 says nothing may hard-depend on this server. A
  disabled option prevents choosing a dead server. Fallback covers a failure mid-book.

## 6. Configuration

New settings in `config.py`: `qwen_judge_base_url: str | None = None`,
`qwen_judge_api_key: str | None = None`. These are set only on Northflank while the instance runs.
They are unset locally and in CI unless a test sets them. The two model ids are env-overridable
Settings fields, read at call time: `qwen_base_model: str = "Qwen/Qwen3.5-9B"` and
`qwen_finetuned_model: str = "seed2_checkpoint140"`. (Changed 2026-11-27 from module constants, to
match AGENTS.md.)

## 7. Verification

### Confirmed seams (owner, 2026-11-27)

1. **`POST /storybooks` and `GET /judges` through the FastAPI TestClient.** Precedent:
   `backend/tests/test_main.py`. Covers AC-07 to AC-09 and AC-19 to AC-22.
2. **`providers` routing, with `providers.OpenAI` patched at the client boundary.** Precedent:
   `backend/tests/test_providers.py`. Asserts the `base_url`, `model` and `extra_body` received, and
   the Gemma retry after a raised Qwen call. Covers SH-03, SH-04, AC-12 to AC-17.
3. **The `consistency_check` node with the same boundary patch.** Covers AC-15, AC-16 and AC-18 on
   real `StoryMemory` state.
4. **The write page component test.** Precedent: `frontend/app/s/[profileId]/write/page.test.tsx`.
   Covers AC-01 to AC-06, with `GET /judges` mocked at fetch.
5. **Migration applied to a scratch DB**, using the method in the project-state memory (local
   container `supabase_db_storybuddy-onboarding`). Covers AC-10.
6. **Live go/no-go on the Vast instance** (AC-27). It must be done before any UI work is called done.
   One real pair per Qwen model must show a parsed `SceneVerdict`, with its latency recorded. The
   owner judges the latency against the Qwen timeout (`QWEN_JUDGE_TIMEOUT_SECONDS`, provisionally 90 s) and book length. No tolerance was agreed.
7. **One E2E scenario in a real browser** (J1, plus J2 with the server stopped), driven with
   `playwright-cli`. The owner logs in.

### Results

None. Nothing has been run against this spec.

## 8. Open decisions, readiness and sources

All resolved by the owner on 2026-11-27 ("i confirm", accepting the recommendations):

| ID | Decision | Why |
|---|---|---|
| **OD-01** | The record (AC-23) is shown on `/research/metrics/[jobId]`. This replaces Q10's "Technical record", which exists only for held books (`NeedsHelpQueue.tsx:274`) | That page already shows `style_preset_id` for every job |
| **OD-02** | An additive `IdentityCheck.judge_model` records the model that answered, with no `schema_version` bump | Follows the `identity_checks` precedent (`story_memory.py:254`). Counts are derived, so there is no second record to keep in sync |
| **OD-03** | The Qwen leg makes one attempt with no client retries. Its timeout is set after the §7.6 measurement | With the 60 s timeout and `MAX_RETRIES`, a dead server would stall each check for minutes |
| Seams | §7 items 1–7 confirmed | |

Owner-accepted assumptions:

- The API takes choice ids, not model ids.
- Submitting with a Qwen choice is accepted even while the server is down.
- An unparseable Qwen answer falls back to Gemma.
- The loading and offline copy is as written in AC-02 and AC-03.

**Readiness:** Ready. Its prerequisites are settled. This does not mean it is implemented, and it
does not authorise implementation.

### Source index

| Source decision | Home |
|---|---|
| Q1 deploy in the live product | §1 Problem, US-03 |
| Q2 live dropdown in the pipeline | US-01, US-03 |
| Q3 Vast.ai, costs understood | US-06, §5 |
| Q4 seed 2, disclosed as post-hoc | SH-01, SH-07, §5 |
| Q5 per-book choice, saved on the job | US-02, SH-06, AC-10 |
| Q6 fallback + recorded + disabled option | SH-04, SH-05, AC-03, AC-16, AC-21 |
| Q7 Gemma default | SH-01, AC-01, AC-07 |
| Q8 visible to everyone | §1 Users, AC-01 |
| Q9 later checks use the book's judge | SH-06, AC-18 |
| Q10 shown in the Technical record | US-05, AC-23; moved to the metrics job page by OD-01 |
| Identity check only; safety path untouched | SH-02, AC-15, §1 Out of scope |
| Measure latency and structured output first | AC-27, §7.6 |
| New ADR amending ADR-019 and the gate | SH-07 |
| Proposed labels | SH-01 |

Sources: `docs/product/adr/ADR-019-serving-the-fine-tuned-judge-vllm-scale-to-zero-openai.md`,
`docs/specs/judge-finetune.md` §7.5, `docs/capstone/research_runbook.md` ("Exact values of the
partial comparison", line 833 and line 840), `docs/capstone/hardware_and_hosting.md` §7.
