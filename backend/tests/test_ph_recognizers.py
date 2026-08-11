"""Runs against real Presidio (CPU-local, fast, no mock) — the thing under test is the
pattern/entity-extraction behavior itself, which a mock can't stand in for (spec §6)."""
from presidio_analyzer import AnalyzerEngine

from ph_recognizers import ph_recognizers
from tests.fixtures.pii_cases import MUST_NOT_REDACT, MUST_REDACT


def _analyzer() -> AnalyzerEngine:
    from presidio_analyzer.nlp_engine import SpacyNlpEngine
    nlp_engine = SpacyNlpEngine(models=[{"lang_code": "en", "model_name": "en_core_web_sm"}])
    engine = AnalyzerEngine(nlp_engine=nlp_engine)
    for recognizer in ph_recognizers():
        engine.registry.add_recognizer(recognizer)
    return engine


def _ph_entity_types(engine: AnalyzerEngine, text: str) -> set[str]:
    results = engine.analyze(text=text, language="en")
    return {r.entity_type for r in results if r.entity_type.startswith("PH_")}


def test_must_redact_cases_find_every_expected_entity_type():
    engine = _analyzer()
    for text, expected_types in MUST_REDACT:
        found = _ph_entity_types(engine, text)
        assert expected_types <= found, f"{text!r}: expected {expected_types}, found {found}"


def test_must_not_redact_cases_find_no_ph_entities():
    engine = _analyzer()
    for text in MUST_NOT_REDACT:
        found = _ph_entity_types(engine, text)
        assert found == set(), f"{text!r}: expected no PH_* entities, found {found}"


def test_marker_span_excludes_the_marker_itself():
    engine = _analyzer()
    text = "Kausap ko si Maria kanina."
    results = [r for r in engine.analyze(text=text, language="en") if r.entity_type == "PH_PERSON"]
    assert len(results) == 1
    matched = text[results[0].start : results[0].end]
    assert matched == "Maria"
    assert "si" not in matched


def test_particle_name_is_one_span():
    engine = _analyzer()
    text = "Kausap ko si Juan dela Cruz kanina."
    results = [r for r in engine.analyze(text=text, language="en") if r.entity_type == "PH_PERSON"]
    assert len(results) == 1
    matched = text[results[0].start : results[0].end]
    assert matched == "Juan dela Cruz"


def test_nino_and_pena_are_detected():
    engine = _analyzer()
    assert _ph_entity_types(engine, "Kasama ko si Niño kahapon.") == {"PH_PERSON"}
    assert _ph_entity_types(engine, "Nakita ko si Peña sa palengke.") == {"PH_PERSON"}


# --- providers integration: registration + totality invariant (§4b, §4c) ---
# These call providers._presidio and providers.redact_pii against real Presidio —
# the spec sanctions real Presidio only in this file (AGENTS.md Testing bright line).

def test_presidio_registers_ph_recognizers():
    """providers._presidio() must register every PH_* entity type from ph_recognizers."""
    from providers import _presidio
    _presidio.cache_clear()
    analyzer, _ = _presidio()
    supported = {entity for r in analyzer.registry.recognizers for entity in r.supported_entities}
    assert {"PH_PERSON", "PH_MOBILE", "PH_ADDRESS", "PH_TIN", "PH_SSS", "PH_PHILHEALTH"} <= supported
    _presidio.cache_clear()


def test_redact_pii_never_leaks_the_original_value():
    """§2's totality invariant: end-to-end against real Presidio + real ph_recognizers."""
    from providers import _presidio, redact_pii
    _presidio.cache_clear()
    text = "Ako si Juan dela Cruz, taga Purok 3, Barangay San Isidro."
    result = redact_pii(text)
    assert "Juan" not in result
    assert "Cruz" not in result
    assert "Purok 3" not in result
    _presidio.cache_clear()


def test_redact_pii_leaves_narrative_entities_alone():
    """Regression, prod job e94cc400 (2026-08-11): spaCy tagged the story title "The Lost Little
    Star" as ORGANIZATION, the anonymizer's default operator hard-redacted it, and
    "<ORGANIZATION> upon a time" reached a book caption a child would read.

    §4c enumerates what hard-redacts — PH_TIN, PH_SSS, PH_PHILHEALTH, PH_MOBILE, PH_ADDRESS —
    and its stated rationale is that redaction output *is* the narrative. ORGANIZATION,
    LOCATION, DATE_TIME and NRP are spaCy's free-text NER guesses, not identifiers; on a
    children's story they are mostly false positives that destroy the prose.
    """
    from providers import _presidio, redact_pii
    _presidio.cache_clear()
    text = (
        "The Lost Little Star\n\nOnce upon a time, a little girl named Mia found a tiny "
        "glowing star in her backyard in Manila."
    )
    result = redact_pii(text)
    assert "<ORGANIZATION>" not in result
    assert "<LOCATION>" not in result
    assert "The Lost Little Star" in result
    assert "Manila" in result
    assert "Mia" not in result  # persons are still pseudonymized
    _presidio.cache_clear()


def test_redact_pii_still_hard_redacts_structured_identifiers():
    """The other half of §4c: identifiers must become obvious holes, never plausible fakes."""
    from providers import _presidio, redact_pii
    _presidio.cache_clear()
    result = redact_pii("Tawagan mo ako sa 0917 123 4567 o email sa mia@example.com.")
    assert "0917" not in result
    assert "mia@example.com" not in result
    assert "<PH_MOBILE>" in result
    assert "<EMAIL_ADDRESS>" in result
    _presidio.cache_clear()
