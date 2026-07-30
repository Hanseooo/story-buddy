# Character Bible — Plan A (config + pure functions + the effect helper)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build everything *below* the `char_bible` node — the config field it reads, the two pure functions, and `mint_reference`, the single effect boundary that draws a character reference, judges it, re-rolls up to 3 times, and uploads the winner.

**Architecture:** One file, `backend/pipeline/char_bible.py`, replacing a pass-through stub. Four levels: `char_bible(state)` (Plan B) → `mint_reference(...)` (the one effect boundary — wraps `text_to_image`, `judge`, and the Storage upload) → `reference_prompt` / `best_draw` (pure, no mocks). Two provider calls get deliberately **different** failure policies: `text_to_image` raises (no artifact exists), `judge` degrades to `ref_verdict = None` (the artifact exists and is paid for; only the *check* failed).

**Tech Stack:** Python 3.12, Pydantic v2, pytest + `unittest.mock`, ruff, uv. All vendor calls go through `backend/providers.py`; Storage through `backend/app/db.py`.

**Spec:** `docs/specs/character-bible.md`. Read §4 (behavior) and §6 (tests) before starting. **Plan B** (`2026-07-30-character-bible-b-node.md`) builds the node on top of this and must not be started until this plan is green.

## Global Constraints

- **Run everything from `backend/`.** Verify command: `uv run ruff check . && uv run pytest`. Never `pip`, never `poetry` — `uv` only.
- **`backend/contracts/` MUST NOT be modified.** Every type this needs (`Character`, `CharacterDescription`, `RefVerdict`, `Cost`) already exists. Modifying it fails the spec's Definition of Done.
- **No new contract fields, no `schema_version` bump.**
- **Provider SDKs, endpoints and API keys live in `backend/providers.py` and nowhere else.** Model IDs live in `backend/app/config.py` as env-overridable settings. Never hardcode either at a call site.
- **Every model call is mocked in tests.** No assertion may touch image or verdict *quality* — that is the offline eval harness (Tier B), never CI.
- **`MAX_DRAWS = 3`** (ADR-028). Not 1, not 4.
- **No seed is passed to `text_to_image`.** A fixed seed makes all three draws identical and the re-roll a no-op. CC-7 is knowingly unsatisfied here (spec §5).
- **`canonical_ref_image` is a durable Storage *path*, never a signed URL and never the base64 data URI the judge was shown.**
- Ruff config: `line-length = 120`, default rule set (E4/E7/E9/F). `ruff format` is **not** adopted — do not reformat existing lines.
- Match the surrounding file style: module docstring, `log = logging.getLogger(__name__)`, module-level prompt constants, comments that name the ADR they enforce.

---

### Task 1: `settings.default_style_fragment`

The node needs *a* style fragment to exist. ADR-022's three-preset `style_presets` dict, `style_preset_id` resolution and the picker UI are wholly owned by the `style-presets` spec — **do not build them here.** This task authors exactly one default, the `cel` preset, verbatim from `backend/spikes/phase_05.py:46` where it was authored 2026-07-21.

**Files:**
- Modify: `backend/app/config.py` (append to the model-ID block, after `fal_image_edit_model`)
- Modify: `backend/.env.example` (the "Model overrides" comment block)

**Interfaces:**
- Consumes: nothing.
- Produces: `settings.default_style_fragment: str` — read by `char_bible` in Plan B, Task 4.

No test: this is a config constant with no branch, loop, or parser (AGENTS.md *Verification*, TDD scope). Plan B Task 4's style-fallback test is what proves it is wired.

- [ ] **Step 1: Add the setting**

In `backend/app/config.py`, immediately after the `fal_image_edit_model` line and before the `judge_base_url` comment block:

```python
    # ADR-022's `cel` preset — "the flagship default kids see first" — authored 2026-07-21 in
    # backend/spikes/phase_05.py. This is ADR-007 as originally written (one fixed style). The
    # three-preset `style_presets` dict, `style_preset_id` resolution and the picker UI stay
    # wholly owned by the `style-presets` spec; `char_bible` only needs *a* fragment to exist.
    default_style_fragment: str = (
        "flat cel-shaded cartoon, thick clean black outlines of even weight, bright solid colour fills, "
        "two flat shadow tones, limited palette, no gradients, no glossy highlights, no airbrushing"
    )
```

- [ ] **Step 2: Add the override line**

In `backend/.env.example`, append to the commented model-override block (after the `# FAL_IMAGE_MODEL=...` line):

