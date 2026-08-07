import re
import unicodedata


def normalize_nickname(raw: str) -> str:
    """Spec §5 — four-step pipeline. Raises ValueError at creation time; never at login."""
    # Step 1: NFKD + strip combining marks (Niño → Nino, José → Jose)
    nfkd = unicodedata.normalize("NFKD", raw)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Step 2: lowercase, trim outer whitespace, collapse whitespace runs to a single hyphen
    lowered = stripped.lower().strip()
    hyphened = re.sub(r"\s+", "-", lowered)
    # Step 3: collapse repeated hyphens, strip leading/trailing hyphens
    collapsed = re.sub(r"-{2,}", "-", hyphened).strip("-")
    # Step 4: reject if any character outside [a-z0-9-] survives, or length is out of range
    if not collapsed or re.search(r"[^a-z0-9-]", collapsed):
        raise ValueError(f"nickname {raw!r} cannot be normalized to a valid form")
    if len(collapsed) < 2:
        raise ValueError(f"nickname {raw!r} normalizes to under 2 characters")
    if len(collapsed) > 32:
        raise ValueError(f"nickname {raw!r} normalizes to over 32 characters")
    return collapsed
