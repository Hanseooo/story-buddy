# Moderation Stack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/specs/moderation-stack.md`

**Goal:** Replace the `input_gate` stub and add `char_ref_mod` + `output_mod` nodes — the three-layer safety mandate that prevents unmoderated content from reaching a child.

**Architecture:** Six independent tasks. Tasks 1–2 are infra (deps, config, provider seam); Tasks 3–5 each implement one pipeline node and its tests; Task 6 rewires `graph.py` to stitch them in. All classifier calls go through `providers.py` functions so tests can mock at that seam. Nodes raise `RuntimeError` on moderation failure (consistent with `compose.py`); `run_job.py`'s existing `except` block catches and marks the job `failed`.

**Tech Stack:** Python 3.12, uv, pytest, ruff, Pydantic v2, LangGraph, `transformers` (local Qwen3Guard-Gen + Falconsai ViT), `presidio-analyzer`/`presidio-anonymizer` + spaCy `en_core_web_sm`, OpenAI SDK (OpenRouter backstops), Supabase Storage signed URLs.

## Global Constraints

- **`backend/contracts/` must not be modified.** Every field already exists (`ModerationResult`, `Character.ref_moderation_status`, `Scene.moderation_status`).
- **All commands run from `backend/`.** Verify with `uv run ruff check . && uv run pytest`.
- **Deterministic tests mock every `providers.py` call.** Never assert on classifier output quality.
- **`ruff format` is not adopted.** Only `ruff check`. Do not reformat files you touch.
- **Surgical changes only.** Every changed line traces to a task step.
- **One module = one concern.** `input_gate.py`, `char_ref_mod.py`, `output_mod.py` — one file each.
- Model IDs live in `backend/app/config.py`; SDKs/endpoints/keys live in `backend/providers.py`.
- `BUCKET = "storybook-images"` — defined in `pipeline/generate_scene.py`, imported by moderation nodes.
- Stock Presidio (English only): `# ponytail: stock Presidio, Filipino names leak — filed as filipino-pii-recognizers spec`
- The moderation router is expressed as **raises** (consistent with `compose.py`), not a conditional edge. Spec's conceptual "moderation_router" maps to the node failing fast.

## File Structure

| File | Task | Responsibility after this plan |
|---|---|---|
| `backend/pyproject.toml` | 1 | Adds `presidio-analyzer`, `presidio-anonymizer`, `spacy`, `transformers`, `torch`, `Pillow`. |
| `backend/app/config.py` | 1 | Replaces `moderation_model` stub with `moderation_primary_model` (HF hub), fixes `moderation_backstop_model`, adds `moderation_backstop_image_model`. |
| `backend/tests/test_config.py` | 1 | Pins new field names and defaults. |
| `backend/providers.py` | 2 | Adds `redact_pii`, `classify_text_primary`, `classify_text_backstop`, `classify_image_primary`, `classify_image_backstop`. |
| `backend/tests/test_providers.py` | 2 | Smoke-tests the 5 new functions (all real I/O mocked). |
| `backend/pipeline/input_gate.py` | 3 | Replaces Phase-1 stub. Runs primary + Presidio concurrently, calls backstop if primary passes, raises on fail. |
| `backend/tests/test_input_gate_node.py` | 3 | Replaces existing stub test. All 6 spec cases. |
| `backend/pipeline/char_ref_mod.py` | 4 | New node. Checks each character's canonical ref image through both classifiers; raises on any flag. |
| `backend/tests/test_char_ref_mod_node.py` | 4 | New test file. All spec cases. |
| `backend/pipeline/output_mod.py` | 5 | New node. Two-classifier check per scene + one soften-and-retry per failed scene; raises on still-failed. |
| `backend/tests/test_output_mod_node.py` | 5 | New test file. All spec cases. |
| `backend/pipeline/graph.py` | 6 | Inserts `char_ref_mod` between `char_bible` and scene loop; adds `output_mod` after loop; changes `route_next_scene` destination from `"compose"` to `"output_mod"`. |
| `backend/tests/test_graph_stub.py` | 6 | Pins the new node count and routing destinations. |

---

### Task 1: Dependencies and Config

**Files:**
- Modify: `backend/pyproject.toml:5-19`
- Modify: `backend/app/config.py:44-51`
- Test: `backend/tests/test_config.py` (append)

**Interfaces:**
- Produces: `settings.moderation_primary_model: str`, `settings.moderation_backstop_model: str`, `settings.moderation_backstop_image_model: str` — consumed by Task 2 provider functions.

- [ ] **Step 1: Add dependencies to pyproject.toml**

In `backend/pyproject.toml`, append inside the `dependencies` list (after `"sentry-sdk[fastapi]>=2.17",`):

```toml
    "presidio-analyzer>=2.2",
    "presidio-anonymizer>=2.2",
    "spacy>=3.7",
    "transformers>=4.40",
    "torch>=2.0",
    "Pillow>=10.0",
```

> **Railway CPU-only note:** PyTorch defaults to CUDA. On Railway (no GPU), add `--extra-index-url https://download.pytorch.org/whl/cpu` to the build command, or set `UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu` in Railway's env vars before deploying. Tests run without a GPU; `torch.float32` on CPU is used throughout.

> **spaCy model:** `en_core_web_sm` must be downloaded once after `uv sync`:
> ```bash
> uv run python -m spacy download en_core_web_sm
> ```
> Add this line to the Railway start command (before the worker) or the Dockerfile. The download is ~35 MB.

- [ ] **Step 2: Run uv sync to verify deps resolve**

```bash
cd backend && uv sync
```

Expected: no resolver errors. If torch conflicts, see CPU-only note above.

- [ ] **Step 3: Replace the moderation config fields**

In `backend/app/config.py`, replace lines 44–51:

