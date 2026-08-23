import pytest
from scripts.corpus_storage_telemetry import (
    generate_sample_image,
    encode_image,
    verify_mime_type,
    calculate_byte_statistics,
    calculate_corpus_projections,
    generate_telemetry_report,
)


def test_generate_sample_image():
    img = generate_sample_image(width=1024, height=768, seed=42)
    assert img.size == (1024, 768)
    assert img.mode == "RGB"


def test_encode_and_verify_locked_mixed_formats():
    img = generate_sample_image(width=100, height=100, seed=1)
    png_bytes = encode_image(img, format="PNG")
    webp_bytes = encode_image(img, format="WEBP", quality=82)

    is_png, mime_png = verify_mime_type(png_bytes, expected_format="PNG", expected_size=(100, 100))
    is_webp, mime_webp = verify_mime_type(webp_bytes, expected_format="WEBP", expected_size=(100, 100))

    assert (is_png, mime_png) == (True, "image/png")
    assert (is_webp, mime_webp) == (True, "image/webp")
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert webp_bytes[:4] == b"RIFF" and webp_bytes[8:12] == b"WEBP"

    is_invalid, mime_invalid = verify_mime_type(b"notanimage", expected_format="PNG", expected_size=(1, 1))
    assert is_invalid is False
    assert mime_invalid == "unknown"


def test_calculate_byte_statistics():
    sizes = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    stats = calculate_byte_statistics(sizes)

    assert stats["count"] == 10
    assert stats["min"] == 100
    assert stats["max"] == 1000
    assert stats["mean"] == 550.0
    assert stats["median"] == 550.0
    assert stats["p95"] >= 900.0


def test_calculate_corpus_projections_and_deduplication():
    reference_png = [1_500_000] * 20
    scene_webp = [150_000] * 20

    proj = calculate_corpus_projections(
        reference_png_sizes=reference_png,
        scene_webp_sizes=scene_webp,
        canonical_references=88,
        scene_images=619,
        viewers=3,
    )

    assert proj["canonical_references"] == 88
    assert proj["scene_images"] == 619
    assert proj["total_unique_assets"] == 707
    assert proj["reference_storage_bytes"] == 88 * 1_500_000
    assert proj["scene_storage_bytes"] == 619 * 150_000
    expected = (88 * 1_500_000) + (619 * 150_000)
    assert proj["total_storage_gb"] == pytest.approx(expected / 1024**3)
    assert proj["campaign_egress_gb"] == pytest.approx(3 * expected / 1024**3)
    assert proj["supabase_storage_headroom_gb"] == pytest.approx(1 - expected / 1024**3)


def test_generate_telemetry_report():
    reference_png = [1_400_000, 1_500_000, 1_600_000]
    scene_webp = [140_000, 150_000, 160_000]
    report = generate_telemetry_report(
        reference_png_sizes=reference_png,
        scene_webp_sizes=scene_webp,
        canonical_references=88,
        scene_images=619,
    )

    assert "# Corpus Storage, Generation Telemetry & Cost Smoke Test Report" in report
    assert "Encoded Byte Distribution" in report
    assert "PNG references" in report
    assert "WebP quality 82 scenes" in report
    assert "Storage & Bandwidth Projections" in report
    assert "Supabase quota headroom" in report
    assert "Cloudflare" not in report
    assert "R2" not in report
