"""Can the extraction model write a clean permanent description when the schema
gives narrative its own slot?  Three arms, same model, same call path, temp 0."""
import json, re, sys
from pydantic import BaseModel
from providers import structured_text
from pipeline.analyze import (
    EXTRACTION_PROMPT, ExtractedCharacter, StoryAnalysis, ExtractedObject, ExtractedLocation,
)
from contracts.story_memory import TimelineEvent

OLD = ("Locations and objects: whatever the story mentions. Describe each location by what is "
       "permanently there")
assert OLD in EXTRACTION_PROMPT
_head, _tail = EXTRACTION_PROMPT.split("Locations and objects:", 1)
_tail = _tail.split("\n\nTimeline:", 1)[1]
def prompt_with(para: str) -> str:
    return _head + para + "\n\nTimeline:" + _tail

CONTROL_PARA = EXTRACTION_PROMPT.split("Locations and objects:", 1)[1].split("\n\nTimeline:", 1)[0]
CONTROL_PARA = "Locations and objects:" + CONTROL_PARA


# ---- arm B: one prose slot for appearance, one for everything else ----
class SplitObject(BaseModel):
    name: str
    appearance: str
    use_and_history: str | None = None
    owner_name: str | None = None

class SplitLocation(BaseModel):
    name: str
    appearance: str
    what_happens_there: str | None = None

class SplitAnalysis(BaseModel):
    characters: list[ExtractedCharacter]
    locations: list[SplitLocation]
    objects: list[SplitObject]
    timeline: list[TimelineEvent]

SPLIT_PARA = """Locations and objects: whatever the story mentions.
Every location and object has TWO separate fields, and each fact belongs in exactly one of them.
appearance: only what a person would see if they walked in and looked at it, with the story
stopped and nobody present. Permanent physical facts only. Never its use, never who owns it,
never what happens to it, never any change it undergoes during the story.
what_happens_there / use_and_history: everything else the story says about it — what it is for,
who uses it, what is done to it, how it changes. Put the change here, in full, never in appearance.
Copy every stated permanent physical fact into appearance without alteration, and fill missing
detail once with plain, child-safe features that make it visually recognizable.
Set owner_name to the character's name if owned by a character, or null if unowned."""


# ---- arm C: axes, no prose slot at all (how characters are already handled) ----
class AxisObject(BaseModel):
    name: str
    materials: list[str]
    colours: list[str]
    form_features: list[str]
    owner_name: str | None = None

class AxisLocation(BaseModel):
    name: str
    permanent_features: list[str]

class AxisAnalysis(BaseModel):
    characters: list[ExtractedCharacter]
    locations: list[AxisLocation]
    objects: list[AxisObject]
    timeline: list[TimelineEvent]

AXIS_PARA = """Locations and objects: whatever the story mentions.
Describe each object with short drawable noun phrases on three axes: materials (what it is made
of), colours, and form_features (shape, size, parts, markings). Describe each location with
permanent_features: short drawable noun phrases for what is permanently there.
Every entry must be a thing a person could see with the story stopped and nobody present. Never
write a use, an owner, an event, or a change: "used to flatten the tail", "eaten by the sheep",
"later painted" are all forbidden. Copy stated permanent physical facts without alteration and
fill missing detail once with plain, child-safe, drawable features.
Set owner_name to the character's name if owned by a character, or null if unowned."""


NARRATIVE = re.compile(
    r"\b(used|use|uses|where|when|eaten|eat|caused|damag|built|made by|mentioned|found|hid|"
    r"later|after|before|during|because|belong|painted|carried|poured|kept|stored|sits|"
    r"happens|story|decorate|straighten|flatten)\w*\b", re.I)

def flag(s: str) -> str:
    hits = sorted(set(m.group(0).lower() for m in NARRATIVE.finditer(s)))
    return ("NARRATIVE:" + ",".join(hits)) if hits else "clean"

stories = {}
for r in json.load(open("finetune/corpus_synthetic.json", encoding="utf-8")):
    if r["story_id"] in ("syn-001", "syn-002"):
        stories[r["story_id"]] = r["text"]
stories["syn-901"] = json.load(open(
    "C:/Users/Asus/AppData/Local/Temp/claude/C--Users-Asus-Desktop-story-buddy/"
    "c8166e32-e669-4f7c-9349-b1b839e6968f/scratchpad/probe_intake.json", encoding="utf-8"))[0]["text"]

ARMS = [("A control", CONTROL_PARA, StoryAnalysis),
        ("B split  ", SPLIT_PARA,   SplitAnalysis),
        ("C axes   ", AXIS_PARA,    AxisAnalysis)]

score = {}
for sid, text in stories.items():
    for label, para, schema in ARMS:
        try:
            out = structured_text(prompt_with(para), schema).model_validate(
                structured_text(prompt_with(para).format(text=text), schema).model_dump()
            ) if False else structured_text(prompt_with(para).format(text=text), schema)
        except Exception as exc:
            print(f"{sid} {label}  CALL FAILED: {type(exc).__name__}: {str(exc)[:200]}")
            continue
        print(f"\n===== {sid}  arm {label} =====")
        for o in out.objects:
            if hasattr(o, "description"):
                fields = {"description": o.description}
            elif hasattr(o, "appearance"):
                fields = {"appearance": o.appearance, "use_and_history": o.use_and_history}
            else:
                fields = {"materials": o.materials, "colours": o.colours, "form_features": o.form_features}
            key = "description" if "description" in fields else ("appearance" if "appearance" in fields else None)
            visual = fields[key] if key else " | ".join(fields["materials"] + fields["colours"] + fields["form_features"])
            v = flag(visual)
            score.setdefault(label, [0, 0])
            score[label][1] += 1
            if v == "clean": score[label][0] += 1
            print(f"  obj {o.name!r:26s} [{v}]")
            for k, val in fields.items():
                print(f"        {k}: {val!r}")
        for loc in out.locations:
            if hasattr(loc, "description"): visual, extra = loc.description, None
            elif hasattr(loc, "appearance"): visual, extra = loc.appearance, loc.what_happens_there
            else: visual, extra = " | ".join(loc.permanent_features), None
            v = flag(visual)
            score.setdefault(label, [0, 0]); score[label][1] += 1
            if v == "clean": score[label][0] += 1
            print(f"  loc {loc.name!r:26s} [{v}]")
            print(f"        visual: {visual!r}")
            if extra is not None: print(f"        other : {extra!r}")

print("\n===== clean visual fields per arm =====")
for label, (ok, n) in score.items():
    print(f"  arm {label}: {ok}/{n} clean")