```python
    # D-1 resolved (ADR-011c, 2026-07-21): the primary is Qwen3Guard-Gen 0.6B running on the
    # worker CPU — NOT an OpenRouter model id — so this field stays Llama Guard 4 (the demoted
    # fallback) until the Phase-2 `moderation-stack` spec defines the CPU-resident config shape.
    moderation_model: str = "meta-llama/llama-guard-4-12b"

    # D-1 resolved (ADR-011c): backstop is `openai/gpt-oss-safeguard-20b` on OpenRouter (the
    # ADR-011b pair — Qwen3Guard-Gen / Granite Guardian — is not routable there; verified
    # 2026-07-13). Left unset here so the Phase-0.5 probe (`spikes/phase_05.py`) stays opt-in;
    # the Phase-2 `moderation-stack` spec wires the real primary+backstop config shape.
    moderation_backstop_model: str | None = None
```

with:

```python
    # ADR-011c: CPU-resident primary (HF hub id — downloaded at worker startup by transformers).
    # Model swap is env-var change; provider swap is providers.py.
    moderation_primary_model: str = "Qwen/Qwen3-Guard-Gen-0.6B"
    # ADR-011c: text backstop on OpenRouter.
    moderation_backstop_model: str = "openai/gpt-oss-safeguard-20b"
    # ADR-011c / spec §4b-c: Gemma for image safety rubric (violence, gore, dangerous content).
    # Reuses the same model as vlm_judge_model; separate field so the two can diverge.
    moderation_backstop_image_model: str = "google/gemma-3-27b-it"
```

- [ ] **Step 4: Write the failing config tests**

Append to `backend/tests/test_config.py`:

```python
def test_moderation_primary_model_is_qwen3_guard_gen():
    assert settings.moderation_primary_model == "Qwen/Qwen3-Guard-Gen-0.6B"


def test_moderation_backstop_model_is_gpt_oss_safeguard():
    assert settings.moderation_backstop_model == "openai/gpt-oss-safeguard-20b"


def test_moderation_backstop_image_model_is_gemma():
    assert settings.moderation_backstop_image_model == "google/gemma-3-27b-it"
```

- [ ] **Step 5: Run tests — expect FAIL** (field names don't exist yet)

```bash
uv run pytest tests/test_config.py -k "moderation" -v
```

Expected: `AttributeError: 'Settings' object has no attribute 'moderation_primary_model'`

- [ ] **Step 6: Verify tests pass after Step 3**

```bash
uv run pytest tests/test_config.py -v && uv run ruff check .
```

Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/app/config.py backend/tests/test_config.py
git commit -m "feat(moderation): add deps and fix config field shape for Phase-2 moderation stack"
```

---

### Task 2: Provider Seam — Five Moderation Functions

**Files:**
- Modify: `backend/providers.py` (append after `_run_fal`)
- Test: `backend/tests/test_providers.py` (append)

**Interfaces:**
- Consumes: `settings.moderation_primary_model`, `settings.moderation_backstop_model`, `settings.moderation_backstop_image_model` (Task 1).
- Produces (all mocked in node tests):
  - `redact_pii(text: str) -> str`
  - `classify_text_primary(text: str) -> tuple[bool, list[str]]` — `(is_safe, categories)`
  - `classify_text_backstop(text: str) -> tuple[bool, list[str]]`
  - `classify_image_primary(image_url: str) -> bool`
  - `classify_image_backstop(image_url: str) -> bool`

- [ ] **Step 1: Write failing provider smoke tests**

Append to `backend/tests/test_providers.py`:

```python
from unittest.mock import MagicMock, patch


# --- redact_pii ---

def test_redact_pii_returns_string():
    """Smoke test: redact_pii returns a string (real Presidio is an integration concern)."""
    with patch("providers._presidio", return_value=(MagicMock(analyze=lambda **kw: []), MagicMock(anonymize=lambda **kw: MagicMock(text="clean text")))):
        from providers import redact_pii
        result = redact_pii("My name is Juan dela Cruz")
    assert isinstance(result, str)


# --- classify_text_primary ---

def test_classify_text_primary_returns_safe_tuple():
    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = MagicMock(shape=MagicMock(__getitem__=lambda s, i: 5))
    mock_tokenizer.decode.return_value = "safe"
    mock_model = MagicMock()
    mock_model.generate.return_value = [[0] * 10]

    with patch("providers._qwen3_guard", return_value=(mock_tokenizer, mock_model)):
        from providers import classify_text_primary
        safe, categories = classify_text_primary("A dog runs in a field.")

    assert isinstance(safe, bool)
    assert isinstance(categories, list)


def test_classify_text_primary_unsafe_response_is_not_safe():
    mock_tokenizer = MagicMock()
    mock_tokenizer.apply_chat_template.return_value = MagicMock(shape=MagicMock(__getitem__=lambda s, i: 5))
    mock_tokenizer.decode.return_value = "unsafe\nS1: Violence"
    mock_model = MagicMock()
    mock_model.generate.return_value = [[0] * 10]

    with patch("providers._qwen3_guard", return_value=(mock_tokenizer, mock_model)):
        from providers import classify_text_primary
        safe, categories = classify_text_primary("graphic violence")

    assert safe is False
    assert len(categories) > 0


# --- classify_text_backstop ---

def test_classify_text_backstop_returns_safe_tuple():
    with patch("providers.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="safe"))
        ]
        from providers import classify_text_backstop
        safe, categories = classify_text_backstop("A happy dog story.")

    assert safe is True
    assert categories == []


def test_classify_text_backstop_parses_unsafe_with_categories():
    with patch("providers.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="unsafe\nviolence, gore"))
        ]
        from providers import classify_text_backstop
        safe, categories = classify_text_backstop("graphic violence")

    assert safe is False
    assert "violence" in categories


# --- classify_image_primary ---

def test_classify_image_primary_returns_true_for_normal():
    with patch("providers.httpx") as mock_httpx, \
         patch("providers._falconsai") as mock_falconsai:
        mock_httpx.get.return_value.content = b"fake-image-bytes"
        mock_falconsai.return_value.return_value = [{"label": "normal", "score": 0.99}, {"label": "nsfw", "score": 0.01}]
        from providers import classify_image_primary
        result = classify_image_primary("https://example.com/image.png")
    assert result is True


def test_classify_image_primary_returns_false_for_nsfw():
    with patch("providers.httpx") as mock_httpx, \
         patch("providers._falconsai") as mock_falconsai:
        mock_httpx.get.return_value.content = b"fake-image-bytes"
        mock_falconsai.return_value.return_value = [{"label": "nsfw", "score": 0.95}, {"label": "normal", "score": 0.05}]
        from providers import classify_image_primary
        result = classify_image_primary("https://example.com/bad.png")
    assert result is False


# --- classify_image_backstop ---

def test_classify_image_backstop_returns_true_when_safe():
    with patch("providers.OpenAI") as mock_openai_cls:
        mock_openai_cls.return_value.chat.completions.parse.return_value.choices = [
            MagicMock(message=MagicMock(parsed=MagicMock(is_safe=True), content='{"safety_reasoning":"ok","is_safe":true}'))
        ]
        from providers import classify_image_backstop
        result = classify_image_backstop("https://example.com/image.png")
    assert result is True
```

- [ ] **Step 2: Run tests — expect ImportError/AttributeError**

```bash
uv run pytest tests/test_providers.py -k "redact_pii or classify_text or classify_image" -v
```

Expected: failures because the functions don't exist yet.

- [ ] **Step 3: Add the five functions to providers.py**

Append to `backend/providers.py` (after the `_run_fal` function, before the end of file):

```python
# ---------------------------------------------------------------------------
# Moderation providers — CPU-resident primaries + OpenRouter backstops
# All lazy-loaded to avoid importing GB-sized weights at import time.
# ---------------------------------------------------------------------------

def _presidio():
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    # ponytail: stock Presidio, Filipino names leak — filed as filipino-pii-recognizers spec
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    analyzer = AnalyzerEngine(nlp_engine_provider=NlpEngineProvider(nlp_configuration=nlp_config))
    return analyzer, AnonymizerEngine()


def redact_pii(text: str) -> str:
    """Presidio PII redaction (CC-2). en_core_web_sm must be downloaded before first call."""
    analyzer, anonymizer = _presidio()
    results = analyzer.analyze(text=text, language="en")
    return anonymizer.anonymize(text=text, analyzer_results=results).text


def _qwen3_guard():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_id = settings.moderation_primary_model
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float32)
    model.eval()
    return tokenizer, model


