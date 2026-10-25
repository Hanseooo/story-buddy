# 01 — Audit: why moderation over-refuses

**Status:** ready-for-agent
**Type:** research
**Progress:** open
**Blocked by:** None
**Conflict gate:** ADR-011, `AGENTS.md` child-safety rules, ADR-003. Reading and measuring is
allowed. Proposing a change to the stack or the graph needs the owner's verdict first.
**Phase:** [Post technical defense](../../post-technical-defense/map.md)

## Question

Which moderation layer refuses benign children's stories and images, how often, and why? Would a
written policy fix it without letting real unsafe content through? Separately, what would a
teacher-held flagged run take?

## Starting evidence (2026-10-25)

- There is no banned-word list. Text runs Llama Guard 4, then `gpt-oss-safeguard-20b`; a flag from
  either fails the story (`backend/pipeline/input_gate.py:46-63`, models in
  `backend/app/config.py:58-70`).
- The text backstop prompt gives `gpt-oss-safeguard-20b` no written policy, only "safe or unsafe for
  ages 5–12" (`backend/providers.py:907`). That model is built to apply a policy it is given.
  *Inferred* cause of over-strictness, not measured.
- Image moderation: `mistral-small-3.2-24b` primary, `gemma-3-27b` backstop (`config.py:65-70`).
  The image backstop prompt is at `providers.py:929`.
- *Measured* in the B6 campaign (2026-09-16/17): 4 of 30 synthetic stories (syn-001, -017, -022,
  -027) were quarantined by the image backstop after the primary said safe. The owner found no safety
  concern in syn-022 or syn-027. The primary errored 15+ times (120 s timeouts), leaving the backstop
  to decide alone. fal's own checker separately refused syn-018, syn-019 and don-015 (*The Red
  Shoes*). Find the repository record of these counts before citing them.
- An operator-only override exists, empty in production: `scene_moderation_overrides`
  (`config.py:99`).
- `output_mod` runs inside the per-scene loop (`AGENTS.md`, graph), so a hold would pause mid-book.

## Investigate

- What the panel saw flagged at the defense. Find the job and its `failure_reason`.
- A replay set from stored material: the B6 quarantines, the defense input, the Filipino/Taglish
  probe-4 cases, and a small set of truly unsafe cases so a miss shows up. Per layer: flags, errors,
  agreement.
- Whether a written children's-story policy for the text backstop, and the image backstop if it
  helps, lowers false alarms without new misses. A replay through OpenRouter is paid; propose it with
  a cost.
- Whether combining the layers differently (both must flag, or a tie-break) is safer than tuning a
  prompt. Name what ADR-011 would need.
- Teacher-held runs: where the pause would sit, how long a child waits, what the child sees
  (`docs/specs/kid-flow-pause-lifecycle.md`, `docs/specs/kid-flow-failure-semantics.md`), and what the
  teacher sees, given they would view a flagged image.

## Edge cases the answer must cover

- A teacher releases an image that is actually unsafe.
- No teacher acts for hours or days.
- A primary classifier that errors leaves one conservative layer deciding alone.
- fal's checker refuses before our layers run, so it cannot be overridden.
- The child must never see a moderation category or `jobs.error`.

## Done when

- Per-layer false-alarm and miss counts on the replay set, labelled *measured*, with denominators.
- Options for the policy, the layer combination and the teacher hold, each with tradeoffs and the ADR
  or ethics change it needs.
- Cost estimate and a go/no-go.

## Comments
