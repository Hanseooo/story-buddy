"""Regression for the captured Qwen3.5 training/serving resize mismatch."""
import base64
import hashlib
import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

import providers
from finetune import evaluate as ev
from finetune.manifest import ManifestRecord


FIXTURES = Path(__file__).parent / "fixtures"


def test_qwen_requests_match_trainer_pixels_and_gemma_keeps_originals(monkeypatch):
    receipt = json.loads((FIXTURES / "qwen35-resize-scene.json").read_text())
    record = ManifestRecord.model_validate(receipt["record"])
    paths = dict(zip(record.images, (
        FIXTURES / "qwen35-resize-reference.png", FIXTURES / "qwen35-resize-scene.png",
    ), strict=True))
    uris = {name: "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()
            for name, path in paths.items()}
    expected_hashes = [receipt["reference"]["prepared_rgb_pixels_sha256"],
                       receipt["prepared_rgb_pixels_sha256"]]
    requests = []

    def completion(client, model, content, schema, extra_body, **kwargs):
        images = [item["image_url"]["url"] for item in content if item["type"] == "image_url"]
        sizes, pixels = [], []
        for uri in images:
            with Image.open(BytesIO(base64.b64decode(uri.split(",", 1)[1]))) as image:
                sizes.append(image.size)
                pixels.append(hashlib.sha256(image.tobytes()).hexdigest())
        requests.append((model, images, sizes, pixels))
        parsed = schema.model_validate(receipt["record"])
        return SimpleNamespace(id="deterministic-test", choices=[SimpleNamespace(
            message=SimpleNamespace(parsed=parsed, content=parsed.model_dump_json()), logprobs=None,
        )])

    monkeypatch.setattr(providers, "_fetch_completion", completion)
    ev.zero_shot_base_judge(uris.__getitem__)(record)
    ev.finetuned_judge(uris.__getitem__, model="judge-qualification")(record)
    ev.prompted_gemma_judge(uris.__getitem__)(record)
    for _, _, sizes, pixels in requests[:2]:
        assert sizes == [(591, 443), (591, 443)]
        assert pixels == expected_hashes
    assert requests[0][1] == requests[1][1]
    assert requests[2][1] == [uris[path] for path in record.images]
    assert requests[2][2] == [(1024, 768), (1024, 768)]


@pytest.mark.parametrize("uri", [
    None,
    "https://example.invalid/image.png",
    "data:image/png;base64,!invalid!",
    "data:image/png;base64,bm90IGFuIGltYWdl",
])
def test_qwen_preparation_failure_aborts_capture_before_request(monkeypatch, uri):
    receipt = json.loads((FIXTURES / "qwen35-resize-scene.json").read_text())
    # Reuse captured image-pair metadata in the validation capture interface.
    record = ManifestRecord.model_validate(receipt["record"]).model_copy(update={"split": "val"})

    def unexpected_request(*args, **kwargs):
        pytest.fail("Unprepared remote images must fail before a model request")

    monkeypatch.setattr(providers, "_fetch_completion", unexpected_request)

    def load_image(_):
        return uri if uri is not None else ev.image_data_uri(FIXTURES / "missing-image.png")

    with pytest.raises(ValueError, match="Qwen image preparation"):
        ev.capture_predictions(
            [record], "seed_0", ev.finetuned_judge(load_image),
            model_id=ev.BASE_MODEL, prompt_version="4",
        )