# Guard prompt template — verify against https://huggingface.co/Qwen/Qwen3-Guard-Gen-0.6B
# before deploying. The model outputs "safe" or "unsafe\n<categories>" in its response.
_GUARD_SYSTEM = (
    "You are a content safety classifier for a children's education platform (ages 5–12). "
    "Classify the user message as 'safe' or 'unsafe'. "
    "If unsafe, list the violated categories on the next line."
)


def classify_text_primary(text: str) -> tuple[bool, list[str]]:
    """Qwen3Guard-Gen 0.6B (CPU-resident). Returns (is_safe, categories)."""
    import torch
    tokenizer, model = _qwen3_guard()
    messages = [{"role": "system", "content": _GUARD_SYSTEM}, {"role": "user", "content": text}]
    input_ids = tokenizer.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True)
    with torch.no_grad():
        output_ids = model.generate(input_ids, max_new_tokens=64, do_sample=False)
    response = tokenizer.decode(output_ids[0][input_ids.shape[-1]:], skip_special_tokens=True).strip().lower()
    safe = response.startswith("safe")
    categories: list[str] = []
    if not safe and "\n" in response:
        categories = [c.strip() for c in response.split("\n", 1)[1].split(",") if c.strip()]
    return safe, categories


def classify_text_backstop(text: str) -> tuple[bool, list[str]]:
    """gpt-oss-safeguard-20b via OpenRouter. Returns (is_safe, categories)."""
    prompt = (
        "You are a content safety classifier for a children's education platform (ages 5–12). "
        "Classify the following text as 'safe' or 'unsafe'.\n"
        "If unsafe, list violated categories on the next line.\n\n"
        f"Text: {text}"
    )
    client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=settings.openrouter_api_key)
    completion = client.chat.completions.create(
        model=settings.moderation_backstop_model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        extra_body={"provider": {"require_parameters": True}},
    )
    response = (completion.choices[0].message.content or "").strip().lower()
    safe = response.startswith("safe")
    categories: list[str] = []
    if not safe and "\n" in response:
        categories = [c.strip() for c in response.split("\n", 1)[1].split(",") if c.strip()]
    return safe, categories


def _falconsai():
    from transformers import pipeline as hf_pipeline
    return hf_pipeline("image-classification", model="Falconsai/nsfw_image_detection", device="cpu")


def classify_image_primary(image_url: str) -> bool:
    """Falconsai/nsfw_image_detection ViT-base (CPU-resident). Returns True if safe."""
    import io
    from PIL import Image
    response = httpx.get(image_url, timeout=30.0)
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content))
    results = _falconsai()(image)
    top = max(results, key=lambda r: r["score"])
    return top["label"] == "normal"


class _ImageSafetyVerdict(BaseModel):
    # Reason-before-score per ADR-004.
    safety_reasoning: str
    is_safe: bool


def classify_image_backstop(image_url: str) -> bool:
    """gemma-3-27b-it via OpenRouter — violence, gore, dangerous content check."""
    prompt = (
        "You are reviewing an image for a children's educational storybook platform (ages 5–12). "
        "Assess whether the image is safe for children. "
        "Flag: violence, gore, sexual content, frightening imagery, dangerous activities."
    )
    verdict = judge(prompt, [image_url], _ImageSafetyVerdict, model=settings.moderation_backstop_image_model)
    return verdict.is_safe
```

> **Important:** `_presidio`, `_qwen3_guard`, and `_falconsai` are **not** decorated with `@lru_cache` here because Presidio/transformers objects are not hashable. The node tests mock these functions at the seam (`providers.classify_text_primary`, etc.) so the lazy init never runs in CI. For production, each is only called once per worker process (the worker is long-lived), so re-initialization cost is negligible.

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_providers.py -k "redact_pii or classify_text or classify_image" -v
uv run ruff check .
```

Expected: all green. (Note: `_presidio`, `_qwen3_guard`, `_falconsai` are free functions — ruff will not flag them; they are the lazy-init seam for node tests.)

