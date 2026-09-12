# Story Titles — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a required, safety/privacy-checked, immutable story title to `POST /storybooks`,
stored on the `jobs` row and never entering the LangGraph pipeline.

**Architecture:** `jobs.title` is a nullable text column, written once by `create_storybook` and by
no other endpoint. The title is checked synchronously, in the request handler, by reusing
`input_gate.py`'s existing moderation classifiers and PII redaction (extracted into a small
`providers.check_text` helper) — never a new moderation model, never `contracts/story_memory.py`.
A redaction that changes the title returns `409` with the redacted text for the child to confirm
before the row is written, so a privacy replacement is never silent.

**Tech Stack:** FastAPI, Pydantic, Supabase (Postgres), pytest, `unittest.mock`.

**Spec:** `docs/specs/story-titles.md` — read alongside `docs/product/adr/ADR-059-story-titles-are-job-metadata-checked-synchronously-before-persistence.md`,
which this plan implements task-by-task.

## Global Constraints

- `MAX_TITLE_CHARS = 80` (spec §1, §3).
- Title required, 1–80 Unicode code points after trimming outer whitespace; interior spacing/case
  preserved; embedded line breaks rejected (spec §3).
- Count Unicode code points, not UTF-16 units — Python's `len(str)` already does this; no new
  counting dependency (spec §3).
- Title never enters `contracts/story_memory.py`, `StoryMemory.Input`, or any pipeline node input
  (spec §4; ADR-059 Decision 2).
- Unchecked title text must never reach durable storage or logs (spec §4; CC-5). Log entity/pass-fail
  counts only, never the title string.
- No new moderation model (spec §4; ADR-059 Decision 3) — reuse `providers.classify_text_primary`,
  `providers.classify_text_backstop`, `providers.redact_pii`.
- No rename/PATCH endpoint for `title` — immutability enforced by absence of a write path (spec §4;
  ADR-059 Decision 5).
- Legacy `jobs.title` rows stay `NULL`; no backfill (spec §4).

---

### Task 1: `MAX_TITLE_CHARS` config constant

**Files:**
- Modify: `backend/app/config.py`
- Test: `backend/tests/test_config.py`

**Interfaces:**
- Produces: `app.config.MAX_TITLE_CHARS: int = 80`, importable exactly like `MIN_STORY_WORDS`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_config.py` (near the existing `MIN_STORY_WORDS` import/assertion at
line 7/168):

```python
def test_max_title_chars_is_80():
    from app.config import MAX_TITLE_CHARS
    assert MAX_TITLE_CHARS == 80
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `uv run pytest tests/test_config.py::test_max_title_chars_is_80 -v`
Expected: FAIL — `ImportError: cannot import name 'MAX_TITLE_CHARS'`

- [ ] **Step 3: Add the constant**

In `backend/app/config.py`, add directly below `MIN_STORY_WORDS = 5` (line 176):

```python
# docs/specs/story-titles.md §1/§3: fixed length independent of story word count.
MAX_TITLE_CHARS = 80
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_config.py::test_max_title_chars_is_80 -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_config.py
git commit -m "feat(titles): add MAX_TITLE_CHARS config constant"
```

---

### Task 2: `providers.check_text` — shared moderation + redaction helper

**Files:**
- Modify: `backend/providers.py`
- Test: `backend/tests/test_providers.py` (create if it does not already exist — check with
  `ls backend/tests/test_providers.py` first; if it exists, add to it instead of creating)

**Interfaces:**
- Consumes: `providers.classify_text_primary(text: str) -> tuple[bool, list[str]]`,
  `providers.classify_text_backstop(text: str) -> tuple[bool, list[str]]`,
  `providers.redact_pii(text: str) -> str` — all already defined in `backend/providers.py`
  (lines 650, 719, 731).
- Produces: `providers.check_text(text: str) -> tuple[bool, list[str], str]` — `(is_safe,
  categories, redacted_text)`. `redacted_text` is always `redact_pii(text)`, computed
  unconditionally so a flagged title's redaction is still available to callers that want it (Task
  4 doesn't need it on the unsafe path, but the return shape stays uniform — no `Optional` a caller
  has to null-check).

This is the ADR-059 Decision 3 extraction: the same primary-then-backstop sequence
`input_gate.py:44-62` already runs, minus the `ThreadPoolExecutor` concurrency (a title is one
short string, not a story body — no stated volatility justifies the extra moving part here).

- [ ] **Step 1: Write the failing tests**

Create/append to `backend/tests/test_providers.py`:

