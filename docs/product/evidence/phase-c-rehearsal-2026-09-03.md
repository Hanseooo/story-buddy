# Phase C rehearsal — the corpus cannot supply the hard negatives the design requires

**Date:** 2026-09-03 · **Cost:** $0 (no provider calls, no database writes) ·
**Script:** `scripts/rehearse_selection.py` · **Bundles:** `data/judge/corpus-smoke-h` (real, `a723126`)

Run before the campaign, which is what makes it useful: the defect below is fatal at step 09 and
step 13, and both of those run *after* the ~$25 is spent.

## What was rehearsed

Steps 09–13 had never executed against real bundles. The modules themselves are unit-tested
(143 tests across `test_dataset_selection`, `test_finetune_dataset`, `test_finetune_llamafactory`,
`test_finetune_manifest`, `test_materialize_pairs` — all passing), so what was untested was the
chain against real generated data, not the functions.

`build_dataset --candidate-report` runs clean on the real bundles and emits well-formed JSON. Every
`candidates` list came back **empty**. That is the finding, not a glitch.

## The rule

`dataset_selection.validate_hard_negative_matches` (`:361-385`) requires all of:

| Line | Rule |
|---|---|
| `:361` | `set(matches) != set(train_characters)` → **hard fail**. Every synthetic train character with a canonical reference needs exactly one match. |
| `:372` | species compared by **exact casefold string equality** |
| `:379` | art style must be **exactly equal** |
| `:384` | the target needs at least one finalized natural scene |

`candidate_report` (`:113-158`) applies the same species+style rule when listing eligible pairings.
`PREREGISTRATION_OBJ4.md:564` states the design intent: constructed negatives are frozen
"matching character species and art style".

## Measured on the real bundles

```
train characters requiring a hard-negative match: 4
  syn-001:c0     species='hedgehog'     style=cel       scenes=5
  syn-001:c1     species='tin rooster'  style=cel       scenes=4
  syn-002:c0     species='human'        style=gouache   scenes=5
  syn-002:c1     species='sheep'        style=gouache   scenes=4

legal pairings found: 0 / 4 characters
FAIL -- ManifestError: every synthetic training reference requires exactly one hard-negative match
```

Species strings come from the extractor, not from a declaration, and they carry modifiers
(`'tin rooster'`, not `'rooster'`), which makes exact-equality matching *harder*, not easier.

## Projected across all 24 synthetic train stories

Species read from each story's own introduction in `corpus_synthetic.json`; styles are declared.

| Style | Train characters | Have a same-species partner |
|---|---|---|
| cel | 10 | **0** |
| gouache | 10 | 2 — Marisol (syn-002), Nonoy (syn-017) |
| cut_paper | 10 | 2 — Ate Rina (syn-012), Lala (syn-021) |
| **Total** | **30** | **4** |

**26 of 30 train characters have no legal hard-negative partner.** Only humans repeat within a
style, and cel has just one human. This is a projection: species is extracted at generation time,
so the exact strings are not knowable until the campaign runs. The direction is not in doubt — the
synthetic corpus was authored with deliberately distinctive creatures, one per story.

## Why this exists

Two requirements pull against each other, and nothing in the repo reconciles them.

- A character-consistency corpus wants **distinctive** characters. That is what makes a consistency
  failure legible, and the corpus delivers it: a gecko, a paper crane, a two-spouted kettle, a
  storm cloud on nine raindrop feet.
- The hard-negative rule wants **species collisions**, because a constructed negative is only hard
  when the two characters could plausibly be confused.

`candidate_role` is `not_applicable` on all 30 synthetic stories, which is consistent with the
corpus never having been authored to supply cross-character negatives at all.

## What this does NOT show

- It does not test `freeze_dataset` or `to_llamafactory` on real data. The selection blocker is
  upstream of both, so neither could be reached.
- It says nothing about the generation half, which is tested (2 stories end to end at `a723126`).
- It is not a judgement on the fine-tune design. Hard negatives are sound; the corpus does not
  supply them.

## Open decision

Not decided here, and it needs an ADR plus a preregistration amendment because
`PREREGISTRATION_OBJ4.md:564` states the species+style rule as a committed design:

1. **Relax the completeness rule** so a character with no eligible partner may have no hard
   negative. Smallest code change; weakens the negative set the design argued for.
2. **Relax the matching rule** (drop style equality, or normalize species). Does not help — even
   ignoring style, only the 5 humans collide.
3. **Change the corpus** so species repeat within a style. Largest change: the stories are written,
   and the corpus is a hashed input (`intake_sha256`).

Option 2 is measured to be insufficient. 1 and 3 are real choices with different costs.