```
# DEFAULT_STYLE_FRAGMENT=
```

- [ ] **Step 3: Verify it loads**

Run from `backend/`:

```bash
uv run python -c "from app.config import settings; print(settings.default_style_fragment)"
```

Expected: the full `cel` fragment printed on one line, starting `flat cel-shaded cartoon, thick clean black outlines`.

- [ ] **Step 4: Lint**

Run: `uv run ruff check .`
Expected: `All checks passed!`

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/.env.example
git commit -m "feat(config): add default_style_fragment (ADR-022 cel preset)"
```

---

### Task 2: The pure functions — `reference_prompt` and `best_draw`

Both are pure, so they are **not** effect boundaries (MASTER_SPEC §6 rule 1 governs the *effect* seam) and need no mocks at all.

`best_draw` ranks on `len(attributes_present)`, ties → earliest draw. This is `char_bible`'s own rule over `RefVerdict` and is **unrelated** to `regeneration-controller`'s lexicographic scene rule over `VlmVerdict` — different schema, different question. **Do not unify them.**

**Files:**
- Modify: `backend/pipeline/char_bible.py` (currently a 6-line stub — replace it wholesale)
- Test: `backend/tests/test_char_bible_node.py` (create)

**Interfaces:**
- Consumes: `CharacterDescription`, `RefVerdict` from `contracts.story_memory` (already exist — do not modify them).
- Produces:
  - `reference_prompt(description: CharacterDescription, name: str, style_fragment: str) -> str`
  - `best_draw(verdicts: list[RefVerdict]) -> int`
  - `_describe(description: CharacterDescription, name: str) -> str` (module-private; also used by the judge prompt in Task 3)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_char_bible_node.py`:

```python
from contracts.story_memory import CharacterDescription, RefVerdict
from pipeline.char_bible import best_draw, reference_prompt

FRAG = "flat cel-shaded cartoon, thick clean black outlines"


def _verdict(matches: bool, attributes: list[str] | None = None) -> RefVerdict:
    return RefVerdict(
        differences_observed="the scarf is blue, not red",
        matches_description=matches,
        attributes_present=attributes or [],
    )


# --- best_draw (pure) ---

def test_best_draw_ranks_on_attributes_present_length():
    """Spec §4: best-of ranks on len(attributes_present) — lengths 1, 3, 2 → index 1."""
    verdicts = [
        _verdict(False, ["a"]),
        _verdict(False, ["a", "b", "c"]),
        _verdict(False, ["a", "b"]),
    ]
    assert best_draw(verdicts) == 1


def test_best_draw_breaks_ties_toward_the_earliest_draw():
    """Spec §4: ties → earliest draw. Lengths 2, 2, 2 → index 0."""
    verdicts = [_verdict(False, ["a", "b"]) for _ in range(3)]
    assert best_draw(verdicts) == 0


def test_best_draw_returns_zero_when_every_verdict_is_empty():
    """Spec §4 edge case: all attributes_present empty → 0. Deterministic, never arbitrary."""
    verdicts = [_verdict(False), _verdict(False), _verdict(False)]
    assert best_draw(verdicts) == 0


# --- reference_prompt (pure) ---

def test_reference_prompt_contains_every_populated_description_axis():
    description = CharacterDescription(
        species="dog",
        colours=["orange"],
        body_features=["three eyes"],
        clothing=["a red scarf"],
        notes="always smiling",
    )
    prompt = reference_prompt(description, "the orange dog", FRAG)
    for axis in ["dog", "orange", "three eyes", "a red scarf", "always smiling"]:
        assert axis in prompt


def test_reference_prompt_floors_to_the_character_name_on_an_empty_description():
    """Spec §4: CharacterDescription is all-Optional, so a fully empty one is contract-legal
    (a resumed pre-story-analyzer checkpoint could carry one). The prompt floors to the name."""
    prompt = reference_prompt(CharacterDescription(), "the orange dog", FRAG)
    assert "Character: the orange dog\n" in prompt


def test_reference_prompt_always_contains_the_style_fragment():
    """ADR-022: style rides the reference, so the fragment is never optional in this prompt."""
    assert FRAG in reference_prompt(CharacterDescription(), "the orange dog", FRAG)
    assert FRAG in reference_prompt(CharacterDescription(species="dog"), "the orange dog", FRAG)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_char_bible_node.py -v`
Expected: collection error — `ImportError: cannot import name 'best_draw' from 'pipeline.char_bible'`.