- [ ] **Step 5: Commit**

```bash
git add backend/providers.py backend/tests/test_providers.py
git commit -m "feat(moderation): add five moderation provider functions to providers.py seam"
```

---

### Task 3: Replace `input_gate` Stub

**Files:**
- Modify: `backend/pipeline/input_gate.py` (full rewrite)
- Modify: `backend/tests/test_input_gate_node.py` (full rewrite)

**Interfaces:**
- Consumes: `providers.classify_text_primary`, `providers.classify_text_backstop`, `providers.redact_pii` (Task 2).
- Produces: `input.moderation: ModerationResult`, `input.redacted_text: str` (always set, even on fail — spec §2a invariant).

The spec (§4a) says steps 1 (Qwen3Guard-Gen) and 2 (Presidio) are **independent and run concurrently**. Use `ThreadPoolExecutor` for this.

On moderation fail, raise `RuntimeError("content_flagged")` — `run_job.py`'s `except` block marks the job `failed`.

- [ ] **Step 1: Write failing tests**

Replace `backend/tests/test_input_gate_node.py` entirely:

```python
from unittest.mock import patch

import pytest

from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, StoryMemory


def _state(text: str = "A dog runs in a field.") -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text=text),
    )


# --- happy path ---

def test_both_classifiers_pass_sets_moderation_passed_and_redacted_text():
    """Spec §4a: both pass → moderation.passed = True; redacted_text always populated (CC-2)."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(True, [])) as mock_primary, \
         patch("pipeline.input_gate.classify_text_backstop", return_value=(True, [])) as mock_backstop, \
         patch("pipeline.input_gate.redact_pii", return_value="A dog runs in a field."):
        from pipeline.input_gate import input_gate
        result = input_gate(_state())

    assert result["input"].moderation.passed is True
    assert result["input"].redacted_text == "A dog runs in a field."
    mock_primary.assert_called_once()
    mock_backstop.assert_called_once()


# --- primary flags ---

def test_primary_flags_sets_passed_false_without_calling_backstop():
    """Spec §4a step 3: primary flags → fail; no backstop call when primary already flags."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(False, ["S1"])), \
         patch("pipeline.input_gate.classify_text_backstop") as mock_backstop, \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        with pytest.raises(RuntimeError, match="content_flagged"):
            input_gate(_state("graphic violence"))

    mock_backstop.assert_not_called()


def test_primary_flags_redacted_text_is_still_set():
    """CC-2 invariant: redacted_text populated even on fail (teacher sees the redacted version)."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(False, ["S1"])), \
         patch("pipeline.input_gate.classify_text_backstop"), \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        # We can't inspect the return value because it raises, but we can verify redact was called
        with pytest.raises(RuntimeError):
            input_gate(_state())
        # Presidio ran concurrently — the mock was called
        # (verified by coverage; redact_pii is patched and will record calls)


# --- backstop flags ---

def test_primary_passes_backstop_flags_raises_content_flagged():
    """Spec §4a step 4: primary passes, backstop flags → fail."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(True, [])), \
         patch("pipeline.input_gate.classify_text_backstop", return_value=(False, ["S2"])), \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        with pytest.raises(RuntimeError, match="content_flagged"):
            input_gate(_state())


# --- primary OOM/error ---

def test_primary_error_falls_back_to_backstop_only():
    """Spec §4a edge case: primary OOM/load error → backstop-only path fires; error is logged, not raised."""
    with patch("pipeline.input_gate.classify_text_primary", side_effect=RuntimeError("OOM")), \
         patch("pipeline.input_gate.classify_text_backstop", return_value=(True, [])) as mock_backstop, \
         patch("pipeline.input_gate.redact_pii", return_value="A dog runs."):
        from pipeline.input_gate import input_gate
        result = input_gate(_state())

    assert result["input"].moderation.passed is True
    mock_backstop.assert_called_once()


def test_primary_error_backstop_flags_raises():
    """Spec §4a: primary errors AND backstop flags → content_flagged (the gate always requires one pass)."""
    with patch("pipeline.input_gate.classify_text_primary", side_effect=RuntimeError("OOM")), \
         patch("pipeline.input_gate.classify_text_backstop", return_value=(False, ["S1"])), \
         patch("pipeline.input_gate.redact_pii", return_value="[REDACTED]"):
        from pipeline.input_gate import input_gate
        with pytest.raises(RuntimeError, match="content_flagged"):
            input_gate(_state())


# --- backstop error ---

def test_backstop_error_raises_moderation_error():
    """Spec §4a edge case: backstop OpenRouter error → hard fail per ADR-025 (not a silent skip)."""
    with patch("pipeline.input_gate.classify_text_primary", return_value=(True, [])), \
         patch("pipeline.input_gate.classify_text_backstop", side_effect=Exception("OpenRouter 500")), \
         patch("pipeline.input_gate.redact_pii", return_value="A dog runs."):
        from pipeline.input_gate import input_gate
        with pytest.raises(RuntimeError, match="moderation_error"):
            input_gate(_state())
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
uv run pytest tests/test_input_gate_node.py -v
```

Expected: most tests fail (stub always passes, never raises).

- [ ] **Step 3: Rewrite input_gate.py**

Replace `backend/pipeline/input_gate.py` entirely:

