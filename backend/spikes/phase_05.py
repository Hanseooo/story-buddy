"""Phase 0.5 spike — the three probes from ROADMAP. Real models, real money, never in CI.

Needs OPENROUTER_API_KEY and FAL_KEY in backend/.env.

    uv run python -m spikes.phase_05 consistency
    uv run python -m spikes.phase_05 seed
    uv run python -m spikes.phase_05 structured

Probe 1 is the kill criterion and only a human can score it: it writes the reference plus
5 scenes to spikes/out/ for you to eyeball. Pass = "same character" on >= 4 of 5.
"""
import hashlib
import sys
from pathlib import Path

from pydantic import BaseModel

import providers
from app.config import settings

OUT = Path(__file__).parent / "out"

CHARACTER = (
    "Pip, a small round fox cub with oversized ears, a cream chest patch, and one bent "
    "whisker, flat storybook illustration, thick outlines, warm gouache colours"
)
SCENES = [
    "standing on a mossy log looking up at the moon",
    "curled asleep inside a teapot",
    "running through tall grass in the rain",
    "sharing a berry with a beetle",
    "peeking out from behind a mushroom, surprised",
]


def consistency() -> None:
    """Probe 1 — non-human character consistency. THE KILL CRITERION."""
    reference = providers.text_to_image(f"Character reference sheet, full body, plain background. {CHARACTER}")
    _write("reference.png", reference)
    reference_url = providers.upload_reference(reference)
    print(f"reference uploaded: {reference_url}")

    for i, scene in enumerate(SCENES, start=1):
        image = providers.edit_image(
            f"The exact same character from the reference image, {scene}. Keep identity unchanged.",
            [reference_url],
        )
        _write(f"scene-{i}.png", image)

    print(f"\nOpen {OUT} and score each scene against reference.png.")
    print("PASS if >= 4 of 5 read as the same character. FAIL -> re-run against FLUX.1 Kontext [dev].")


def seed() -> None:
    """Probe 2 — is fal.ai's seed actually deterministic? Do not trust the docs."""
    reference_url = providers.upload_reference(_read("reference.png"))
    prompt = f"The exact same character from the reference image, {SCENES[0]}."

    digests = []
    for run in (1, 2):
        image = providers.edit_image(prompt, [reference_url], seed=12345)
        _write(f"seed-run-{run}.png", image)
        digests.append(hashlib.sha256(image).hexdigest())
        print(f"run {run}: {digests[-1]}")

    if digests[0] == digests[1]:
        print("\nPASS: byte-identical. The Phase 3 ablation (ADR-008, CC-7) can rely on seeds.")
    else:
        print("\nFAIL: same seed, different bytes. Phase 3 ablation needs another provider or")
        print("must drop its reproducibility assumption. Record this against CC-7.")


class _Probe(BaseModel):
    character_name: str
    mood: str


def structured() -> None:
    """Probe 3 — do both models honour strict json_schema with require_parameters set?"""
    prompt = "Extract the character name and mood: 'Pip the fox cub was very sleepy.'"

    for model in (settings.text_model, settings.vlm_judge_model):
        try:
            result = providers.structured_text(prompt, _Probe, model=model)
        except Exception as exc:  # noqa: BLE001 — a probe reports failures, it does not raise
            print(f"FAIL {model}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {model}: {result!r}")


def _write(name: str, data: bytes) -> None:
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_bytes(data)
    print(f"wrote {OUT / name}")


def _read(name: str) -> bytes:
    path = OUT / name
    if not path.exists():
        sys.exit(f"{path} missing — run `consistency` first.")
    return path.read_bytes()


PROBES = {"consistency": consistency, "seed": seed, "structured": structured}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PROBES:
        sys.exit(f"usage: python -m spikes.phase_05 [{'|'.join(PROBES)}]")
    PROBES[sys.argv[1]]()
