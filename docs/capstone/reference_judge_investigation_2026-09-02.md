# Reference-judge investigation — 2026-09-02

Measured findings from the ADR-050 smoke re-run and the probes that followed. The probe
scripts were throwaway and are not kept; every number below is reproducible from the
procedure described in each section.

**Bottom line:** the reference gate does not work, and the cause is not routing, not the
prompt, not the schema, and not ADR-050's retry. No off-the-shelf open-weight VLM tested
reliably grounds a stated attribute against the image. This is the case ADR-018 already
anticipated; until that fine-tune exists, `ref_verdict` cannot be trusted in either
direction.

---

## 1. The paid smoke re-run (`data/judge/corpus-smoke-c`)

Single-story paid run per `research_runbook.md`:
`--corpus finetune/corpus_synthetic.json --out ../data/judge/corpus-smoke-c --limit 1
--max-usd 1.00 --price-per-megapixel 0.03 --price-basis "<fal urls, verified 2026-09-01>"`

- Cost **USD 0.66** (`usd_high`), 22 images, exit 0, no halt, no quarantine.
- `code_commit 8112cee` — ADR-045 was committed first so this line is truthful.
- **Scenes passing: 2 of 7** (s0, s1), up from 0 of 7 in `corpus-smoke-b`.
- 19 attempts; `wrong_body_feature` 14, `different_face` 14.
- **11 structured contradictions**, 10 naming Bok-Bok (was ~89 free-text in smoke-b).
- `text_free` False on 16 of 19 — unchanged false-positive pattern, and again never the
  sole gate: both passing attempts had `text_free: True`.
- **`unchecked_references: 2`** — ADR-050's counter fired on its first real run and made
  the dropped gate readable from the record instead of by opening PNGs.

**Not a like-for-like comparison with smoke-b.** ADR-049, ADR-050 and ADR-045 all landed
between the runs, and extraction is nondeterministic: Bok-Bok's spec came back this time
*without* "no face" and "standing on one leg". The impossible constraint was simply not
asked for. Do not attribute 0 to 2 to any single change.

## 2. ADR-050's retry did not help, and its premise was wrong

ADR-050 argued the judge stall was transient ("the identical timeout cleared on one
unchanged retry"). One clean retry was not a rate. In smoke-c the judge hit the full
120s bound on both attempts and both references still shipped unchecked.

One thing did work: Bok-Bok took **two draws**, which only happens when draw 1 returned a
*failing* verdict. The gate rejected a reference for the first time on record, then lost
the judge on the redraw.

## 3. What the stall actually is: OpenRouter routing

`providers.VISION_PROVIDERS` pins `mistral-small` only. `google/gemma-3-27b-it` has **no
pin**, so every judge call is routed freely. Four backends serve it:

| backend | reference-judge call |
|---|---|
| **DeepInfra** | **5 of 5 timeouts** at the bound — dead for this model |
| Parasail | answers in 6-10s; **1 of 4 stalls** |
| Nebius | answers in 2-6s, never stalls |
| Novita | 404 — cannot serve `require_parameters` (strict schema) |

Unpinned calls failed **5 of 5**. OpenRouter evidently prefers DeepInfra, which is first
in the endpoint list. This fully explains the timeouts — and explains why 19 scene-judge
calls succeeded in the same run: repeated draws from a pool, not a property of references.

**Falsified along the way** (each tested directly, all negative): payload size (a call with
*two* images succeeded while a smaller one-image call timed out); vision vs text (a call
with **no image** also hit the full bound); the `RefVerdict` schema; the reference prompt;
and determinism (byte-identical calls gave opposite outcomes).

## 4. Pinning a provider does NOT fix the gate

Ground truth was read off `ref-c1-1.png` by hand, not from any model. Bok-Bok's spec
demands *metal beak and comb*. The image shows a grey rust-patched metal body and metal
tail, but a **bright yellow beak** and a **red comb and wattles**. At minimum two plain
contradictions.

Two-sided test — the real spec (must find at least 1) and a description hand-written to
match the image (must find 0), three reps each:

| provider | vs real spec (expect >=1) | vs matched description (expect 0) |
|---|---|---|
| Parasail | 2, 3, timeout | **3**, 0, 0 |
| Nebius | **0, 0, 0** | **3, 3, 2** |

**Nebius is anti-correlated with the truth** — clean when it should flag, flagging when it
is clean. Pinning it would have been the worst available outcome: the gate would run, pass
everything, and write `unchecked_references: 0`. A visibly broken gate would have become an
invisibly broken one.

Across every run of the probe, **neither provider ever named the yellow beak or the red
comb**. They returned quibbles: "tin vs generic metal", "jagged comb", "tail length".

## 5. The model, not the schema

| condition | found the beak/comb colour? |
|---|---|
| gemma + strict schema | no (n=3 contradictions, all quibbles) |
| gemma + **free text, no schema** | **no**, twice — same quibbles |
| qwen/qwen3-vl-32b-instruct + schema | no — n=0 both reps |
| mistralai/mistral-small-3.2-24b + schema | no — n=0 both reps |

Free text rules out constrained decoding as the cause: gemma misses it with no schema at
all. *Caveat on strength of evidence:* gemma has many reps; qwen and mistral have two each,
and the colour detector was a crude substring match. "All models fail" is well supported for
gemma and only weakly indicated for the other two.

## 6. Two pathologies confirmed as a side effect

- `matches_description: True` was returned on **every single call**, including ones listing
  three contradictions. This is exactly prod job `b9506307` as recorded in
  `contracts/story_memory.py`, and re-justifies ADR-034 making the list the gate.
- `differences_observed` came back as literally `"tin rooster"` and `"Contradictions:"` —
  fragments of the prompt and the schema, not observations — even when
  `providers._assert_field_order` passed. Field order is checked; field *content* is not.

## 7. Open items

1. **The gate is untrustworthy in both directions.** Any Objective 3 claim resting on
   `ref_verdict` needs this caveat until the ADR-018 fine-tune exists.
2. **A `VISION_PROVIDERS` pin for gemma is still worth doing** — it converts a 5-of-5 hang
   into a working call — but it is a latency/availability fix, NOT a correctness fix, and
   must not be described as fixing the reference gate. Needs an ADR (ADR-002 territory).
   Parasail's 1-in-4 stall rate and its recorded corruption incident (prod row `558afb6d`)
   both argue against pinning it alone.
3. **`syn-001` may not be representative.** Every conclusion from the last two sessions
   rests on one story that `--limit 1` picked because it is index 0. A faceless rusty tin
   rooster is close to the hardest subject available. `--check-rosters` across all 30
   synthetic stories is text-only, free, and would settle whether 2/7 is a floor from an
   adversarial case or a representative rate. **Do this before optimising anything.**
4. **`text_free`** — 16 of 19 false, measured across two runs as changing zero outcomes.
   Levers unchanged: the two-line demotion to rank-only (`lettering-suppression.md` §4.6.2)
   or making the judge quote the text it saw.
5. **The tin rooster** — do not engineer against it until item 3 says such subjects are
   common in the corpus.

## 8. Note for probe authors

`providers._bounded` exists because httpx does not honour its own timeout here. A probe that
calls the SDK directly will hang with no ceiling (observed: 31 minutes). `_bounded` also
abandons non-daemon threads, so a script that uses it will never exit on its own — finish
with `os._exit(0)`. Use `python -u` and redirect to a file; a pipe buffers everything until
the process ends.