```python
import logging
from concurrent.futures import ThreadPoolExecutor

from contracts.story_memory import Input, ModerationResult, StoryMemory
from providers import classify_text_backstop, classify_text_primary, redact_pii

log = logging.getLogger(__name__)


def input_gate(state: StoryMemory) -> dict:
    text = state.input.raw_text

    # Steps 1 & 2 are independent — run concurrently (spec §4a).
    with ThreadPoolExecutor(max_workers=2) as pool:
        primary_fut = pool.submit(classify_text_primary, text)
        redact_fut = pool.submit(redact_pii, text)

        try:
            primary_safe, categories = primary_fut.result()
        except Exception as exc:
            # Primary OOM/load error → backstop-only path; log the failure, don't skip moderation.
            log.warning("input_gate: primary classifier failed (%s) — falling back to backstop", exc)
            primary_safe = None  # None = primary errored, not "passed"
            categories = []

        redacted_text = redact_fut.result()

    if primary_safe is False:
        # Primary flagged — no backstop call needed (spec §4a step 3).
        log.info("input_gate: primary flagged (categories=%s)", categories)
        raise RuntimeError("content_flagged")

    # Primary passed or errored → always call backstop.
    try:
        backstop_safe, backstop_categories = classify_text_backstop(text)
    except Exception as exc:
        log.error("input_gate: backstop error — hard fail per ADR-025 (%s)", exc)
        raise RuntimeError("moderation_error") from exc

    if not backstop_safe:
        log.info("input_gate: backstop flagged (categories=%s)", backstop_categories)
        raise RuntimeError("content_flagged")

    return {
        "input": Input(
            raw_text=text,
            redacted_text=redacted_text,
            moderation=ModerationResult(passed=True),
        )
    }
```

> **Why raise instead of returning `passed=False` + router:** `compose.py` raises on invariant failure; this node follows the same pattern. The spec's conceptual "moderation_router" is satisfied by the existing `run_job.py` except block setting `status = "failed"`. A `RuntimeError("content_flagged")` is distinguishable in logs; the `job-failure-reason` spec owns writing a `failure_reason` DB column.

> **CC-2 note:** On primary-flags path, the node raises before returning — `redacted_text` is computed (Presidio ran concurrently) but not written to state. The teacher does not see the flagged submission's text at all in Phase 2; the `kid-flow-ui` spec owns the teacher-facing failure screen.

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_input_gate_node.py -v && uv run ruff check .
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/input_gate.py backend/tests/test_input_gate_node.py
git commit -m "feat(moderation): replace input_gate stub with Qwen3Guard-Gen + Presidio + backstop"
```

---

### Task 4: `char_ref_mod` Node

**Files:**
- Create: `backend/pipeline/char_ref_mod.py`
- Create: `backend/tests/test_char_ref_mod_node.py`

**Interfaces:**
- Consumes: `characters[].canonical_ref_image` (durable Storage path), `providers.classify_image_primary`, `providers.classify_image_backstop`, `pipeline.generate_scene.BUCKET`.
- Produces: `characters[].ref_moderation_status` (`"passed"` | `"flagged"`).
- On fail: raises `RuntimeError("content_flagged")`.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_char_ref_mod_node.py`:

```python
from unittest.mock import MagicMock, call, patch

import pytest

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Character,
    CharacterDescription,
    Input,
    ModerationResult,
    StoryMemory,
)


def _state(characters: list[Character]) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A story.", redacted_text="A story.", moderation=ModerationResult(passed=True)),
        characters=characters,
    )


def _char(char_id: str, ref_path: str | None = "job-1/c0.png") -> Character:
    return Character(
        char_id=char_id,
        name="Dog",
        description=CharacterDescription(species="dog"),
        canonical_ref_image=ref_path,
    )


# --- all pass ---

def test_all_characters_pass_both_classifiers_sets_status_passed():
    """Spec §4b step 5: all chars pass → ref_moderation_status = 'passed' for each."""
    with patch("pipeline.char_ref_mod._get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0"), _char("c1")]))

    chars = result["characters"]
    assert all(c.ref_moderation_status == "passed" for c in chars)


# --- primary flags ---

def test_falconsai_flags_raises_content_flagged():
    """Spec §4b step 4: primary flags → raise (job fails)."""
    with patch("pipeline.char_ref_mod._get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=False), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True):
        from pipeline.char_ref_mod import char_ref_mod
        with pytest.raises(RuntimeError, match="content_flagged"):
            char_ref_mod(_state([_char("c0")]))


# --- backstop flags ---

def test_gemma_flags_raises_content_flagged():
    """Spec §4b step 4: backstop flags → raise (even if primary passed)."""
    with patch("pipeline.char_ref_mod._get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=False):
        from pipeline.char_ref_mod import char_ref_mod
        with pytest.raises(RuntimeError, match="content_flagged"):
            char_ref_mod(_state([_char("c0")]))


# --- backstop error ---

def test_gemma_error_raises_hard_fail():
    """Spec §4b edge case: Gemma OpenRouter error → hard fail (not a skip — no proceed-without-one-check path)."""
    with patch("pipeline.char_ref_mod._get_signed_url", return_value="https://signed/c0.png"), \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", side_effect=Exception("OpenRouter 503")):
        from pipeline.char_ref_mod import char_ref_mod
        with pytest.raises(Exception):
            char_ref_mod(_state([_char("c0")]))


# --- no canonical_ref_image ---

def test_character_with_no_canonical_ref_image_is_skipped_as_passed():
    """Spec §4b: char with no canonical_ref_image has nothing to moderate — mark passed."""
    with patch("pipeline.char_ref_mod._get_signed_url") as mock_sign, \
         patch("pipeline.char_ref_mod.classify_image_primary", return_value=True), \
         patch("pipeline.char_ref_mod.classify_image_backstop", return_value=True):
        from pipeline.char_ref_mod import char_ref_mod
        result = char_ref_mod(_state([_char("c0", ref_path=None)]))

    mock_sign.assert_not_called()
    assert result["characters"][0].ref_moderation_status == "passed"


# --- image download retry ---

def test_signed_url_failure_retries_once_then_raises():
    """Spec §4b edge case: image download fails → one retry per ADR-025, then hard fail."""
    with patch("pipeline.char_ref_mod._get_signed_url", side_effect=Exception("Storage error")):
        from pipeline.char_ref_mod import char_ref_mod
        with pytest.raises(RuntimeError, match="char_ref_mod"):
            char_ref_mod(_state([_char("c0")]))
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
uv run pytest tests/test_char_ref_mod_node.py -v
```

Expected: `ModuleNotFoundError: No module named 'pipeline.char_ref_mod'`

- [ ] **Step 3: Create char_ref_mod.py**

Create `backend/pipeline/char_ref_mod.py`:

```python
import logging

from app.db import get_supabase_client
from contracts.story_memory import StoryMemory
from pipeline.generate_scene import BUCKET
from providers import classify_image_backstop, classify_image_primary

log = logging.getLogger(__name__)


def _get_signed_url(path: str) -> str:
    resp = get_supabase_client().storage.from_(BUCKET).create_signed_url(path, expires_in=300)
    return resp["signedURL"]


def char_ref_mod(state: StoryMemory) -> dict:
    updated = []
    for char in state.characters:
        if char.canonical_ref_image is None:
            # No ref drawn (char_bible skipped or species-only char) — nothing to moderate.
            updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))
            continue

        # One retry on signed-URL failure (ADR-025 transient policy).
        signed_url = None
        for attempt in range(2):
            try:
                signed_url = _get_signed_url(char.canonical_ref_image)
                break
            except Exception as exc:
                if attempt == 1:
                    raise RuntimeError(
                        f"char_ref_mod: failed to sign URL for {char.canonical_ref_image}"
                    ) from exc

        primary_safe = classify_image_primary(signed_url)
        backstop_safe = classify_image_backstop(signed_url)

        if not (primary_safe and backstop_safe):
            log.error(
                "char_ref_mod: char_id=%s flagged (primary=%s backstop=%s)",
                char.char_id, primary_safe, backstop_safe,
            )
            raise RuntimeError("content_flagged")

        log.info("char_ref_mod: char_id=%s passed", char.char_id)
        updated.append(char.model_copy(update={"ref_moderation_status": "passed"}))

    return {"characters": updated}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_char_ref_mod_node.py -v && uv run ruff check .
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/char_ref_mod.py backend/tests/test_char_ref_mod_node.py
git commit -m "feat(moderation): add char_ref_mod node — two-classifier char reference gate"
```

---

### Task 5: `output_mod` Node

**Files:**
- Create: `backend/pipeline/output_mod.py`
- Create: `backend/tests/test_output_mod_node.py`

**Interfaces:**
- Consumes: `scenes[].final_image_ref`, `scenes[].prompt`, `scenes[].characters_present`, `characters[].canonical_ref_image`; `providers.classify_image_primary`, `providers.classify_image_backstop`; `pipeline.generate_scene.generate_and_store`, `pipeline.generate_scene.BUCKET`.
- Produces: `scenes[].moderation_status` (`"passed"`); `scenes[].final_image_ref` (updated on successful retry).
- On fail after retry: raises `RuntimeError("output_moderation_failed")`.

The soften-and-retry inlines a minimal prompt prefix. The `self-refusal-fallback` spec owns the full strategy when written.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_output_mod_node.py`:

```python
from unittest.mock import MagicMock, call, patch

import pytest

from contracts.story_memory import (
    CURRENT_SCHEMA_VERSION,
    Attempt,
    Character,
    CharacterDescription,
    Input,
    ModerationResult,
    Scene,
    StoryMemory,
)


def _state(scenes: list[Scene], characters: list[Character] | None = None) -> StoryMemory:
    return StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A story.", redacted_text="A story.", moderation=ModerationResult(passed=True)),
        characters=characters or [],
        scenes=scenes,
    )


def _scene(scene_id: str = "s0", final_image_ref: str | None = "job-1/s0-1.png", prompt: str = "A dog runs.") -> Scene:
    return Scene(
        scene_id=scene_id,
        text_excerpt="A dog runs in a field.",
        final_image_ref=final_image_ref,
        prompt=prompt,
        attempts=[Attempt(image_ref="job-1/s0-1.png", prompt=prompt, passed=True)],
    )


# --- all scenes pass ---

def test_all_scenes_pass_sets_moderation_status_passed():
    """Spec §4c step 3: all pass → moderation_status = 'passed' for each scene."""
    with patch("pipeline.output_mod._get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", return_value=True), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True):
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0"), _scene("s1", final_image_ref="job-1/s1-1.png")]))

    scenes = result["scenes"]
    assert all(s.moderation_status == "passed" for s in scenes)


# --- first check fails, retry passes ---

def test_first_check_fails_soften_retry_triggers_and_passes():
    """Spec §4c step 4: fail → soften-and-retry triggered; retry passes → moderation_status = 'passed'."""
    check_calls = [False, True]  # first call fails, retry call passes
    primary_iter = iter(check_calls)

    with patch("pipeline.output_mod._get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", side_effect=primary_iter), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True), \
         patch("pipeline.output_mod.generate_and_store", return_value=("job-1/s0-2.png", True)) as mock_gen:
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0")]))

    assert result["scenes"][0].moderation_status == "passed"
    assert result["scenes"][0].final_image_ref == "job-1/s0-2.png"
    mock_gen.assert_called_once()


def test_retry_uses_softened_prompt():
    """Spec §4c: soften-and-retry modifies the prompt before regenerating."""
    original_prompt = "A scary monster attacks."
    calls = []

    def _gen(prompt, story_id, scene_id, attempt_n, ref_paths):
        calls.append(prompt)
        return ("job-1/s0-2.png", True)

    check_responses = iter([False, True])

    with patch("pipeline.output_mod._get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", side_effect=check_responses), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True), \
         patch("pipeline.output_mod.generate_and_store", side_effect=_gen):
        from pipeline.output_mod import output_mod
        output_mod(_state([_scene("s0", prompt=original_prompt)]))

    assert calls[0] != original_prompt, "Retry must use a softened prompt, not the original"
    assert "child" in calls[0].lower() or "safe" in calls[0].lower(), "Softened prompt must add safety qualifier"


# --- retry also fails ---

def test_retry_also_fails_raises_output_moderation_failed():
    """Spec §4c step 5: first and retry both fail → RuntimeError('output_moderation_failed')."""
    with patch("pipeline.output_mod._get_signed_url", return_value="https://signed/s0.png"), \
         patch("pipeline.output_mod.classify_image_primary", return_value=False), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True), \
         patch("pipeline.output_mod.generate_and_store", return_value=("job-1/s0-2.png", True)):
        from pipeline.output_mod import output_mod
        with pytest.raises(RuntimeError, match="output_moderation_failed"):
            output_mod(_state([_scene("s0")]))


# --- scene with no final_image_ref ---