```python
from unittest.mock import patch

from providers import check_text


def test_check_text_safe_no_redaction_needed():
    with patch("providers.classify_text_primary", return_value=(True, [])), \
         patch("providers.classify_text_backstop", return_value=(True, [])), \
         patch("providers.redact_pii", return_value="My Dragon Book"):
        safe, categories, redacted = check_text("My Dragon Book")
    assert safe is True
    assert categories == []
    assert redacted == "My Dragon Book"


def test_check_text_primary_flagged_skips_backstop():
    with patch("providers.classify_text_primary", return_value=(False, ["violence"])) as primary, \
         patch("providers.classify_text_backstop") as backstop, \
         patch("providers.redact_pii", return_value="text"):
        safe, categories, redacted = check_text("text")
    assert safe is False
    assert categories == ["violence"]
    primary.assert_called_once()
    backstop.assert_not_called()


def test_check_text_primary_errors_falls_back_to_backstop():
    with patch("providers.classify_text_primary", side_effect=RuntimeError("oom")), \
         patch("providers.classify_text_backstop", return_value=(True, [])), \
         patch("providers.redact_pii", return_value="text"):
        safe, categories, redacted = check_text("text")
    assert safe is True
    assert categories == []


def test_check_text_backstop_flagged():
    with patch("providers.classify_text_primary", return_value=(True, [])), \
         patch("providers.classify_text_backstop", return_value=(False, ["self_harm"])), \
         patch("providers.redact_pii", return_value="text"):
        safe, categories, redacted = check_text("text")
    assert safe is False
    assert categories == ["self_harm"]


def test_check_text_backstop_errors_hard_fails():
    with patch("providers.classify_text_primary", return_value=(True, [])), \
         patch("providers.classify_text_backstop", side_effect=RuntimeError("down")), \
         patch("providers.redact_pii", return_value="text"):
        safe, categories, redacted = check_text("text")
    assert safe is False
    assert categories == ["moderation_error"]


def test_check_text_returns_redacted_text_even_when_safe():
    with patch("providers.classify_text_primary", return_value=(True, [])), \
         patch("providers.classify_text_backstop", return_value=(True, [])), \
         patch("providers.redact_pii", return_value="call me at <PH_MOBILE>"):
        safe, categories, redacted = check_text("call me at 09171234567")
    assert redacted == "call me at <PH_MOBILE>"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_providers.py -k check_text -v`
Expected: FAIL — `ImportError: cannot import name 'check_text' from 'providers'`

- [ ] **Step 3: Write the implementation**

In `backend/providers.py`, add directly after `redact_pii` (after line 695, before the
`# ADR-032: Local Qwen3Guard removed` comment at line 698):

```python
def check_text(text: str) -> tuple[bool, list[str], str]:
    """Primary-then-backstop moderation plus PII redaction, on ANY text — story or title.

    Same sequence `input_gate.py` runs on `Input.raw_text` (ADR-059 Decision 3), run
    sequentially rather than concurrently: this exists for short, synchronous, one-shot
    checks (a title at submission time), not the story body's per-job cost profile.
    Returns (is_safe, categories, redacted_text). `redacted_text` is always computed —
    callers on the unsafe path may ignore it, but the shape never needs a None-check.
    """
    try:
        primary_safe, categories = classify_text_primary(text)
    except Exception as exc:
        _log.warning("check_text: primary classifier failed (%s) — falling back to backstop", exc)
        primary_safe = None
        categories = []

    redacted = redact_pii(text)

    if primary_safe is False:
        _log.info("check_text: primary flagged (categories=%s)", categories)
        return False, categories, redacted

    try:
        backstop_safe, backstop_categories = classify_text_backstop(text)
    except Exception as exc:
        _log.error("check_text: backstop error — hard fail per ADR-025 (%s)", exc)
        return False, ["moderation_error"], redacted

    if not backstop_safe:
        _log.info("check_text: backstop flagged (categories=%s)", backstop_categories)
        return False, backstop_categories, redacted

    return True, [], redacted
```

