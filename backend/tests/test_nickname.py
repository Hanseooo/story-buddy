import pytest
from app.nickname import normalize_nickname

# Spec §5.1 — transcribed verbatim. Do not edit without updating the TypeScript suite too.
PASS_VECTORS = [
    ("Juan", "juan"),
    ("MARIA", "maria"),
    ("Ana Mae", "ana-mae"),
    ("  Juan  Dela   Cruz ", "juan-dela-cruz"),
    ("Niño", "nino"),
    ("José-María", "jose-maria"),
    ("Kim  -  Lee", "kim-lee"),
    ("--Jun--", "jun"),
    ("R2D2", "r2d2"),
]

REJECT_VECTORS = [
    "Juan!",    # illegal character survives step 4
    "J",        # under 2 characters after normalization
    "a" * 33,   # over 32 characters after normalization
    "😀",       # non-[a-z0-9-] survives
    "ᜃᜌ",     # Baybayin — non-[a-z0-9-] survives
]


@pytest.mark.parametrize("raw,expected", PASS_VECTORS)
def test_normalize_nickname_pass(raw, expected):
    assert normalize_nickname(raw) == expected


@pytest.mark.parametrize("raw", REJECT_VECTORS)
def test_normalize_nickname_rejects(raw):
    with pytest.raises(ValueError):
        normalize_nickname(raw)