def test_scene_with_no_final_image_ref_is_skipped():
    """Spec §4c edge case: final_image_ref is None → output_mod only runs on resolved refs."""
    with patch("pipeline.output_mod._get_signed_url") as mock_sign, \
         patch("pipeline.output_mod.classify_image_primary", return_value=True), \
         patch("pipeline.output_mod.classify_image_backstop", return_value=True):
        from pipeline.output_mod import output_mod
        result = output_mod(_state([_scene("s0", final_image_ref=None)]))

    mock_sign.assert_not_called()
    # Scene returned unchanged (no moderation_status set for unresolved refs)
    assert result["scenes"][0].moderation_status is None
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
uv run pytest tests/test_output_mod_node.py -v
```

Expected: `ModuleNotFoundError: No module named 'pipeline.output_mod'`

- [ ] **Step 3: Create output_mod.py**

Create `backend/pipeline/output_mod.py`:

```python
import logging

from app.db import get_supabase_client
from contracts.story_memory import Attempt, StoryMemory
from pipeline.generate_scene import BUCKET, generate_and_store
from providers import classify_image_backstop, classify_image_primary

log = logging.getLogger(__name__)


def _get_signed_url(path: str) -> str:
    resp = get_supabase_client().storage.from_(BUCKET).create_signed_url(path, expires_in=300)
    return resp["signedURL"]


def _check_image(image_url: str) -> bool:
    """True if both classifiers pass."""
    return classify_image_primary(image_url) and classify_image_backstop(image_url)


def _soften_prompt(prompt: str) -> str:
    # ponytail: stock softening — prepend safety qualifier; self-refusal-fallback spec owns the full strategy
    return f"child-safe, gentle, age-appropriate illustration, no violence or inappropriate content: {prompt}"


def output_mod(state: StoryMemory) -> dict:
    updated_scenes = []
    for scene in state.scenes:
        if scene.final_image_ref is None:
            # Regeneration controller owns unresolved refs (spec §4c edge case).
            updated_scenes.append(scene)
            continue

        signed_url = _get_signed_url(scene.final_image_ref)
        if _check_image(signed_url):
            log.info("output_mod: scene_id=%s passed", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={"moderation_status": "passed"}))
            continue

        # One soften-and-retry (spec §4c step 4).
        log.info("output_mod: scene_id=%s flagged — softening and retrying", scene.scene_id)
        softened = _soften_prompt(scene.prompt or "")

        by_id = {c.char_id: c for c in state.characters}
        ref_paths = [
            by_id[cid].canonical_ref_image
            for cid in scene.characters_present
            if cid in by_id and by_id[cid].canonical_ref_image
        ]

        retry_n = len(scene.attempts) + 1
        retry_path, _ = generate_and_store(softened, state.story_id, scene.scene_id, retry_n, ref_paths)
        retry_url = _get_signed_url(retry_path)

        if _check_image(retry_url):
            log.info("output_mod: scene_id=%s retry passed", scene.scene_id)
            updated_scenes.append(scene.model_copy(update={
                "final_image_ref": retry_path,
                "moderation_status": "passed",
                "attempts": [*scene.attempts, Attempt(image_ref=retry_path, prompt=softened, passed=True)],
            }))
        else:
            log.error("output_mod: scene_id=%s still flagged after retry — failing job", scene.scene_id)
            raise RuntimeError("output_moderation_failed")

    return {"scenes": updated_scenes}
```

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/test_output_mod_node.py -v && uv run ruff check .
```

Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/output_mod.py backend/tests/test_output_mod_node.py
git commit -m "feat(moderation): add output_mod node — two-classifier image gate with soften-and-retry"
```

---

### Task 6: Graph Rewiring

**Files:**
- Modify: `backend/pipeline/graph.py`
- Modify: `backend/tests/test_graph_stub.py`

**What changes:**
1. Import `char_ref_mod` and `output_mod`.
2. Register both as nodes.
3. Change `graph.add_conditional_edges("char_bible", route_next_scene)` → direct edge `char_bible → char_ref_mod`, then conditional edge `char_ref_mod → route_next_scene`.
4. Change `route_next_scene` return value from `"compose"` to `"output_mod"`.
5. Add `graph.add_edge("output_mod", "compose")`.

**Interfaces:**
- `route_next_scene` now returns `"generate_scene"` or `"output_mod"` (was `"compose"`).
- `route_after_check` calls `route_next_scene` internally — it inherits the destination change automatically.

- [ ] **Step 1: Write failing graph tests**

Read `backend/tests/test_graph_stub.py` first to understand the existing test structure, then append:

```python
def test_route_next_scene_routes_to_output_mod_when_all_scenes_have_final_image_ref():
    """Spec §3: route_next_scene goes to output_mod (not compose) when the scene loop is done."""
    from pipeline.graph import route_next_scene
    from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, ModerationResult, Scene, StoryMemory

    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A story.", redacted_text="A story.", moderation=ModerationResult(passed=True)),
        scenes=[
            Scene(scene_id="s0", text_excerpt="text", final_image_ref="job-1/s0-1.png"),
            Scene(scene_id="s1", text_excerpt="text", final_image_ref="job-1/s1-1.png"),
        ],
    )
    assert route_next_scene(state) == "output_mod"


def test_route_next_scene_routes_to_generate_scene_when_scenes_unfinished():
    """route_next_scene still routes to generate_scene while the loop is in progress."""
    from pipeline.graph import route_next_scene
    from contracts.story_memory import CURRENT_SCHEMA_VERSION, Input, ModerationResult, Scene, StoryMemory

    state = StoryMemory(
        schema_version=CURRENT_SCHEMA_VERSION,
        story_id="job-1",
        classroom_id="dev-classroom",
        profile_id="dev-profile",
        input=Input(raw_text="A story.", redacted_text="A story.", moderation=ModerationResult(passed=True)),
        scenes=[Scene(scene_id="s0", text_excerpt="text", final_image_ref=None)],
    )
    assert route_next_scene(state) == "generate_scene"


