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

### Candidate run metadata (owner-supplied SQL result, 2026-10-26)

- Job `314fafc9-4020-4114-9a75-25a0c8059d47`, created `2026-10-24 01:22:35.226904+00`,
  is recorded as `status=failed`, `failure_reason=scene_safety`, `approved_at=null`, with last
  published `current_stage=consistency_check:1/1`.
- This verifies the stored failure classification, not which classifier flagged, what it saw,
  whether another classifier errored, or whether the flag was appropriate. Current repository
  code maps `output_moderation_failed` to `scene_safety`; deployed revision remains unverified.
  The progress label is not independent evidence that the consistency judge caused the failure.
- A trace URL was supplied. The agent's web tool could not access it and no browser was available;
  trace observations, stored images and checkpoint state have not yet been inspected. No false-alarm
  classification or replay count is established by this row.
- A second owner-supplied SQL result lists eight root-namespace checkpoints for the same thread,
  steps 8 through 15. The latest is `1f1cf4b1-69fd-69b5-800f-bec6ac0d6cc1`, timestamp
  `2026-10-24T01:34:43.426741+00:00`, with source `loop`. Checkpoint history therefore exists;
  the state has not been decoded. Channel names accumulate and are not execution/verdict evidence.
  In particular, `branch:to:output_mod` in channel versions is not proof of a completed moderation
  call, and the listed timestamps do not isolate classifier latency from retries or human waiting.

### Documentation check (2026-10-26; no classifier calls)

**Verified official guidance:**

- Meta documents Llama Guard prompts with explicit category and conversation sections, input/output
  role selection, and customizable category definitions. The model card describes a general hazard
  taxonomy, not a Grade 5–6 storybook suitability rubric. Its limitations include dependence on
  training data for multilingual/common-sense judgments and susceptibility to prompt injection.
  Sources: [Meta prompt format](https://dev.meta.ai/llama/docs/model-cards-and-prompt-formats/llama-guard-4),
  [official model card](https://huggingface.co/meta-llama/Llama-Guard-4-12B/blob/main/README.md).
- OpenAI recommends supplying safeguard's written policy as a system message and the material to
  classify as a user message. Its guide calls for definitions, violating/non-violating criteria,
  boundary examples, explicit output instructions, and manual escalation for ambiguity. It also
  cautions that adding policies can reduce accuracy; policy changes require experimentation.
  Source: [gpt-oss-safeguard guide](https://developers.openai.com/cookbook/articles/gpt-oss-safeguard-guide).
- Neither checked guide supplies a blanket exemption for fictional stories or a validated
  children's-story rubric. How fiction, ordinary conflict, suspense and sadness are treated must
  be explicit in the project policy and evaluated, rather than inferred from model names.

**Verified local evidence:**

- `backend/providers.py:889–922` constructs broad ages-5–12 safe/unsafe prompts. The primary gets a
  short system instruction and user text; the backstop gets instruction and text in one user message.
  Neither application-built text prompt contains project rule definitions, allowed exceptions or
  boundary examples. Provider-side chat-template transformations were not inspected: this does not
  prove the effective Llama Guard prompt format is malformed.
- Audience drift remains unresolved: `docs/product/PRD_v2.md:151`,
  `docs/product/RESEARCH_PROTOCOL.md:340` and
  `docs/capstone/research_direction_and_goals.md:272` specify Grade 5–6, ages 10–12. The moderation
  prompts say ages 5–12 and the image backstop also refers to a young child. No age/prompt change
  was made. Whether that difference contributes to false alarms is unmeasured.
- `backend/providers.py:603` now raises on an empty or unrecognized verdict. Its comment records
  the historical empty-response-as-unsafe bug; that historical behavior is not the current parser.

**Hypotheses and limits:** Explicit project criteria and audience alignment are candidates for
controlled comparison, not demonstrated fixes. This documentation check cannot explain run
`314fafc9`, establish provider behavior, or supply false-alarm/miss rates. No database, trace, stored
image or live classifier was inspected, no paid probe ran, and no implementation changed. The audit
remains open: measured replay denominators, cost estimate and go/no-go are still missing.

### Short audit checkpoint (2026-10-26; paid replay deferred)

The owner accepted deferring the paid replay and using the code/document findings for the next
discussion. The short read-only audit is complete; the full measured audit remains open. No paid
classifier calls, database inspection, tests or implementation changes were made in this audit.

- The B6 historical refusal record was located in `docs/specs/obj4-readiness-audit.md` §7.5:
  four named unilateral backstop refusals, with human review reported as upholding the primary.
  This is historical evidence, not a current replay measurement or independently repeated review.
- Before replay, agree on the written labeling policy, target age range, label reviewer, text/image
  sample sizes, repeat count, spending cap and go/no-go criteria. Zero observed misses in a small
  sample does not establish safety generally.
- Image classifiers cover complementary categories: the primary screens NSFW content, while the
  backstop also screens violence and dangerous activities. Requiring both to flag could remove
  category coverage; treat this as an ADR decision requiring evidence, not a simple voting change.
- The defense run's stored failure classification is known; classifier attribution, flagged image,
  checkpoint contents and deployed revision remain unverified. Access to those artifacts is needed
  to diagnose that run, but does not itself require paid classifier calls.
- The map already records teacher-hold interview decisions, including waiting under existing
  retention/deletion rules. Further discussion should use those decisions and focus on unresolved
  policy and release safeguards rather than reopen settled preferences.

**Handoff:** Ticket 02 may continue policy/spec discussion using these limited findings, with the
measured audit dependency explicitly deferred rather than satisfied. This does not authorize build
work or accept ADR amendments. Tickets 05–15 retain their decision gates. At this checkpoint ticket
03 records implementation with signed-in browser verification pending, and ticket 04 records done.
