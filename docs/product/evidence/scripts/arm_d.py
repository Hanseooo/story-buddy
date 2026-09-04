"""Arm D: axes + an explicit slot for the change. Saves raw output so the drop
rule can be tuned offline without further spend."""
import json
from pydantic import BaseModel
from providers import structured_text
from pipeline.analyze import EXTRACTION_PROMPT, ExtractedCharacter
from contracts.story_memory import TimelineEvent

SCRATCH = ("C:/Users/Asus/AppData/Local/Temp/claude/C--Users-Asus-Desktop-story-buddy/"
           "c8166e32-e669-4f7c-9349-b1b839e6968f/scratchpad")
_head, _tail = EXTRACTION_PROMPT.split("Locations and objects:", 1)
_tail = _tail.split("\n\nTimeline:", 1)[1]

class AxisObject(BaseModel):
    name: str
    materials: list[str]
    colours: list[str]
    form_features: list[str]
    changes_during_story: str | None = None
    owner_name: str | None = None

class AxisLocation(BaseModel):
    name: str
    permanent_features: list[str]
    changes_during_story: str | None = None

class AxisAnalysis(BaseModel):
    characters: list[ExtractedCharacter]
    locations: list[AxisLocation]
    objects: list[AxisObject]
    timeline: list[TimelineEvent]

PARA = """Locations and objects: whatever the story mentions.
Describe each object on three axes — materials (what it is made of), colours, and form_features
(shape, size, parts, markings). Describe each location with permanent_features. Every entry is a
short drawable noun phrase, one line, under 120 characters.
An entry on those axes must be true of the object in EVERY picture of the story, from the first
page to the last. If the story changes how the thing looks — it is painted, broken, eaten, opened,
cleaned, torn — that change is NOT an axis entry. Put it in changes_during_story instead, in full,
and leave the axes describing the thing as it was before the change. Set changes_during_story to
null when the thing looks the same throughout.
Copy stated permanent physical facts without alteration; fill missing detail once with plain,
child-safe, drawable features. Set owner_name to the character's name if owned, or null."""

stories = {r["story_id"]: r["text"] for r in
           json.load(open("finetune/corpus_synthetic.json", encoding="utf-8"))
           if r["story_id"] in ("syn-001", "syn-002")}
stories["syn-901"] = json.load(open(f"{SCRATCH}/probe_intake.json", encoding="utf-8"))[0]["text"]

out = {}
for sid, text in stories.items():
    r = structured_text((_head + PARA + "\n\nTimeline:" + _tail).format(text=text), AxisAnalysis)
    out[sid] = {"objects": [o.model_dump() for o in r.objects],
                "locations": [loc.model_dump() for loc in r.locations]}
    print(f"\n===== {sid} =====")
    for o in r.objects:
        print(f"  obj {o.name!r}")
        print(f"      materials={o.materials} colours={o.colours} form={o.form_features}")
        print(f"      changes_during_story={o.changes_during_story!r}")
    for loc in r.locations:
        print(f"  loc {loc.name!r}  features={loc.permanent_features}")
        print(f"      changes_during_story={loc.changes_during_story!r}")

json.dump(out, open(f"{SCRATCH}/arm_d.json", "w", encoding="utf-8"), indent=1)
print(f"\nsaved -> {SCRATCH}/arm_d.json")