- [ ] **Step 3: Write the minimal implementation**

Replace the entire contents of `backend/pipeline/char_bible.py`:

```python
"""The node every other image in the book depends on (spec `docs/specs/character-bible.md`).

Draws one canonical reference per principal character, judges it against the
`CharacterDescription` it came from, re-rolls up to 3 times, and persists the accepted path
plus its verdict. ADR-028 falsified ADR-007's assumption that a reference is correct *because*
it was generated from the description; this node is the gate that makes that failure visible.

It does NOT fix the rate — at the measured draw quality 3 draws still ship an off-spec
reference roughly 42% of the time, now with the verdict persisted instead of silently. The fix
for the rate is swapping `fal_image_model` (ADR-001's named seam), not anything in this file.
"""
import logging

from contracts.story_memory import CharacterDescription, RefVerdict

log = logging.getLogger(__name__)

MAX_DRAWS = 3   # ADR-028. Not ADR-010's 1: a bad scene is one page, a bad reference is every page.

REFERENCE_PROMPT = """\
A single full-body character reference of one character, standing, facing forward, centred on a \
plain neutral background. No other characters, no scenery, no text, no border.

Character: {subject}

Style: {style_fragment}"""


def _describe(description: CharacterDescription, name: str) -> str:
    """The `CharacterDescription` axes as one line. Shared by the draw prompt and the judge
    prompt so they can never drift into describing different characters."""
    axes = [
        description.species,
        ", ".join(description.colours),
        ", ".join(description.body_features),
        ", ".join(description.clothing),
        description.notes,
    ]
    populated = [axis for axis in axes if axis]
    return f"{name} - {'; '.join(populated)}" if populated else name


def reference_prompt(description: CharacterDescription, name: str, style_fragment: str) -> str:
    """Pure. ADR-022: the fragment names a medium and its physical artifacts — it never says
    "beautiful", "8k" or "highly detailed"."""
    return REFERENCE_PROMPT.format(subject=_describe(description, name), style_fragment=style_fragment)


def best_draw(verdicts: list[RefVerdict]) -> int:
    """Pure. Best-of when every draw failed: most attributes present, ties → earliest (ADR-010).

    `char_bible`'s own rule over `RefVerdict`. UNRELATED to `regeneration-controller`'s
    lexicographic scene rule over `VlmVerdict` — different schema, different question. Do not
    unify them.
    """
    return max(range(len(verdicts)), key=lambda i: (len(verdicts[i].attributes_present), -i))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_char_bible_node.py -v`
Expected: 6 passed.

- [ ] **Step 5: Keep the graph importable**

Step 3 replaced the file wholesale, which deleted the `char_bible` function that `pipeline/graph.py` imports — so the whole suite is currently red with `ImportError: cannot import name 'char_bible'`. Append the stub back (temporary scaffolding — Plan B Task 4 replaces the body):

```python
def char_bible(state) -> dict:
    # ponytail: stub — Plan B Task 4 fills this in (select, mint, map, bump cost).
    return {}
```

- [ ] **Step 6: Check nothing else broke**

Run: `uv run ruff check . && uv run pytest`
Expected: `All checks passed!` and every test passes, including `tests/test_graph_stub.py`. **Paste the output into your report — do not claim it.**

- [ ] **Step 7: Commit**

```bash
git add backend/pipeline/char_bible.py backend/tests/test_char_bible_node.py
git commit -m "feat(char_bible): add reference_prompt and best_draw (pure)"
```

---

### Task 3: `mint_reference` — the one effect boundary

This helper wraps **all three** of the node's effects — `text_to_image`, `judge`, and the Storage upload — exactly as `generate_scene.generate_and_store` already bundles generate + store behind one seam. Node and graph tests patch `pipeline.char_bible.mint_reference`; this task's tests patch the three inner calls.

**The two failure policies are deliberate and must not be "fixed" into consistency:**

| Call | Failure | Why |
|---|---|---|
| `text_to_image` | **Raises** → job `failed` | No artifact. Nothing to ship (ADR-025 Decision 1 as written). |
| `judge` | **Degrades** → accept the draw, return `None` | The artifact exists and is paid for. The *check* failed. ADR-010's "always something shippable" governs. |

No node-level retry on either — the OpenAI SDK / fal helper bounded retry is the entire policy (ADR-025 Decision 1).

**Files:**
- Modify: `backend/pipeline/char_bible.py`
- Test: `backend/tests/test_char_bible_node.py`