Check `backend/providers.py` for its existing module logger name before adding this — grep
`_log = logging.getLogger` in the file and reuse that name (do not introduce a second logger).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_providers.py -k check_text -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/providers.py backend/tests/test_providers.py
git commit -m "feat(titles): extract check_text — shared moderation+redaction for any text"
```

---

### Task 3: `jobs.title` migration and `CreateStorybookRequest.title`

**Files:**
- Create: `supabase/migrations/0019_jobs_title.sql`
- Modify: `backend/app/main.py:49-65` (`CreateStorybookRequest`)
- Test: `backend/tests/test_main.py`

**Interfaces:**
- Consumes: `app.config.MAX_TITLE_CHARS` (Task 1).
- Produces: `CreateStorybookRequest.title: str` (validated, trimmed, 1–80 chars, no line breaks),
  `CreateStorybookRequest.title_ack: str | None = None` — consumed by Task 4.

- [ ] **Step 1: Write the migration**

Create `supabase/migrations/0019_jobs_title.sql`:

```sql
-- supabase/migrations/0019_jobs_title.sql
-- docs/specs/story-titles.md; ADR-059 Decision 1/5.
-- Nullable: existing rows stay NULL, no backfill. Only `create_storybook` (backend/app/main.py)
-- ever writes this column — there is no PATCH/update endpoint for it, which is how ADR-059
-- Decision 5 enforces immutability. 1-80 char / no-newline validation lives in
-- CreateStorybookRequest, not a DB constraint: the checked/redacted value is computed in Python
-- before the insert, so a DB-level CHECK would duplicate that logic against a value the API has
-- already guaranteed.
alter table jobs
  add column if not exists title text;
```

- [ ] **Step 2: Write the failing tests for `CreateStorybookRequest.title` validation**

Add to `backend/tests/test_main.py`, near the existing style-preset validation tests (after line 141):

```python
# --- story-titles spec §3: title field validation ---

def test_create_storybook_requires_title():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post("/storybooks", json={"text": "A dog runs in a field."})
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()


def test_create_storybook_rejects_empty_title():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post(
            "/storybooks", json={"text": "A dog runs in a field.", "title": "   "}
        )
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()


def test_create_storybook_rejects_title_over_80_chars():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field.", "title": "x" * 81},
        )
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()


def test_create_storybook_accepts_title_at_exactly_80_chars():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue), \
         patch("app.main.check_text", return_value=(True, [], "x" * 80)):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field.", "title": "x" * 80},
        )
    assert response.status_code == 200


def test_create_storybook_rejects_title_with_embedded_newline():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field.", "title": "My Book\nPart Two"},
        )
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()


def test_create_storybook_trims_outer_whitespace_preserves_interior():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue), \
         patch("app.main.check_text", return_value=(True, [], "My  Cool Book")):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field.", "title": "  My  Cool Book  "},
        )
    assert response.status_code == 200
    # check_text is called with the trimmed-but-interior-preserved title
    from app.main import check_text as _  # noqa: F401 — import path sanity for the patch target
```

(The last test's `check_text` mock return doesn't need to assert the call arg precisely here —
Task 4 adds the assertion that `check_text` receives the trimmed title, since that's where
`check_text` is actually invoked.)

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_main.py -k "test_create_storybook_requires_title or test_create_storybook_rejects_empty_title or test_create_storybook_rejects_title_over_80_chars or test_create_storybook_rejects_title_with_embedded_newline" -v`
Expected: FAIL — `title` isn't a recognized field yet, so title-omitting/invalid-title requests
currently succeed (422 assertions fail) or `check_text` doesn't exist yet.

- [ ] **Step 4: Add the field and validator**

In `backend/app/main.py`, modify `CreateStorybookRequest` (lines 49-65):

