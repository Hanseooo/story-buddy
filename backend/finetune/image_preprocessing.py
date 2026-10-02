"""Qwen research inputs matching the pinned trainer's preliminary PIL resize.

LLaMA-Factory 7af9095: MMPluginMixin._preprocess_image and Qwen2VLPlugin.
The model processor still performs patch-aligned resizing after this preparation.
"""
import base64
import math
from io import BytesIO
from pathlib import Path

from PIL import Image

from finetune.train import FIXED_CONFIG_PINS


class ImagePreparationError(ValueError):
    """Invalid research images must abort capture rather than count as model errors."""


def image_data_uri(path: Path) -> str:
    mime = "image/png" if path.suffix.lower() == ".png" else "image/webp"
    try:
        contents = path.read_bytes()
    except OSError as exc:
        raise ImagePreparationError("Qwen image preparation could not read the frozen asset") from exc
    return f"data:{mime};base64," + base64.b64encode(contents).decode()


def prepare_qwen_image_uri(uri: str) -> str:
    """Prepare embedded images only, so a remote URL cannot silently skip the resize."""
    header, separator, encoded = uri.partition(",")
    if not separator or not header.startswith("data:image/") or not header.endswith(";base64"):
        raise ImagePreparationError("Qwen image preparation requires a base64 image data URI")
    try:
        contents = base64.b64decode(encoded, validate=True)
        return _prepare_image(contents)
    except (ValueError, OSError, Image.DecompressionBombError) as exc:
        raise ImagePreparationError("Qwen image preparation failed") from exc


def _prepare_image(contents: bytes) -> str:
    with Image.open(BytesIO(contents)) as source:
        image = source
        max_pixels = FIXED_CONFIG_PINS["image_max_pixels"]
        # These are the pinned trainer's defaults, not additional study parameters.
        min_pixels = 32 * 32
        if image.width * image.height > max_pixels:
            factor = math.sqrt(max_pixels / (image.width * image.height))
            image = image.resize((int(image.width * factor), int(image.height * factor)))
        if image.width * image.height < min_pixels:
            factor = math.sqrt(min_pixels / (image.width * image.height))
            image = image.resize((int(image.width * factor), int(image.height * factor)))
        if image.mode != "RGB":
            image = image.convert("RGB")
        if min(image.width, image.height) < 28:
            image = image.resize((max(image.width, 28), max(image.height, 28)))
        if image.width / image.height > 200:
            image = image.resize((image.height * 180, image.height))
        if image.height / image.width > 200:
            image = image.resize((image.width, image.width * 180))
        output = BytesIO()
        image.save(output, format="PNG")
    return "data:image/png;base64," + base64.b64encode(output.getvalue()).decode()