**Interfaces:**
- Consumes: `reference_prompt`, `best_draw`, `_describe`, `MAX_DRAWS` (Task 2); `providers.text_to_image`, `providers.judge`, `app.db.get_supabase_client`.
  - **Real provider signatures** (the spec's §4 pseudocode abbreviates them):
    - `text_to_image(prompt: str, seed: int | None = None) -> bytes`
    - `judge(prompt: str, image_urls: list[str], schema: type[T], model: str | None = None) -> T`
- Produces: `mint_reference(description: CharacterDescription, name: str, style_fragment: str, story_id: str, char_id: str) -> tuple[str, RefVerdict | None, int]`.
  The third element is the **number of draws made** — the node cannot compute it (the loop is inside the helper) and needs it for invariant 4, so the helper reports it.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_char_bible_node.py`:

```python
from unittest.mock import MagicMock, patch

import pytest

from pipeline.char_bible import mint_reference

DRAWS = [b"draw-1-bytes", b"draw-2-bytes", b"draw-3-bytes"]


def _mint(judge_side_effect, images=None):
    """Runs mint_reference with all three effects patched.

    Returns (result, text_to_image_mock, judge_mock, fake_supabase).
    """
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", side_effect=list(images or DRAWS)) as t2i, \
         patch("pipeline.char_bible.judge", side_effect=judge_side_effect) as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        result = mint_reference(
            CharacterDescription(species="dog", colours=["orange"]),
            "the orange dog",
            FRAG,
            "story-1",
            "c0",
        )
    return result, t2i, judge_mock, fake_supabase


def _uploaded_bytes(fake_supabase) -> bytes:
    return fake_supabase.storage.from_.return_value.upload.call_args.args[1]


def _uploaded_path(fake_supabase) -> str:
    return fake_supabase.storage.from_.return_value.upload.call_args.args[0]


def test_mint_reference_accepts_a_passing_first_draw():
    """Spec §6: one text_to_image call, one judge call, verdict returned unchanged."""
    passing = _verdict(True, ["dog", "orange"])
    (path, verdict, draws), t2i, judge_mock, supabase = _mint([passing])

    assert t2i.call_count == 1
    assert judge_mock.call_count == 1
    assert verdict is passing
    assert draws == 1
    assert _uploaded_bytes(supabase) == b"draw-1-bytes"
    assert path == "story-1/ref-c0.png"


def test_mint_reference_rerolls_until_a_draw_passes():
    """Spec §6: fail → fail → pass yields 3 draws, and the THIRD image's bytes are uploaded."""
    (_, verdict, draws), t2i, _, supabase = _mint(
        [_verdict(False), _verdict(False), _verdict(True, ["dog"])]
    )

    assert t2i.call_count == 3
    assert draws == 3
    assert verdict.matches_description is True
    assert _uploaded_bytes(supabase) == b"draw-3-bytes"


def test_mint_reference_best_of_uploads_the_draw_with_most_attributes_present():
    """Spec §6 exhaustion best-of: attributes_present lengths 1, 3, 2 → the SECOND draw wins.
    Guards the ranking key."""
    (_, verdict, draws), _, _, supabase = _mint([
        _verdict(False, ["a"]),
        _verdict(False, ["a", "b", "c"]),
        _verdict(False, ["a", "b"]),
    ])

    assert _uploaded_bytes(supabase) == b"draw-2-bytes"
    assert draws == 3
    # A FAILING verdict is persisted — loud, never a placeholder, never a failed job (ADR-010).
    assert verdict.matches_description is False


def test_mint_reference_best_of_ties_go_to_the_earliest_draw():
    """Spec §6: lengths 2, 2, 2 → the FIRST draw's bytes are uploaded."""
    (_, _, _), _, _, supabase = _mint([
        _verdict(False, ["a", "b"]),
        _verdict(False, ["c", "d"]),
        _verdict(False, ["e", "f"]),
    ])

    assert _uploaded_bytes(supabase) == b"draw-1-bytes"


def test_mint_reference_never_draws_more_than_three_times():
    """Spec §6 cap (ADR-028): never more than 3 text_to_image calls, however many verdicts fail."""
    (_, _, draws), t2i, _, _ = _mint([_verdict(False) for _ in range(3)])

    assert t2i.call_count == 3
    assert draws == 3


