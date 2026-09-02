import re, sys
sys.path.insert(0, "C:/Users/Asus/AppData/Local/Temp/claude/C--Users-Asus-Desktop-story-buddy/c8166e32-e669-4f7c-9349-b1b839e6968f/scratchpad")
from strip_probe import load, strip

STOP = re.compile(r"^(a|an|the|small|part of)$", re.I)
def informative(name, stripped):
    words = [w for w in re.findall(r"[a-z']+", stripped.lower()) if not STOP.match(w)]
    namew = set(re.findall(r"[a-z']+", name.lower()))
    extra = [w for w in words if w not in namew]
    return extra

rows = load()
none_left, some_left = [], []
for kind, tag, name, d in rows:
    s = strip(d)
    extra = informative(name, s)
    (none_left if not extra else some_left).append((kind, tag, name, d, s, extra))

print(f"AFTER STRIPPING NARRATIVE — {len(none_left)}/{len(rows)} add NOTHING beyond the object's own name:\n")
for kind, tag, name, d, s, _ in none_left:
    print(f"  [{kind}] {tag:26s} {name!r:26s} {d!r}  ->  {s!r}")
print(f"\n{len(some_left)}/{len(rows)} keep real appearance detail:\n")
for kind, tag, name, d, s, extra in some_left:
    print(f"  [{kind}] {tag:26s} {name!r:26s} -> {s!r}   (adds: {' '.join(extra)})")