```python
from app.config import MAX_TITLE_CHARS, MIN_STORY_WORDS, SELECTABLE_STYLE_PRESET_IDS, settings


class CreateStorybookRequest(BaseModel):
    text: str
    title: str
    style_preset_id: str | None = None
    # Set only on a resubmission after a 409 asked the child to confirm a redacted title
    # (ADR-059 Decision 4) — the exact string the client is accepting.
    title_ack: str | None = None

    @field_validator("text")
    @classmethod
    def validate_min_length(cls, v: str) -> str:
        if word_count(v) < MIN_STORY_WORDS:
            raise ValueError(f"Story text must be at least {MIN_STORY_WORDS} words")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        # Reject BEFORE trimming — an embedded newline is invalid regardless of outer whitespace.
        if "\n" in v or "\r" in v:
            raise ValueError("Title must be a single line")
        trimmed = v.strip()
        if len(trimmed) < 1:
            raise ValueError("Give your story a title.")
        if len(trimmed) > MAX_TITLE_CHARS:
            raise ValueError("Keep your title to 80 characters.")
        return trimmed

    @field_validator("style_preset_id")
    @classmethod
    def validate_style_preset(cls, v: str | None) -> str | None:
        if v is not None and v not in SELECTABLE_STYLE_PRESET_IDS:
            raise ValueError(f"Unknown style_preset_id: {v!r}")
        return v
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_main.py -k "test_create_storybook_requires_title or test_create_storybook_rejects_empty_title or test_create_storybook_rejects_title_over_80_chars or test_create_storybook_rejects_title_with_embedded_newline" -v`
Expected: PASS. (`test_create_storybook_accepts_title_at_exactly_80_chars` and the trim test still
fail — they need `app.main.check_text`, added in Task 4. That's expected here.)

- [ ] **Step 6: Apply the migration**

This is a schema change against the live Supabase project — run it explicitly in the target
environment per the spec's closing checklist (`docs/specs/story-titles.md` §7: "migration files
are not self-applying"). Follow the project's existing migration-apply command (check
`AGENTS.md` for the Supabase CLI invocation used for prior migrations, e.g.
`supabase db push` or the project's documented equivalent) — do not skip this or assume CI applies
it.

- [ ] **Step 7: Commit**

```bash
git add supabase/migrations/0019_jobs_title.sql backend/app/main.py backend/tests/test_main.py
git commit -m "feat(titles): add jobs.title column and CreateStorybookRequest.title validation"
```

---

### Task 4: Synchronous title checking and persistence in `create_storybook`

**Files:**
- Modify: `backend/app/main.py:92-130` (`create_storybook`)
- Test: `backend/tests/test_main.py`

**Interfaces:**
- Consumes: `providers.check_text(text: str) -> tuple[bool, list[str], str]` (Task 2),
  `CreateStorybookRequest.title` / `.title_ack` (Task 3).
- Produces: `jobs.title` written as the checked/redacted string on every successful `POST
  /storybooks`; `422` on an unsafe or empty/over-limit-after-redaction title; `409` with
  `{"checked_title": <redacted>}` when redaction changed the title and the client hasn't
  confirmed it yet.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_main.py`:

```python
# --- story-titles spec §4: synchronous title check before persistence (ADR-059) ---

def test_create_storybook_persists_checked_title_when_unchanged():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue), \
         patch("app.main.check_text", return_value=(True, [], "My Dragon Book")) as ct:
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field.", "title": "My Dragon Book"},
        )
    assert response.status_code == 200
    ct.assert_called_once_with("My Dragon Book")
    insert_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args["title"] == "My Dragon Book"


def test_create_storybook_rejects_unsafe_title_without_persisting():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue), \
         patch("app.main.check_text", return_value=(False, ["violence"], "My Violent Book")):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field.", "title": "My Violent Book"},
        )
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()
    # CC-5: the title text must never appear in the error response.
    assert "My Violent Book" not in response.text


def test_create_storybook_returns_409_when_redaction_changes_title_unconfirmed():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue), \
         patch("app.main.check_text", return_value=(True, [], "call me at <PH_MOBILE>")):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field.", "title": "call me at 09171234567"},
        )
    assert response.status_code == 409
    assert response.json()["detail"]["checked_title"] == "call me at <PH_MOBILE>"
    fake_supabase.table.return_value.insert.assert_not_called()


def test_create_storybook_persists_redacted_title_when_ack_matches():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue), \
         patch("app.main.check_text", return_value=(True, [], "call me at <PH_MOBILE>")):
        response = client.post(
            "/storybooks",
            json={
                "text": "A dog runs in a field.",
                "title": "call me at 09171234567",
                "title_ack": "call me at <PH_MOBILE>",
            },
        )
    assert response.status_code == 200
    insert_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_args["title"] == "call me at <PH_MOBILE>"


