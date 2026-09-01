"""Text-only roster diagnostic: does each synthetic record's declared roster reconcile
with what `analyze` actually extracts? No Fal, no images, no database, no writes to
`data/judge/corpus`. Run from `backend/`:

    uv run python ../.scratch/obj4-dataset-generation-readiness/roster_diagnostic.py

Mirrors `analyze()`'s 3-character cap and `reconcile_declared_roster`'s casefolded
counting so a MISMATCH here is the same failure `build_corpus` would raise at packaging.
"""
import json
import pathlib
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path.cwd()))  # run from `backend/`

from pipeline.analyze import extract_entities  # noqa: E402

CORPUS = pathlib.Path("finetune/corpus_synthetic.json")
REPORT = pathlib.Path(__file__).with_name("roster_diagnostic.json")


def probe(record: dict) -> dict:
    story_id = record["story_id"]
    try:
        analysis = extract_entities(record["text"])
    except Exception as error:  # a provider/validation failure is itself a finding
        return {"story_id": story_id, "status": "ERROR", "error": f"{type(error).__name__}: {error}"}
    # analyze() caps at 3 before anything is persisted or drawn.
    capped = analysis.characters[:3]
    extracted = [c.name for c in capped]
    extracted_non_human = [c.name for c in capped if not c.description.is_humanoid]
    reconciles = Counter(n.casefold() for n in record["declared_characters"]) == Counter(
        n.casefold() for n in extracted
    ) and Counter(n.casefold() for n in record["declared_non_human"]) == Counter(
        n.casefold() for n in extracted_non_human
    )
    return {
        "story_id": story_id,
        "status": "OK" if reconciles else "MISMATCH",
        "declared": record["declared_characters"],
        "extracted": extracted,
        "declared_non_human": record["declared_non_human"],
        "extracted_non_human": extracted_non_human,
        "over_extracted": len(analysis.characters) > 3,
    }


def main() -> int:
    records = json.loads(CORPUS.read_text(encoding="utf-8"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows = sorted(pool.map(probe, records), key=lambda row: row["story_id"])
    REPORT.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    counts = Counter(row["status"] for row in rows)
    for row in rows:
        if row["status"] == "OK":
            print(f"OK       {row['story_id']}  {row['extracted']}")
        elif row["status"] == "ERROR":
            print(f"ERROR    {row['story_id']}  {row['error']}")
        else:
            print(f"MISMATCH {row['story_id']}  declared={row['declared']} extracted={row['extracted']}")
            if Counter(n.casefold() for n in row["declared"]) == Counter(
                n.casefold() for n in row["extracted"]
            ):
                print(f"         non-human only: declared={row['declared_non_human']} extracted={row['extracted_non_human']}")
    print(f"\n{len(rows)} records: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"report: {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
