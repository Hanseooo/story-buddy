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


def test_encode_and_verify_mime_type():
    img = generate_sample_image(width=100, height=100, seed=1)
    png_bytes = encode_image(img, format="PNG")
    webp_bytes = encode_image(img, format="WEBP", quality=85)

    is_png, mime_png = verify_mime_type(png_bytes, expected_format="PNG")
    assert is_png is True
    assert mime_png == "image/png"
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

    is_webp, mime_webp = verify_mime_type(webp_bytes, expected_format="WEBP")
    assert is_webp is True
    assert mime_webp == "image/webp"
    assert webp_bytes[:4] == b"RIFF"
    assert webp_bytes[8:12] == b"WEBP"

    is_invalid, mime_invalid = verify_mime_type(b"notanimage", expected_format="PNG")
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
    sample_png = [1_500_000] * 20  # 1.5 MB each
    sample_webp = [200_000] * 20   # 200 KB each

    proj = calculate_corpus_projections(
        sample_png_sizes=sample_png,
        sample_webp_sizes=sample_webp,
        total_images=707,
        total_stories=88,
        num_annotators=2,
        num_adjudicators=1,
    )

    # Reference deduplication metrics
    assert proj["canonical_references"] == 88
    assert proj["scene_images"] == 619
    assert proj["total_unique_assets"] == 707
    assert proj["naive_total_assets_without_dedup"] == 88 + 619 * 2  # 88 refs + 619 scenes + 619 duplicated refs = 1326

    # Storage metrics
    expected_png_mb = (707 * 1_500_000) / (1024 * 1024)
    expected_webp_mb = (707 * 200_000) / (1024 * 1024)
    assert proj["png_total_mb"] == pytest.approx(expected_png_mb, rel=1e-3)
    assert proj["png_total_gb"] == pytest.approx(expected_png_mb / 1024.0, rel=1e-3)
    assert proj["webp_total_mb"] == pytest.approx(expected_webp_mb, rel=1e-3)

    # Bandwidth (3 viewers: 2 annotators + 1 adjudicator)
    assert proj["png_egress_gb"] == pytest.approx(3 * (expected_png_mb / 1024.0), rel=1e-3)

    # Cost projections ($0.035 / image)
    assert proj["compute_cost_base_usd"] == pytest.approx(707 * 0.035, rel=1e-2)
    assert proj["compute_cost_with_retry_margin_usd"] > proj["compute_cost_base_usd"]

    # Provider recommendations
    assert proj["storage_decision"]["supabase_free_png_status"] == "exceeded"
    assert proj["storage_decision"]["supabase_free_webp_status"] == "within_limit"
    assert proj["storage_decision"]["cloudflare_r2_status"] == "recommended"


def test_generate_telemetry_report():
    sample_png = [1_400_000, 1_500_000, 1_600_000]
    sample_webp = [180_000, 200_000, 220_000]
    report = generate_telemetry_report(
        sample_png_sizes=sample_png,
        sample_webp_sizes=sample_webp,
        total_images=707,
        total_stories=88,
    )

    assert "# Corpus Storage, Generation Telemetry & Cost Smoke Test Report" in report
    assert "Encoded Byte Distribution" in report
    assert "Reference Asset De-duplication" in report
    assert "Storage & Bandwidth Projections" in report
    assert "Cloudflare R2" in report
    assert "fal.ai" in report
