# ADR-087 — The identity judge ships as selectable, and Gemma stays the default

**Status:** Proposed (2026-11-27) · awaiting the owner's acceptance · amends in part ADR-019 (the
serving host and the "ships in the live pipeline" premise) · amends in part the deployment gate in
`docs/specs/judge-finetune.md` §7.5 · spec: `docs/specs/judge-selector.md` · Objective 4 and
`PREREGISTRATION_OBJ4.md` are unchanged · revisit before real children use the app

## Context

ADR-019 planned to serve the fine-tuned judge on a scale-to-zero GPU host once it passed the
§7.5 ladder, and to replace prompted Gemma in the pipeline. Rungs A and B, the two that ship, both
require the fine-tune to beat the untuned base.

It did not. On the frozen held-out slice (329 pairs, 47 Different), as copied in
`docs/capstone/research_runbook.md` ("Exact values of the partial comparison"):

| Judge | F1 | Unreadable (of 329) |
|---|---|---|
| Untuned Qwen3.5-9B | 0.472 | 3 |
| Seed 1 (preselected, the registered result) | 0.310 | 40 |
| Seed 2 | 0.417 | 8 |

The project was still asked to deploy the fine-tuned judge in the live product (judge-selector Q1).
No child uses StoryBuddy. It is only demoed (owner, 2026-11-25).

## Decision

1. **The identity judge ships as selectable, and Gemma stays the default.** Whoever writes a book
   picks "Standard (Gemma)", "Qwen base" (untuned Qwen3.5-9B) or "Qwen fine-tuned" (seed 2). The
   choice is saved on the job and fixed for that book, reruns included.
2. **The fine-tune is not promoted.** On the measured held-out result (untuned F1 0.472, seed 1
   0.310, seed 2 0.417), neither seed beats the base, so §7.5's ship rungs are not met. Gemma stays
   the default and Qwen is an opt-in demo option, not a replacement.
3. **Seed 2 is the product option, chosen after the test results.** It had the best held-out F1 of
   the three seeds (0.417) and the fewest unreadable answers (8 of 329). This is a post-hoc pick for
   the demo and is disclosed as one. Seed 1 remains the registered Objective 4 result.
4. **Nothing hard-depends on the Vast server.** If the server is down, both Qwen options are
   disabled and Gemma is used. If a Qwen call fails mid-book, that check is retried once on Gemma
   and the record names the model that answered.
5. **Identity check only.** The choice routes only the identity call, `judge(JUDGE_PROMPT…,
   SceneVerdict)` (judge-selector SH-02). The scene-constraint check, the reference judge and both
   moderation layers keep their current models. The fine-tuned model never sits on the child-safety
   path (`judge-finetune.md` CC-1).
6. **Serving moves from scale-to-zero to an on-demand Vast.ai instance.** One vLLM server serves
   both Qwen options: the base by `model="Qwen/Qwen3.5-9B"`, seed 2 by its LoRA module name. It is
   turned on for rehearsal and the defense and off otherwise. The OpenAI-compatible route from
   ADR-019 stays.

## Consequences

- The product can show each judge answering a real book, which is what the deployment request
  asked for, without claiming the fine-tune is better.
- A book judged by Qwen may be judged worse than one judged by Gemma. That is a choice the writer
  makes, and Gemma is the default.
- The seed 2 option is not evidence for Objective 4. The paper reports seed 1 as registered, and
  any mention of seed 2 in the product says it was picked after the test results.
- Cost: $0.447/hr including a 100 GB disk on the last Vast rental, against about $1.73–2.72/hr
  for RunPod Serverless 48 GB. The owner estimated about $5–6 for roughly 10 hours, plus disk while
  stopped. There is no cold start while the instance is up.
- Measured adapter latency on an earlier Vast host was 21.9 s and 46.6 s per request, against a
  60 s client timeout. A Qwen-judged book can be much slower than a Gemma one.
- ADR-019's de-scope rule still holds: dropping the server costs only the Qwen options. Gemma
  books are unaffected.

## Release gate

Before real children use the app, revisit this decision: whether a judge that did not beat its
base may be offered at all, and whether the choice should be role-gated instead of visible to
everyone. Going back means hiding the dropdown and unsetting the Qwen server settings. Stored
choices then fall back to Gemma per call. No migration.

## Alternatives

- **Keep Gemma only and leave the fine-tune as a research result (§7.5 rung C or D as written).**
  Matches the measured result. Rejected by the owner: the deployment request needs the fine-tuned
  judge running in the product.
- **Replace Gemma with the fine-tune.** Rejected: neither seed beat the base, and this would move
  the registered gate after seeing the held-out numbers.
- **Seed 1, the registered result, as the product option.** Rejected for the demo: lower F1
  (0.310) and 40 of 329 answers unreadable.
- **Scale-to-zero hosting (Modal, RunPod Serverless), as ADR-019 planned.** Rejected: a cold start
  inside a book, a higher hourly price, and the tested serving config ran on Vast unchanged.
- **Role-gate the dropdown to the owner or researchers.** Rejected for the demo: the owner chose a
  visible control for UX.