def test_create_storybook_rejects_when_redaction_empties_the_title():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()
    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue), \
         patch("app.main.check_text", return_value=(True, [], "")):
        response = client.post(
            "/storybooks",
            json={"text": "A dog runs in a field.", "title": "09171234567", "title_ack": ""},
        )
    assert response.status_code == 422
    fake_supabase.table.return_value.insert.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_main.py -k "persists_checked_title or rejects_unsafe_title or returns_409 or persists_redacted_title or rejects_when_redaction" -v`
Expected: FAIL — `app.main` has no `check_text` name to patch yet, and the insert dict has no
`"title"` key.

- [ ] **Step 3: Write the implementation**

In `backend/app/main.py`, add the import and modify `create_storybook`:

```python
from providers import check_text
```

Replace the body of `create_storybook` (lines 93-130) with:

```python
def create_storybook(
    payload: CreateStorybookRequest, user=Depends(get_current_user)
) -> CreateStorybookResponse:
    # ADR-059: checked synchronously, before any write, and never via input_gate/StoryMemory —
    # the title is job metadata, not pipeline input.
    title_safe, _title_categories, checked_title = check_text(payload.title)
    if not title_safe:
        raise HTTPException(422, "that title isn't allowed")
    if len(checked_title) < 1 or len(checked_title) > MAX_TITLE_CHARS:
        raise HTTPException(422, "give your story a different title")
    if checked_title != payload.title and payload.title_ack != checked_title:
        # Redaction changed the title and the child hasn't confirmed this exact string yet
        # (ADR-059 Decision 4) — nothing written, no silent post-submit rename.
        raise HTTPException(409, {"checked_title": checked_title})

    job_id = str(uuid.uuid4())
    before = word_count(payload.text)
    text, truncated = clamp_story(payload.text)
    if truncated:
        # CC-5: log counts only, never the text (ADR-025 D5).
        _log.info("story truncated: %d words → %d words", before, word_count(text))
    supabase = get_supabase_client()
    profile_rows = (
        supabase.table("profiles").select("classroom_id").eq("id", user.id).execute().data
    )
    if not profile_rows or profile_rows[0]["classroom_id"] is None:
        raise HTTPException(403, "only students can submit stories")
    classroom_id = profile_rows[0]["classroom_id"]
    supabase.table("jobs").insert(
        {
            "id": job_id,
            "status": "queued",
            "current_stage": "queued",
            "input_text": text,
            "title": checked_title,
            "truncated": truncated,
            "style_preset_id": payload.style_preset_id or "gouache",
            "profile_id": user.id,
            "classroom_id": classroom_id,
        }
    ).execute()
    queue = get_queue()
    try:
        queue.enqueue("worker.run_job.run_storybook_job", job_id, job_timeout=JOB_TIMEOUT_SECONDS)
    except Exception:
        supabase.table("jobs").delete().eq("id", job_id).execute()
        raise HTTPException(503, "could not start — try again")
    return CreateStorybookResponse(job_id=job_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_main.py -k "persists_checked_title or rejects_unsafe_title or returns_409 or persists_redacted_title or rejects_when_redaction" -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/tests/test_main.py
git commit -m "feat(titles): check and persist titles synchronously in create_storybook"
```

---

### Task 5: Update every existing `/storybooks` test to send a title

**Files:**
- Modify: `backend/tests/test_main.py`

**Interfaces:**
- Consumes: nothing new — this task only updates existing test payloads so they satisfy the now-
  required `title` field and don't hit real network calls through `check_text`.

Every pre-existing `client.post("/storybooks", json={...})` call in `backend/tests/test_main.py`
that does **not** already include `"title"` (added by Tasks 3–4) now fails Pydantic validation
with `422`, breaking that test's own assertion. These are exactly the tests listed by the Task 3/4
grep below — patch each one's payload and, where the test asserts on `response.status_code == 200`
or reads `insert_call_args`, also patch `app.main.check_text` so the request doesn't attempt a real
network call.

- [ ] **Step 1: Find every call needing an update**

Run: `grep -n 'client.post("/storybooks"' backend/tests/test_main.py`

Cross off any line already touched by Task 3 or Task 4 (they already carry `"title"`). For every
remaining line, the payload's `json={...}` dict is missing `"title"`.

- [ ] **Step 2: Run the full file to see the current failures**

Run: `uv run pytest tests/test_main.py -v`
Expected: every pre-existing `/storybooks` test that doesn't already send a title now FAILs
(status code assertions expecting `200`/`503`/`403`/`401` now see `422`, or a real
`check_text` call is attempted and errors on missing credentials).

- [ ] **Step 3: Patch each remaining call**

For each test found in Step 1, add `"title": "My Story"` to the `json={...}` dict, and if the test
asserts `response.status_code == 200` (or otherwise expects the request to reach the insert),
also wrap it with `patch("app.main.check_text", return_value=(True, [], "My Story"))`. Tests that
assert an early rejection (401/403/422 from something unrelated to title, e.g.
`test_create_storybook_no_token_returns_401`) need the `"title"` key added to the payload but do
**not** need the `check_text` patch, since request-shape/auth validation runs before the handler
body executes.

Concretely, for `test_create_storybook_inserts_job_and_enqueues` (line 29):

```python
def test_create_storybook_inserts_job_and_enqueues():
    fake_supabase = MagicMock()
    fake_queue = MagicMock()

    with patch("app.main.get_supabase_client", return_value=fake_supabase), \
         patch("app.main.get_queue", return_value=fake_queue), \
         patch("app.main.check_text", return_value=(True, [], "My Story")):
        response = client.post(
            "/storybooks", json={"text": "A dog runs in a field.", "title": "My Story"}
        )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id

    fake_supabase.table.assert_called_with("jobs")
    insert_call_args = fake_supabase.table.return_value.insert.call_args[0][0]
    assert insert_call_args["input_text"] == "A dog runs in a field."
    assert insert_call_args["title"] == "My Story"
    assert insert_call_args["id"] == job_id

    fake_queue.enqueue.assert_called_once_with("worker.run_job.run_storybook_job", job_id, job_timeout=JOB_TIMEOUT_SECONDS)
```

Apply the same two changes (`"title": "My Story"` in the payload, `check_text` patched to
`(True, [], "My Story")`) to every other test in the file that posts to `/storybooks` and expects
to reach the insert/enqueue path: `test_create_storybook_deletes_the_job_row_and_returns_503_when_enqueue_raises`,
`test_create_storybook_rejects_comic_style_preset_with_422` (still expects 422, from style not
title — the `check_text` patch is harmless to add for consistency but not required since the style
validator raises before the handler body runs), `test_create_storybook_rejects_unknown_style_preset_with_422`,
`test_create_storybook_rejects_empty_string_style_preset_with_422`,
`test_create_storybook_omitting_style_preset_stores_gouache`,
`test_create_storybook_null_style_preset_stores_gouache`,
`test_create_storybook_accepts_cut_paper_style_preset`,
`test_create_storybook_rejects_under_minimum_words_with_422` (422 from word count, before title
check — only needs the payload key added, not the patch), `test_create_storybook_rejects_empty_text_with_422`
(same), `test_create_storybook_clamps_over_max_words_and_marks_truncated`,
`test_create_storybook_normal_body_is_not_truncated`, `test_create_storybook_no_token_returns_401`
(payload key only — auth runs first), `test_create_storybook_bad_token_returns_401` (payload key
only), `test_create_storybook_teacher_token_returns_403` (payload key only — the classroom check
runs before the row is used, but title validation happens first now, so add the key to avoid a
422 masking the intended 403).

- [ ] **Step 4: Run the full file to verify everything passes**

Run: `uv run pytest tests/test_main.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Run the full backend suite**

Run (from `backend/`): `uv run pytest`
Expected: all tests PASS — this catches any other file (e.g. `test_finetune_corpus.py`, which
also posts to `/storybooks`-shaped payloads per the earlier grep) that needs the same treatment.
If `test_finetune_corpus.py` constructs its own request payloads for `/storybooks`, apply the same
`"title"` + `check_text` patch pattern there.

- [ ] **Step 6: Lint**

Run: `uv run ruff check .`
Expected: no new violations.

- [ ] **Step 7: Commit**

```bash
git add backend/tests/test_main.py backend/tests/test_finetune_corpus.py
git commit -m "test(titles): add required title field to existing /storybooks test payloads"
```

---

## Self-Review

**Spec coverage:**
- §1 required/80-char/fixed-once-submitted/no-generation-input → Tasks 1, 3, 4.
- §2 architecture gate → resolved by ADR-059 before this plan was written.
- §3 validation (trim, code points, no line breaks, 1–80, no silent truncation, retain values on
  invalid submission) → Task 3 backend-side; retaining values and the exact copy strings are a
  frontend concern (separate plan).
- §4 safety/persistence: checked-before-write, no unchecked title reaching storage/logs, no
  moderation model, explain-before-commit on redaction, immutability, legacy resubmission → Tasks
  2, 3, 4; immutability is structural (no PATCH endpoint added — verified by absence).
- §5 display contract → frontend plan.
- §6 checklist CC-1/2/3/4/5 → covered by Tasks 2 and 4 (reuse existing gates, no title in
  diagnostics, no new endpoint, no title-in-generation).
- §7 verification → this plan's own test/lint steps are the backend half; `pnpm` commands belong
  to the frontend plan.

**Placeholder scan:** no TBD/TODO; every step has runnable code and an exact test command.

**Type consistency:** `check_text(text: str) -> tuple[bool, list[str], str]` is declared once in
Task 2 and consumed with that exact signature in Tasks 3, 4, and 5's mocks
(`(True, [], "...")` / `(False, [...], "...")`, three-tuple throughout).