def test_mint_reference_degrades_to_a_null_verdict_when_the_judge_fails():
    """Spec §4 two-policies table: the artifact exists and is paid for, only the CHECK failed.
    Accept the draw, return None, and STOP re-rolling — exactly one text_to_image call."""
    (path, verdict, draws), t2i, _, supabase = _mint(RuntimeError("openrouter 500"))

    assert verdict is None
    assert draws == 1
    assert t2i.call_count == 1
    assert path == "story-1/ref-c0.png"
    assert _uploaded_bytes(supabase) == b"draw-1-bytes"


def test_mint_reference_propagates_a_text_to_image_failure():
    """Spec §6 (guards ADR-025 Decision 1): no artifact exists, so there is nothing to ship.
    The exception propagates and the job fails. No node-level retry."""
    fake_supabase = MagicMock()
    with patch("pipeline.char_bible.text_to_image", side_effect=RuntimeError("fal 503")), \
         patch("pipeline.char_bible.judge") as judge_mock, \
         patch("pipeline.char_bible.get_supabase_client", return_value=fake_supabase):
        with pytest.raises(RuntimeError, match="fal 503"):
            mint_reference(CharacterDescription(species="dog"), "the dog", FRAG, "story-1", "c0")

    judge_mock.assert_not_called()
    fake_supabase.storage.from_.return_value.upload.assert_not_called()


def test_mint_reference_uploads_to_the_exact_reference_path():
    """Spec §6 upload target: `{story_id}/ref-{char_id}.png`, in the storybook-images bucket."""
    (path, _, _), _, _, supabase = _mint([_verdict(True)])

    assert path == "story-1/ref-c0.png"
    assert _uploaded_path(supabase) == "story-1/ref-c0.png"
    supabase.storage.from_.assert_called_with("storybook-images")


def test_mint_reference_shows_the_judge_a_data_uri_never_a_url():
    """Spec §6 (guards invariant 5 and the CC-4 posture): the judge sees base64, never a signed
    URL, and what is PERSISTED is the path, never the data URI."""
    (path, _, _), _, judge_mock, _ = _mint([_verdict(True)])

    image_urls = judge_mock.call_args.args[1]
    assert len(image_urls) == 1
    assert image_urls[0].startswith("data:image/png;base64,")
    assert not image_urls[0].startswith("http")
    assert not path.startswith("data:")
    assert not path.startswith("http")


def test_mint_reference_reports_a_draw_count_equal_to_the_provider_calls():
    """Spec §6: the count the helper reports equals the number of text_to_image calls.
    Invariant 4 rides on this — the node cannot compute it, the loop is in here."""
    for side_effect, expected in [
        ([_verdict(True)], 1),
        ([_verdict(False), _verdict(True)], 2),
        ([_verdict(False), _verdict(False), _verdict(False)], 3),
    ]:
        (_, _, draws), t2i, _, _ = _mint(side_effect)
        assert draws == t2i.call_count == expected


def test_mint_reference_passes_no_seed_to_the_image_model():
    """Spec §4 "No seed, by necessity": a fixed seed makes all three draws identical and the
    re-roll a no-op. CC-7 is unsatisfied here as a consequence of the mechanism (§5)."""
    _, t2i, _, _ = _mint([_verdict(False), _verdict(False), _verdict(False)])

    for call in t2i.call_args_list:
        assert call.kwargs.get("seed") is None
        assert len(call.args) == 1   # prompt only — no positional seed
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_char_bible_node.py -v`
Expected: collection error — `ImportError: cannot import name 'mint_reference' from 'pipeline.char_bible'`.

- [ ] **Step 3: Write the implementation**

In `backend/pipeline/char_bible.py`, the import block after Task 2 is `import logging` + `from contracts.story_memory import CharacterDescription, RefVerdict`. Replace that block with this one — three lines are new, the two existing ones are unchanged:

```python
import base64
import logging

from app.db import get_supabase_client
from contracts.story_memory import CharacterDescription, RefVerdict
from providers import judge, text_to_image
```

Add after the `REFERENCE_PROMPT` constant:

```python
BUCKET = "storybook-images"

