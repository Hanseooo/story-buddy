"""Fixtures for tests/test_ph_recognizers.py (spec docs/specs/input-gate-hardening.md §6).

Deny-list is deferred (§8, decided 2026-08-02) — every MUST_REDACT person case here is
marker-triggered (si/ni/kay/sina/nina/kina), not gazetteer-triggered.
"""

# (text, expected_entity_types) — analyze() must find at least one PH_* entity of each
# type listed. Built-in PERSON/PHONE_NUMBER may also fire; not asserted either way.
MUST_REDACT = [
    ("Ako si Juan dela Cruz, taga Purok 3, Barangay San Isidro.",
     {"PH_PERSON", "PH_ADDRESS"}),
    ("Si Maria ay pumunta sa palengke.", {"PH_PERSON"}),
    ("Tinawag ni Pedro ang kaibigan niya.", {"PH_PERSON"}),
    ("Kausap ko kay Ana kanina.", {"PH_PERSON"}),
    ("Sina Juan at Maria ay magkaibigan.", {"PH_PERSON"}),
    ("Nina Pedro at Ana ang bahay na iyon.", {"PH_PERSON"}),
    ("Kina Juan ipinadala ang liham.", {"PH_PERSON"}),
    ("Kasama ko si Niño kahapon.", {"PH_PERSON"}),
    ("Nakita ko si Peña sa palengke.", {"PH_PERSON"}),
    ("Kausap ko si Juan dela Cruz kanina.", {"PH_PERSON"}),
    ("Ang numero niya ay 0917-123-4567.", {"PH_MOBILE"}),
    ("Tawagan mo ako sa +63 917 123 4567.", {"PH_MOBILE"}),
    ("Ang cellphone niya ay 09171234567.", {"PH_MOBILE"}),
    ("Taga Sitio Malinis siya.", {"PH_ADDRESS"}),
    ("Nakatira sila sa Brgy. Malaya.", {"PH_ADDRESS"}),
    ("Ang TIN ko ay 123-456-789.", {"PH_TIN"}),
    ("SSS number ko: 34-1234567-8.", {"PH_SSS"}),
    ("PhilHealth ko ay 12-345678901-2.", {"PH_PHILHEALTH"}),
]

# Plain strings — analyze() must find zero PH_* entities (built-in recognizers are ignored;
# this fixture set is about our false-positive control, not spaCy's).
MUST_NOT_REDACT = [
    "si Lolo ay masaya",
    "si Lola ay maganda",
    "kay ganda ng araw",
    "ang cruz sa simbahan",
    "Kumusta ka na?",
    "Masaya ang bata sa parke.",
    "si Nanay ay nagluluto",
    "si Kuya ay naglalaro",
]
