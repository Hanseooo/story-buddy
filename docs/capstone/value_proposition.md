# StoryBuddy — Value Proposition

> **This document is derived, not authoritative.** It sharpens, in one place, the community/real-world
> value argument for the manuscript's Introduction and Discussion. Sources of truth:
> `docs/product/RESEARCH_PROTOCOL.md` §1, §3 and `docs/capstone/research_direction_and_goals.md` §5.
> Where this and those disagree, they win.

The single hardest question a capstone panel asks is *"so what — why does this matter outside the code?"*
The wrong answers are seductive because they sound impressive and are impossible to defend. This document
fixes the **defensible** answer and names the two traps to never fall into.

---

## 1. The claim, in one sentence

> **A child's story can be published as an illustrated book that other people actually read *as the child's
> story* — on an open-weight stack a public school can afford to run, with no per-seat licensing cost and no
> vendor lock-in.**

Every load-bearing word in that sentence is defended by a *different* kind of evidence. That separation is
the whole point: a panel can attack each layer, and each has its own answer.

> **Precise cost claim — do not overstate it.** The defensible cost property is *no per-seat licensing and no
> vendor lock-in*, because the stack is open-weight and self-hostable (ADR-015). It is **not** "runs on the
> school's own hardware at zero cost" — that is on-device deployment (ADR-015 Reading 3), which is **Future
> Work**: the heavy models (image ~20B, text ~32B, judge ~27B) need a 24 GB+ GPU no ordinary school PC has.
> v1 runs on low-cost *hosted inference of open weights* (~cents per book of compute; see
> `hardware_and_hosting.md`). "Affordable and un-lockable" is defensible; "free on hardware they already own"
> is not. Hold the first line, refuse the second.

---

## 2. The three layers, and how each is defended

| Layer | The claim | How it is defended | Evidence type |
|---|---|---|---|
| **Warrant** (why it matters) | An *authentic audience* and *actual publication* are among the strongest levers on children's writing engagement. | **Cited prior literature — not our finding.** We inherit it; we do not test it. | External, established |
| **Design property** (who it reaches) | Open-weight, self-hostable, **zero per-seat vendor cost** → a provincial public school can run what only a well-funded private school could otherwise afford. SDG-4 (Quality Education). | **True by construction.** It is a property of the architecture (open-weight mandate, ADR-015), provable without any study. | Architectural |
| **Measured finding** (what we prove) | A reader who never saw the text recovers the child's characters and events *from the finished book alone* — the book **is** the child's story, not the model's. | **RQ5, our study's outcome of record.** Blind, between-reader, scored against text-only plot-point annotations. | Empirical (this study) |

The chain reads top to bottom: *prior work says an authentic audience matters → publishing 40 illustrated
books was effectively infinite-cost → we collapse that cost → **but only if the book faithfully transmits the
child's story**, else you have published the model, not the child → RQ5 measures exactly that fidelity.*

**The technical problem and the community value are the same claim from opposite ends.** That is what makes
this research rather than integration.

---

## 3. Two traps — do not fall into either

### Trap A — "StoryBuddy improves children's creativity / writing ability"
Unmeasurable at N ≈ 8–15 with no control, no pre/post, no longitudinal window. Overclaiming here is the
single most likely way the defense goes badly. Creativity is a **motivation** (a warrant from prior work),
never a finding of this study. Already refused in `research_direction_and_goals.md` §5 — keep refusing it.

### Trap B — "Illustrated stories are easier to understand / attract more readers than plain text"
Tempting, and **worse than it looks**, for two independent reasons:

1. **We did not design to measure it.** RQ5 compares an *illustrated* book (pipeline-ON) against another
   *illustrated* book (pipeline-OFF). There is **no text-only control arm anywhere in the study.** To claim
   "pictures beat text," you would need a third condition — raw text, no illustration — that does not exist,
   and adding it is expensive and off-mission.
2. **It is already established, so it would be a warrant, not a finding.** "Pictures aid comprehension" is
   dual-coding / multimedia-learning theory — decades old. Swapping the creativity warrant for the
   picture-superiority warrant changes nothing: it is *still* not our contribution.

**The correct reframing of the "readership" instinct** is Layer 3 above: not *"pictures beat text,"* but
*"the generated book faithfully re-tells what the child wrote, and the consistency machinery (ON vs OFF) is
what buys that fidelity."* That is a finding you own. Hold this line if a panelist says *"aren't pictures
obviously easier to read?"* — RQ5 is about **transmission fidelity of the child's story**, not picture-vs-text.

---

## 4. What we still refuse to claim

See the table in `research_direction_and_goals.md` §5 (learning gains · privacy preservation · watermark
provenance · that the fine-tuned judge will ship). This document does not restate it; it only adds Trap B to
the list of refusals.

---

## 5. Where this lands in the manuscript

- **Introduction** — open with the child and the folder (Layer 1 warrant), land on identity drift (the gap).
- **Discussion** — Layers 2 and 3: the equity property, then what RQ5 actually demonstrated about fidelity.
- **Limitations** — restate Traps A and B explicitly as claims deliberately *not* made.
