"""Zero-cost telemetry for the locked PNG-reference/WebP-scene corpus design."""

import io
import math
import random
import statistics
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def generate_sample_image(width: int = 1024, height: int = 768, seed: int = 0) -> Image.Image:
    """Generate a deterministic illustration-like sample without provider calls."""
    rng = random.Random(seed)
    image = Image.new("RGB", (width, height), (rng.randint(220, 255),) * 3)
    draw = ImageDraw.Draw(image)
    for _ in range(15):
        x0, y0 = rng.randint(0, width), rng.randint(height // 3, height)
        x1, y1 = rng.randint(x0, width + 200), rng.randint(y0, height + 200)
        draw.ellipse([x0, y0, x1, y1], fill=tuple(rng.randint(30, 220) for _ in range(3)))
    for _ in range(30):
        x, y = rng.randint(0, width - 1), rng.randint(0, height - 1)
        draw.rectangle(
            [x, y, min(width, x + rng.randint(5, 250)), min(height, y + rng.randint(5, 250))],
            fill=tuple(rng.randint(0, 255) for _ in range(3)),
        )
    noise = Image.frombytes("L", (width, height), rng.randbytes(width * height))
    return Image.blend(image, Image.merge("RGB", (noise, noise, noise)), alpha=0.15)


def encode_image(image: Image.Image, format: str = "PNG", **kwargs: Any) -> bytes:
    output = io.BytesIO()
    image.save(output, format=format, **kwargs)
    return output.getvalue()


def verify_mime_type(
    image_bytes: bytes,
    expected_format: str,
    expected_size: tuple[int, int] | None = None,
) -> tuple[bool, str]:
    """Verify magic bytes, decode, format, and optional dimensions."""
    image_format = expected_format.upper()
    mime = {"PNG": "image/png", "WEBP": "image/webp"}.get(image_format)
    magic_ok = image_bytes.startswith(b"\x89PNG\r\n\x1a\n") if image_format == "PNG" else (
        image_format == "WEBP" and image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP"
    )
    if mime is None or not magic_ok:
        return False, "unknown"
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image.load()
            if image.format != image_format or (expected_size is not None and image.size != expected_size):
                return False, "unknown"
    except Exception:
        return False, "unknown"
    return True, mime


def calculate_byte_statistics(sizes: list[int]) -> dict[str, float]:
    if not sizes:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0, "count": 0}
    ordered = sorted(sizes)
    return {
        "min": float(ordered[0]),
        "max": float(ordered[-1]),
        "mean": float(statistics.mean(ordered)),
        "median": float(statistics.median(ordered)),
        "p95": float(ordered[min(len(ordered) - 1, math.ceil(0.95 * len(ordered)) - 1)]),
        "count": len(ordered),
    }


def calculate_corpus_projections(
    reference_png_sizes: list[int],
    scene_webp_sizes: list[int],
    canonical_references: int,
    scene_images: int,
    viewers: int = 3,
) -> dict[str, float | int]:
    """Project measured bytes against the locked Supabase design."""
    reference_bytes = int(statistics.mean(reference_png_sizes) * canonical_references) if reference_png_sizes else 0
    scene_bytes = int(statistics.mean(scene_webp_sizes) * scene_images) if scene_webp_sizes else 0
    total_bytes = reference_bytes + scene_bytes
    gib = 1024**3
    return {
        "canonical_references": canonical_references,
        "scene_images": scene_images,
        "total_unique_assets": canonical_references + scene_images,
        "reference_storage_bytes": reference_bytes,
        "scene_storage_bytes": scene_bytes,
        "total_storage_gb": total_bytes / gib,
        "viewers": viewers,
        "campaign_egress_gb": total_bytes * viewers / gib,
        "supabase_storage_headroom_gb": 1.0 - total_bytes / gib,
        "supabase_egress_headroom_gb": 5.0 - total_bytes * viewers / gib,
    }


def generate_telemetry_report(
    reference_png_sizes: list[int],
    scene_webp_sizes: list[int],
    canonical_references: int,
    scene_images: int,
) -> str:
    references = calculate_byte_statistics(reference_png_sizes)
    scenes = calculate_byte_statistics(scene_webp_sizes)
    projection = calculate_corpus_projections(
        reference_png_sizes, scene_webp_sizes, canonical_references, scene_images
    )
    return f"""# Corpus Storage, Generation Telemetry & Cost Smoke Test Report

## Encoded Byte Distribution

| Asset | Count | Sample mean | Sample p95 |
| :--- | ---: | ---: | ---: |
| PNG references | {canonical_references} | {references['mean'] / 1024:.1f} KiB | {references['p95'] / 1024:.1f} KiB |
| WebP quality 82 scenes | {scene_images} | {scenes['mean'] / 1024:.1f} KiB | {scenes['p95'] / 1024:.1f} KiB |

Magic bytes, Pillow decode, format, and dimensions were verified for both samples.

## Storage & Bandwidth Projections

| Measurement | Projection |
| :--- | ---: |
| Reference storage | {projection['reference_storage_bytes'] / 1024**2:.1f} MiB |
| Scene storage | {projection['scene_storage_bytes'] / 1024**2:.1f} MiB |
| Total storage | {projection['total_storage_gb']:.3f} GiB |
| Campaign egress ({projection['viewers']} viewers) | {projection['campaign_egress_gb']:.3f} GiB |

## Supabase quota headroom

Measured headroom is **{projection['supabase_storage_headroom_gb']:.3f} GiB storage** and
**{projection['supabase_egress_headroom_gb']:.3f} GiB campaign egress**. This is a measurement of the
locked design. Insufficient headroom stops the run and requires a separate ADR session.
"""


def main() -> None:
    reference_sizes, scene_sizes = [], []
    for index in range(25):
        image = generate_sample_image(seed=1000 + index)
        reference = encode_image(image, format="PNG")
        scene = encode_image(image, format="WEBP", quality=82)
        assert verify_mime_type(reference, "PNG", image.size) == (True, "image/png")
        assert verify_mime_type(scene, "WEBP", image.size) == (True, "image/webp")
        reference_sizes.append(len(reference))
        scene_sizes.append(len(scene))

    report = generate_telemetry_report(reference_sizes, scene_sizes, 60, 450)
    output = Path(__file__).parents[2] / ".scratch" / "annotation-pilot" / "corpus_storage_telemetry_report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Report successfully generated at: {output}")
    print(report)


if __name__ == "__main__":
    main()
