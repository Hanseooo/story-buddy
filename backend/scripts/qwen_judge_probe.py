"""Go/no-go probe for the self-hosted Qwen judge on Vast (judge-selector spec US-06, AC-27).

Sends one real identity pair to each Qwen model the server must serve, in the request shape the
backend sends: `consistency_check.JUDGE_PROMPT`, reference image first and page second, the
`SceneVerdict` response format, no OpenRouter `provider` body (SH-03), and one attempt with
`max_retries=0` (OD-03). Prints latency and parsed / not parsed per model. The key is read from
the environment and never printed.

Run from `backend/`, where `app.config.settings` can load (it needs the usual backend env):

    QWEN_JUDGE_BASE_URL=http://<host>:<port>/v1 QWEN_JUDGE_API_KEY=... \
        uv run python -m scripts.qwen_judge_probe

Exit codes: 0 both models listed and both answers parsed; 1 a model is missing from `/v1/models`
or an answer did not parse; 2 no server reached (connection failure, timeout, or bad key).
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from openai import APIConnectionError, AuthenticationError, OpenAI

from pipeline.consistency_check import JUDGE_PROMPT, SceneVerdict, _data_uri
from providers import _one_answer

# The two Qwen judge ids of spec SH-01. Ticket 05 adds them to `app/config.py`; read them from
# there once they exist.
QWEN_MODELS = ("Qwen/Qwen3.5-9B", "seed2_checkpoint140")

# A synthetic validation pair from the committed research page (pair 033b8372e89e4c06,
# character syn-025:c0, "Tito Ben", labelled Same). Never a child's picture.
_DATASET = Path(__file__).resolve().parents[2] / "frontend" / "public" / "research" / "dataset"
DEFAULT_NAME = "Tito Ben"
DEFAULT_REFERENCE = _DATASET / "033b8372e89e4c06-reference.webp"
DEFAULT_PAGE = _DATASET / "033b8372e89e4c06-page.webp"


@dataclass
class ModelResult:
    model: str
    seconds: float
    parsed: bool
    detail: str


def exit_code(listed: set[str], results: list[ModelResult]) -> int:
    """GO only when the server lists every Qwen model (SH-05) and each answer parsed (§7.6)."""
    if not set(QWEN_MODELS) <= listed:
        return 1
    return 0 if results and all(r.parsed for r in results) else 1


def _probe(client: OpenAI, model: str, content: list) -> ModelResult:
    t0 = time.perf_counter()
    try:
        verdict = _one_answer(client, model, content, SceneVerdict, {})
    except APIConnectionError:
        raise
    except Exception as exc:  # any other way the answer failed is "not parsed", with its reason
        return ModelResult(model, time.perf_counter() - t0, False, f"{type(exc).__name__}: {exc}")
    return ModelResult(
        model, time.perf_counter() - t0, True, f"same_character={verdict.same_character}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", default=DEFAULT_NAME, help="character name for JUDGE_PROMPT")
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--page", type=Path, default=DEFAULT_PAGE)
    parser.add_argument("--timeout", type=float, default=120.0, help="seconds per request")
    args = parser.parse_args(argv)

    base_url = os.environ.get("QWEN_JUDGE_BASE_URL")
    api_key = os.environ.get("QWEN_JUDGE_API_KEY")
    if not base_url or not api_key:
        print("QWEN_JUDGE_BASE_URL and QWEN_JUDGE_API_KEY must both be set", file=sys.stderr)
        return 2

    content = [{"type": "text", "text": JUDGE_PROMPT.format(name=args.name)}]
    content += [
        {"type": "image_url", "image_url": {"url": _data_uri(path.read_bytes())}}
        for path in (args.reference, args.page)
    ]
    client = OpenAI(base_url=base_url, api_key=api_key, timeout=args.timeout, max_retries=0)

    print(f"server: {base_url}")
    try:
        listed = {m.id for m in client.models.list()}
        print(f"/v1/models: {', '.join(sorted(listed)) or '(none)'}")
        for model in QWEN_MODELS:
            if model not in listed:
                print(f"MISSING from /v1/models: {model}")
        results = [_probe(client, model, content) for model in QWEN_MODELS if model in listed]
    except AuthenticationError:
        print("connection failure: the server rejected the key (401)")
        return 2
    except APIConnectionError as exc:
        print(f"connection failure: {type(exc).__name__}: {exc}")
        return 2

    for r in results:
        status = "parsed" if r.parsed else "NOT PARSED"
        print(f"{r.model}: {r.seconds:.1f} s, {status} ({r.detail})")
    code = exit_code(listed, results)
    print("GO" if code == 0 else "NO-GO")
    return code


if __name__ == "__main__":
    sys.exit(main())
