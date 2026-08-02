"""Filipino PII recognizers (spec docs/specs/input-gate-hardening.md §4b).

Marker patterns are the point of this module: Tagalog marks personal names grammatically —
si / ni / kay / sina / nina / kina — a signal English NER structurally cannot see. The PSA
surname deny-list is deferred (§8, decided 2026-08-02): provenance and licensing are unresolved
for a capstone data artifact, and the marker patterns alone are shippable per the spec's own
escape hatch. No deny-list means PH_PERSON only fires when a marker is present.
"""
import re

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer

# Case-sensitivity is load-bearing: [A-ZÑ] must distinguish proper names from common words.
# Presidio defaults to IGNORECASE; we strip it for every PH_* recognizer.
_FLAGS = re.DOTALL | re.MULTILINE

_MARKERS = ("si", "ni", "kay", "sina", "nina", "kina")
# Each lookbehind is fixed-width (required by Python re); both lower and title-case because
# the IGNORECASE flag is stripped (case-sensitivity guards the [A-ZÑ] name character class).
_MARKER_LOOKBEHIND = "|".join(
    lb
    for m in _MARKERS
    for lb in (rf"(?<=\b{m} )", rf"(?<=\b{m.capitalize()} )")
)

# Longest-first so "delos"/"delas" aren't partially matched by "de"/"del".
_PARTICLE = r"(?:delos|delas|dela|del|de|Santa|San)"
_NAME_WORD = r"[A-ZÑ][\w'-]*"
_EXTRA_TOKEN = rf"(?:{_PARTICLE}|{_NAME_WORD})"

# Alternation of *individually* fixed-width lookbehinds — Python's re permits this, but not
# one variable-width lookbehind. A naive r"\b(?:si|ni)\s+([A-Z]\w+)" would span the marker
# too, corrupting the sentence when the span is later replaced.
PERSON_MARKER_REGEX = rf"(?:{_MARKER_LOOKBEHIND}){_NAME_WORD}(?: {_EXTRA_TOKEN}){{0,2}}"

# Kinship terms are routinely capitalized in Filipino writing; "si Lolo" is "grandpa", not a
# name. "kay" as an intensifier ("kay ganda ng araw") is already blocked by the capitalization
# requirement in _NAME_WORD — the lowercase word after "kay" never matches.
MARKER_EXCEPTIONS = {"lolo", "lola", "nanay", "tatay", "ate", "kuya", "ninong", "ninang"}


class PersonMarkerRecognizer(PatternRecognizer):
    def __init__(self) -> None:
        pattern = Pattern(name="ph_person_marker", regex=PERSON_MARKER_REGEX, score=0.85)
        super().__init__(
            supported_entity="PH_PERSON",
            patterns=[pattern],
            supported_language="en",
            global_regex_flags=_FLAGS,
        )

    def validate_result(self, pattern_text: str) -> bool | None:
        first_token = pattern_text.split()[0]
        if first_token.casefold() in MARKER_EXCEPTIONS:
            return False
        return None


_ADDR_KEYWORD = r"(?:Barangay|Brgy\.?|Purok|Sitio)"
_ADDR_TOKEN = r"(?:[A-ZÑ][\w'-]*|\d+)"
PH_ADDRESS_REGEX = rf"\b{_ADDR_KEYWORD}\s+{_ADDR_TOKEN}(?:\s+{_ADDR_TOKEN}){{0,2}}"

# +63 9xx / 09xx, spaced, dashed, or bare.
PH_MOBILE_REGEX = r"(?<!\d)(?:\+63[\s-]?9\d{2}|09\d{2})[\s-]?\d{3}[\s-]?\d{4}(?!\d)"

# Fixed government ID formats — public numbering formats, not a curated data list.
PH_TIN_REGEX = r"\b\d{3}-\d{3}-\d{3}(?:-\d{3,4})?\b"
PH_SSS_REGEX = r"\b\d{2}-\d{7}-\d\b"
PH_PHILHEALTH_REGEX = r"\b\d{2}-\d{9}-\d\b"


def _pattern_recognizer(entity: str, regex: str, score: float) -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity=entity,
        patterns=[Pattern(name=entity.lower(), regex=regex, score=score)],
        supported_language="en",
        global_regex_flags=_FLAGS,
    )


def ph_recognizers() -> list[EntityRecognizer]:
    return [
        PersonMarkerRecognizer(),
        _pattern_recognizer("PH_MOBILE", PH_MOBILE_REGEX, 0.9),
        _pattern_recognizer("PH_ADDRESS", PH_ADDRESS_REGEX, 0.85),
        _pattern_recognizer("PH_TIN", PH_TIN_REGEX, 0.6),
        _pattern_recognizer("PH_SSS", PH_SSS_REGEX, 0.6),
        _pattern_recognizer("PH_PHILHEALTH", PH_PHILHEALTH_REGEX, 0.6),
    ]
