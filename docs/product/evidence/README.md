# Measurement evidence for ADR-052 … ADR-055

The object-description and object-duplication ADRs are decided on measurement rather than
argument, and every one of them cites a path under a session scratch directory that does not
survive the session. This directory is that evidence, committed.

**ADR-053 and ADR-054 are Accepted and therefore frozen — their Evidence sections still name the
scratch paths and are not edited.** The crosswalk below is how those citations resolve.

## Crosswalk

| Cited as | Now at |
|---|---|
| `scratchpad/probe_out/runs/syn-901/` | `bundles/probe_out/` |
| `scratchpad/probe_out2/runs/syn-901/` | `bundles/probe_out2/` |
| `scratchpad/probe_out3/runs/syn-901/` | `bundles/probe_out3/` |
| `scratchpad/probe_out4/` | `bundles/probe_out4/` |
| `scratchpad/<name>.py` | `scripts/<name>.py` |
| `scratchpad/dupprobe/` (16 PNGs) | **not committed** — see below |
| `scratchpad/probe_out*/scene/`, `…/ref/` | **not committed** — see below |

## What is not here

The generated images. Each bundle's `memory.json` carries the prompts, the extracted axes, the
directions and the per-scene verdicts — everything the ADRs reason over — while the PNGs are only
the thing a human looked at. The page counts recorded in the ADRs (two fans on `s1`, three
distinct characters on `s4`) were read by eye and are not recoverable from these files. Re-running
a probe costs about USD 0.21 for seven images.

## Bundles

| Bundle | `code_commit` | Cost | What it shows |
|---|---|---|---|
| `probe_out` | pre-ADR-052 | — | the before-image: one object description, contradictory states |
| `probe_out2` | `8f9b79e` | USD 0.39, 13 images | ADR-052 landed; `s0` and `s1` still draw two fans |
| `probe_out3` | `11485e7` | USD 0.21, 7 images | ADR-053 landed; axes clean, no page asserts two states; `s1` and `s4` draw two fans and Lola renders as a second Tala |
| `probe_out4` | `2a87044` | USD 0.21, 7 images | ADR-054 landed; Lola distinct and no `null` in any prompt, but the directions are byte-identical to `probe_out3` and `s0` draws two fans from a single-actor direction |

## Scripts

Image arms — each holds the seed and varies only the prompt, which is what makes them evidence:

| Script | Arms | Result |
|---|---|---|
| `slot_experiment.py`, `arm_d.py` (+ `arm_d.json`) | ADR-053 A/B/C/D | arm D chosen |
| `strip_probe.py`, `strip_probe2.py` | clause-stripper over all 41 stored descriptions | — |
| `drop_rule.py` | drop rule over all 66 axis entries | — |
| `dup_probe.py` | control vs `Draw each object named above exactly once.` | 2 fans / 2 fans |
| `dup_probe2.py` | `This illustration contains exactly one bamboo fan.` | 2 fans / 2 fans |
| `dup_probe3.py` | `key_action` rewritten to name a holder, or to share | 1 fan / 1 fan |

Text arms — free, and the default under ADR-055 D3. Same inputs, `SEGMENTATION_PROMPT` the only
variable, counting multi-character directions that name the fan and resolve who holds it:

| Script | Arm | Resolved |
|---|---|---|
| `seg_ab.py` | no rule (control) | 5 / 24 |
| `seg_ab.py` | ADR-054 D1 as a standalone bullet | 9 / 31 |
| `seg_ab2.py`, `seg_ab3.py` | the same sentence inside the `key_action` definition | 14 / 29 |
| `seg_verify.py` | the above plus the ADR-055 D5 normalizer | 25 / 25 |

`probe_intake.json` is `syn-901`, the single story every measurement above runs on. It is a
reliable reproducer, not a sample: none of these rates estimates a corpus rate.

## Running them again

These are a record, not a suite. Each script hardcodes an absolute path to `backend/` and reads
its inputs from a bundle directory, so a re-run means fixing both paths first. The image arms
spend money. Nothing here is wired into CI, and it should not be.
