"""Serial retry of ERROR rows from roster_diagnostic.json, merged back into the report."""
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path.cwd()))  # run from `backend/`

sys.path.insert(0, str(pathlib.Path(__file__).parent))  # noqa: E402
from roster_diagnostic import CORPUS, REPORT, probe  # noqa: E402

rows = {r["story_id"]: r for r in json.loads(REPORT.read_text(encoding="utf-8"))}
records = {r["story_id"]: r for r in json.loads(CORPUS.read_text(encoding="utf-8"))}

for story_id in [k for k, v in rows.items() if v["status"] == "ERROR"]:
    for attempt in range(3):
        row = probe(records[story_id])
        if row["status"] != "ERROR":
            break
        time.sleep(5)
    rows[story_id] = row
    print(row["status"], story_id, row.get("declared"), "->", row.get("extracted", row.get("error")))

REPORT.write_text(json.dumps(list(rows.values()), indent=2), encoding="utf-8")
from collections import Counter  # noqa: E402
print(Counter(r["status"] for r in rows.values()))
