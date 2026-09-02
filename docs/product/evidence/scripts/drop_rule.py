import json, re
SCRATCH = ("C:/Users/Asus/AppData/Local/Temp/claude/C--Users-Asus-Desktop-story-buddy/"
           "c8166e32-e669-4f7c-9349-b1b839e6968f/scratchpad")
d = json.load(open(f"{SCRATCH}/arm_d.json", encoding="utf-8"))

STOP = {"a","an","the","and","or","with","of","in","on","it","is","was","to","by","its",
        "then","that","this","for","from","into","at","as","be","been","are","were"}
def content(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2}
def stems(ws):                      # crude, deliberate: -ed/-ing/-s/-y off the end
    out = set()
    for w in ws:
        for suf in ("ing", "ed", "es", "s", "y"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                out.add(w[: -len(suf)]); break
        else:
            out.add(w)
    return out

def atoms(entries):                 # entries arrive comma-joined; split them
    out = []
    for e in entries:
        out += [p.strip() for p in e.split(",") if p.strip()]
    return out

THRESHOLD = 2
kept_n = dropped_n = 0
for sid, blob in d.items():
    print(f"\n===== {sid} =====")
    for o in blob["objects"]:
        chg = o.get("changes_during_story")
        cs = stems(content(chg)) if chg else set()
        print(f"  obj {o['name']!r}   change={chg!r}")
        for axis in ("materials", "colours", "form_features"):
            for e in atoms(o[axis]):
                shared = stems(content(e)) & cs
                drop = len(shared) >= THRESHOLD
                kept_n += not drop; dropped_n += drop
                mark = "DROP" if drop else "keep"
                extra = f"  <- shares {sorted(shared)}" if shared else ""
                print(f"      {mark} {axis:13s} {e!r}{extra}")
    for loc in blob["locations"]:
        chg = loc.get("changes_during_story")
        cs = stems(content(chg)) if chg else set()
        for e in atoms(loc["permanent_features"]):
            shared = stems(content(e)) & cs
            drop = len(shared) >= THRESHOLD
            kept_n += not drop; dropped_n += drop
            print(f"      {'DROP' if drop else 'keep'} loc/{loc['name']:16s} {e!r}")
print(f"\nthreshold={THRESHOLD}: {dropped_n} dropped, {kept_n} kept")