# Reason-then-score (ADR-004) applies to EVERY judge call. `RefVerdict` already declares
# `differences_observed` before `matches_description`, and `providers._assert_field_order`
# enforces the ordering on the wire — this prompt only has to ask in the same order.
JUDGE_PROMPT = """\
This image is meant to be a character reference drawn from the description below.

Description: {subject}

First describe every difference you observe between the image and the description. Then say \
whether the image matches the description, and list which of the described attributes are \
actually present in the image."""
```

And add these three functions after `best_draw`:

```python
def _data_uri(image: bytes) -> str:
    """The judge is shown base64, never a signed URL (CC-4). What is PERSISTED is the path.

    ponytail: inline base64. Risk recorded in spec §8 — a 1024^2 PNG is ~1.9 MB encoded and
    `providers._run_fal` hardcodes png. If OpenRouter rejects the body on the first real call,
    the fix is a signed-URL helper in `app/db.py` — a deliberate change, not a hotfix.
    """
    return "data:image/png;base64," + base64.b64encode(image).decode()


def _upload(image: bytes, story_id: str, char_id: str) -> str:
    path = f"{story_id}/ref-{char_id}.png"
    get_supabase_client().storage.from_(BUCKET).upload(
        path, image, {"content-type": "image/png", "upsert": "true"}
    )
    return path


def mint_reference(
    description: CharacterDescription,
    name: str,
    style_fragment: str,
    story_id: str,
    char_id: str,
) -> tuple[str, RefVerdict | None, int]:
    """The node's ONE effect boundary (MASTER_SPEC §6): draw, judge, re-roll, upload.

    Returns `(storage_path, verdict, draws_made)`. The draw count is reported rather than
    inferred because the loop lives in here and the node needs it for CC-3 (invariant 4).

    The loop is node-internal and adds no graph edge and no super-step (ADR-028 Decision 3),
    so ADR-003 and ADR-024 are unamended by it.
    """
    prompt = reference_prompt(description, name, style_fragment)
    judge_prompt = JUDGE_PROMPT.format(subject=_describe(description, name))
    candidates: list[tuple[bytes, RefVerdict]] = []
    draws = 0

    for _ in range(MAX_DRAWS):
        # No seed: a fixed one makes every draw identical and the re-roll a no-op (§4).
        # A hard failure raises → job `failed` with an ADR-025 `failure_reason`. No artifact
        # exists, so there is nothing to ship and no node-level retry.
        image = text_to_image(prompt)
        draws += 1
        try:
            verdict = judge(judge_prompt, [_data_uri(image)], RefVerdict)
        except Exception:
            # DIFFERENT policy from text_to_image above, deliberately (§4). The artifact exists
            # and is paid for; only the CHECK failed. `None` stays honest and is distinguishable
            # from a FAILED verdict (matches_description=False). Do not "fix" this asymmetry.
            log.warning(
                "char_bible: %s judge failed on draw %d — accepting unchecked, ref_verdict=None",
                char_id, draws, exc_info=True,
            )
            return _upload(image, story_id, char_id), None, draws

        # CC-5: a wrong character downstream traces back to a specific reference and draw.
        log.info(
            "char_bible: %s draw %d/%d matches=%s attributes=%s",
            char_id, draws, MAX_DRAWS, verdict.matches_description, verdict.attributes_present,
        )
        if verdict.matches_description:
            log.info("char_bible: %s accepted draw %d", char_id, draws)
            return _upload(image, story_id, char_id), verdict, draws
        candidates.append((image, verdict))

    winner = best_draw([v for _, v in candidates])
    log.warning(
        "char_bible: %s all %d draws failed — best-of picked draw %d, FAILING verdict persisted",
        char_id, draws, winner + 1,
    )
    image, verdict = candidates[winner]
    return _upload(image, story_id, char_id), verdict, draws
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_char_bible_node.py -v`
Expected: 17 passed (6 from Task 2 + 11 here).

- [ ] **Step 5: Run the full verify**

Run from `backend/`: `uv run ruff check . && uv run pytest`
Expected: `All checks passed!` and every test green. **Paste the output — do not claim it.**

- [ ] **Step 6: Commit**

```bash
git add backend/pipeline/char_bible.py backend/tests/test_char_bible_node.py
git commit -m "feat(char_bible): add mint_reference acceptance loop (ADR-028)"
```

---

## Done when

- `settings.default_style_fragment` exists and loads.
- `reference_prompt`, `best_draw`, `mint_reference` exist in `backend/pipeline/char_bible.py`; `char_bible` is still the temporary stub from Task 2 Step 6.
- 17 tests in `backend/tests/test_char_bible_node.py` pass.
- `uv run ruff check . && uv run pytest` is green from `backend/`, **with the output shown**.
- `backend/contracts/` is untouched.

Then start `docs/specs/plans/2026-07-30-character-bible-b-node.md`.