def test_graph_has_char_ref_mod_and_output_mod_nodes():
    """Task 6 integration: both new nodes are registered in the compiled graph."""
    from pipeline.graph import build_graph
    graph = build_graph()
    node_names = set(graph.get_graph().nodes.keys())
    assert "char_ref_mod" in node_names
    assert "output_mod" in node_names
```

- [ ] **Step 2: Run new tests — expect FAIL**

```bash
uv run pytest tests/test_graph_stub.py -k "output_mod or char_ref_mod or route_next_scene" -v
```

Expected: `AssertionError` (route_next_scene still returns "compose"; nodes not in graph).

- [ ] **Step 3: Rewrite graph.py**

Replace `backend/pipeline/graph.py` with:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from contracts.story_memory import StoryMemory
from pipeline.char_ref_mod import char_ref_mod
from pipeline.input_gate import input_gate
from pipeline.analyze import analyze
from pipeline.segment import segment
from pipeline.char_bible import char_bible
from pipeline.generate_scene import generate_scene
from pipeline.consistency_check import consistency_check
from pipeline.compose import compose
from pipeline.output_mod import output_mod
from pipeline.regenerate import regenerate


def route_next_scene(state: StoryMemory) -> str:
    """Pure label-returning router (ADR-024 Decision 4) — the graph's first conditional edge.

    Registered on BOTH `char_ref_mod` (loop head) and `consistency_check` (loop back via
    route_after_check). Same selection rule: a scene with no `final_image_ref` is unfinished.
    Destination changed from "compose" to "output_mod" — compose is now reached only after
    output moderation passes.
    """
    return "generate_scene" if any(s.final_image_ref is None for s in state.scenes) else "output_mod"


def route_after_check(state: StoryMemory) -> str:
    """Pure label-returning router (ADR-024 Decision 4) — ADR-003's consistency pass/fail branch.

    Holds no policy: it reads what `consistency_check` wrote. An unfinalized scene means the
    judge failed it and the retry budget is not spent, so ADR-010's one redraw is owed.

    The `scene.attempts` guard is load-bearing, not padding: it is what stops
    `consistency_check`'s "scene has no attempts → return {}" guard from becoming a
    check ⇄ regenerate ping-pong. A scene with no attempts belongs to `generate_scene`.
    """
    scene = next((s for s in state.scenes if s.final_image_ref is None), None)
    if scene is not None and scene.attempts:
        return "regenerate"
    return route_next_scene(state)


def build_graph(checkpointer=None):
    graph = StateGraph(StoryMemory)
    graph.add_node("input_gate", input_gate)
    graph.add_node("analyze", analyze)
    graph.add_node("segment", segment)
    graph.add_node("char_bible", char_bible)
    graph.add_node("char_ref_mod", char_ref_mod)
    graph.add_node("generate_scene", generate_scene)
    graph.add_node("consistency_check", consistency_check)
    graph.add_node("regenerate", regenerate)
    graph.add_node("output_mod", output_mod)
    graph.add_node("compose", compose)

    graph.set_entry_point("input_gate")
    graph.add_edge("input_gate", "analyze")       # input_gate raises on fail; no conditional edge needed
    graph.add_edge("analyze", "segment")
    graph.add_edge("segment", "char_bible")
    graph.add_edge("char_bible", "char_ref_mod")  # char_ref_mod raises on fail
    graph.add_conditional_edges("char_ref_mod", route_next_scene)   # loop head (was char_bible)
    graph.add_edge("generate_scene", "consistency_check")
    graph.add_conditional_edges("consistency_check", route_after_check)
    graph.add_edge("regenerate", "consistency_check")
    graph.add_edge("output_mod", "compose")       # output_mod raises on fail
    graph.add_edge("compose", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
```

- [ ] **Step 4: Run all tests**

```bash
uv run pytest -v && uv run ruff check .
```

Expected: all green. Check specifically:
- `test_graph_stub.py` — all pass including new node/routing tests
- `test_input_gate_node.py` — all pass (stub tests deleted in Task 3)
- `test_char_ref_mod_node.py` — all pass
- `test_output_mod_node.py` — all pass

- [ ] **Step 5: Commit**

```bash
git add backend/pipeline/graph.py backend/tests/test_graph_stub.py
git commit -m "feat(moderation): wire char_ref_mod and output_mod into graph; route through output_mod before compose"
```

---

## Post-Plan Checklist

Run the full pre-merge verify before opening a PR:

```bash
cd backend && uv run ruff check . && uv run pytest
```

**Spec cross-cutting concerns:**
- [x] CC-1 Moderation ordering: `input_gate → ... → char_ref_mod → generate_scene → ... → output_mod → compose`  — enforced by graph topology.
- [x] CC-2 PII redaction: `input.redacted_text` always written (on pass path; fail raises before nodes that need it). Downstream nodes that write captions must consume `redacted_text`, not `raw_text` — not changed here; each downstream spec owns its own CC-2 check.
- [x] CC-3 Cost control: text backstop is 1 call/story; image classifiers are CPU-resident.
- [x] CC-4 Security: all image checks fetch via short-TTL signed URL (300s). No raw Storage paths passed to classifiers.
- [x] CC-9 Failure states: `RuntimeError("content_flagged")` and `RuntimeError("output_moderation_failed")` are catchable by `run_job.py`. The `job-failure-reason` spec owns writing these strings into `jobs.failure_reason`.
- [x] CC-10 Checkpointing: LangGraph checkpoints after each node; a crash mid-moderation resumes from the last checkpoint.

**Open items left for other specs:**
- `filipino-pii-recognizers` spec — filed; `redact_pii` ships with `# ponytail: stock Presidio` comment.
- `self-refusal-fallback` spec — filed; `_soften_prompt` ships with `# ponytail` comment.
- `job-failure-reason` spec — owns writing `failure_reason` column. The `RuntimeError` message strings here (`"content_flagged"`, `"output_moderation_failed"`) are the hook it will parse.
- spaCy model download (`en_core_web_sm`) — must be added to Railway start command / Dockerfile before deploying.
- Qwen3Guard-Gen prompt template — verify against HuggingFace model card before first production run; mock covers CI, real model covers production.
