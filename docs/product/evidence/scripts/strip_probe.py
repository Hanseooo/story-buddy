import json, glob, re, pathlib

SCRATCH = "C:/Users/Asus/AppData/Local/Temp/claude/C--Users-Asus-Desktop-story-buddy/c8166e32-e669-4f7c-9349-b1b839e6968f/scratchpad"

def load():
    rows = []
    paths = sorted(glob.glob("data/judge/**/runs/*/memory.json", recursive=True))
    paths += [f"{SCRATCH}/probe_out2/runs/syn-901/memory.json",
              f"{SCRATCH}/probe_out/runs/syn-901/memory.json"]
    for p in paths:
        m = json.load(open(p, encoding="utf-8"))
        tag = pathlib.Path(p).parts[-4].replace("corpus-", "") + "/" + m.get("story_id", "?")
        for kind in ("objects", "locations"):
            for o in m.get(kind, []):
                rows.append((kind[:3], tag, o.get("name"), o.get("description") or ""))
    return rows

# candidate: drop any clause headed by a narrative/use marker
MARKERS = r"(?:used|where|when|eaten|caused|damaged|built|made|mentioned|found|placed|hidden|later|which is later|that is later|after|before|during|because)"
CLAUSE = re.compile(
    rf"(?:,|;|\s+)(?:\b(?:and\s+)?(?:it\s+is\s+|it\s+was\s+|is\s+|was\s+|partially\s+|briefly\s+)?){MARKERS}\b.*?(?=[.;]|$)",
    re.IGNORECASE,
)
SENTENCE_MARKER = re.compile(rf"^\s*(?:it|the\s+\w+|this)\s+(?:is|was|has been)\s+(?:\w+\s+)?{MARKERS}\b", re.IGNORECASE)

def strip(desc: str) -> str:
    sentences = re.split(r"(?<=[.])\s+", desc.strip())
    kept = []
    for s in sentences:
        if SENTENCE_MARKER.search(s):
            continue
        s2 = CLAUSE.sub("", s)
        s2 = re.sub(r"\s*,\s*(?=[.]|$)", "", s2).strip().strip(",")
        if s2 and s2 not in {".", ""}:
            kept.append(s2 if s2.endswith(".") else s2)
    out = " ".join(kept).strip()
    out = re.sub(r"\s{2,}", " ", out)
    return out

rows = load()
changed = same = emptied = 0
for kind, tag, name, d in rows:
    s = strip(d)
    flag = "SAME " if s == d else ("EMPTY" if not s else "STRIP")
    if s == d: same += 1
    elif not s: emptied += 1
    else: changed += 1
    print(f"[{kind}] {flag} {tag:26s} {name!r:24s}")
    print(f"        in : {d}")
    if s != d:
        print(f"        out: {s}")
print(f"\n{len(rows)} descriptions: {changed} stripped, {same} untouched, {emptied} emptied")
