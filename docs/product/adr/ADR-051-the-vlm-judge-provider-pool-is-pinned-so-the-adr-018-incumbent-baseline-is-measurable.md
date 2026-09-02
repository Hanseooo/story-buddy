# ADR-051 — The VLM judge's provider pool is pinned, so the ADR-018 incumbent baseline is measurable

**Status:** Accepted (2026-09-02; owner approved the design in session before implementation) ·
**amends ADR-002** (one entry in an allowlist that ADR already prescribes; the aggregator decision,
the allowlist-not-blocklist rule, and the per-call-site rule are all untouched) ·
**does not amend ADR-004, ADR-018, ADR-025, ADR-028, or ADR-034** — no judge model change, no
gate predicate change, no retry-policy change · **no contract, schema, or `StoryMemory` change** ·
one dict entry in `backend/providers.py`

**Context:**

ADR-002 declined to pin `google/gemma-3-27b-it` on an explicit premise, recorded in
`providers.py:58`: *"gemma-3-27b-it serves five providers (none of them Venice), so pinning it
would shrink its pool for nothing."* **That premise is now falsified by measurement.** The pool
contains a dead endpoint, and OpenRouter prefers it.

Measured 2026-09-02, one reference-judge call shape, `CALL_TIMEOUT_SECONDS` shortened to 75s:

| backend | slug | reference-judge call |
|---|---|---|
| **DeepInfra** | `deepinfra` | **5 of 5 timeouts** at the bound — dead for this model |
| Parasail | `parasail` | answers in 6–10s; **1 of 4 stalls** |
| Nebius | `nebius` | answers in 2–6s; never observed to stall |
| Novita | `novita` | **404** — cannot serve `require_parameters` (strict schema) |

**Unpinned calls — production routing — failed 5 of 5.** Falsified along the way, each tested
directly and each negative: payload size (a *two*-image call succeeded while a smaller one-image
call timed out), vision-versus-text (a call with **no image** also hit the full bound), the
`RefVerdict` schema, the reference prompt, and determinism (byte-identical calls gave opposite
outcomes). This is a routing fault, not a property of references — and it explains why 19 scene
judge calls succeeded in the same run that lost both reference calls: repeated draws from a pool.

**The reason this is worth an ADR now is ADR-018, not the gate.** ADR-018 mandates four baselines
and makes one of them the deployment gate: *prompted `gemma-3-27b-it` with reason-then-score — the
incumbent, the thing to beat*, with rung C reading "loses to Gemma by more than 3 F1 points → do
not ship." `finetune/evaluate.py:643` implements that baseline through
`providers.judge_with_metadata(..., route="openrouter")`, which reads the **same
`VISION_PROVIDERS` dict** as the pipeline's `judge()` (`providers.py:193` and `:215`). Measured
today, that baseline would be run against a model that does not answer 5 times in 5. A fine-tune
that beats it wins for the wrong reason, rung A is unearned, and the first reviewer to ask why the
27B incumbent scored so badly is asking a fair question we would have no answer to.

⚠️ **This ADR does not fix the reference gate, and must never be cited as though it did.** Ground
truth for `syn-001`'s `ref-c1-1.png` was read off the image by hand, not from any model: the spec
demands *metal beak and comb*; the image shows a grey rust-patched metal body and tail but a
**bright yellow beak** and a **red comb and wattles**. Two-sided test — the real spec (must find
at least 1 contradiction) and a description hand-written to match the image (must find 0), three
reps each:

| provider | vs real spec (expect ≥1) | vs matched description (expect 0) |
|---|---|---|
| Parasail | 2, 3, timeout | **3**, 0, 0 |
| Nebius | **0, 0, 0** | **3, 3, 2** |

**Nebius is anti-correlated with the truth** — clean when it should flag, flagging when it is
clean. Across every run of the probe, neither surviving provider ever named the yellow beak or the
red comb; both returned quibbles ("tin vs generic metal", "jagged comb", "tail length"). The
failure survives removing the schema entirely (gemma in free text missed the colour twice) and
appears on `qwen/qwen3-vl-32b-instruct` and `mistralai/mistral-small-3.2-24b-instruct` as well.
That is a model-capability finding, it is the case ADR-018 was written to address, and it is out of
scope here. Full record: `docs/capstone/reference_judge_investigation_2026-09-02.md`.

**Decision:**

1. **Pin `google/gemma-3-27b-it` in `providers.VISION_PROVIDERS` to `["nebius", "parasail"]`.**
   One dict entry. No new code, no new call site, no new flag. Slugs verified against
   `GET https://openrouter.ai/api/v1/providers` on 2026-09-02.
2. **Allowlist, not `ignore: ["deepinfra"]`.** ADR-002's rule, and the reason it gave still holds:
   this model sits on the child-facing safety path, so a provider added to the pool later is
   excluded until someone measures it.
3. **Novita is excluded on measurement, not on suspicion.** It 404s on `require_parameters`, which
   `providers._chat` sends on every OpenRouter call.
4. **The stated purpose is availability, and only availability.** The justification of record is
   that ADR-018's incumbent baseline must be measured against a model that answers. Any future
   document claiming this change improved reference-gate correctness is contradicted by the
   two-sided table above, which is reproduced in this ADR for exactly that reason.
5. **No judge-model change.** ADR-018 fixes the incumbent as `gemma-3-27b-it`; swapping it now
   would make the baseline a different thing from the model the pipeline actually ships.
6. **No gate-predicate change.** `not verdict.contradictions and verdict.text_free` (ADR-034) is
   untouched, as is ADR-050's retry.

**Consequences:**

- ⚠️ **The safety path narrows from four providers to two.** `gemma-3-27b-it` is also
  `moderation_backstop_image_model` (`config.py:70`), and `classify_image_backstop`
  (`providers.py:762`) calls the same `judge()`. Two of the four were already unusable, so the
  *effective* pool does not shrink — but the headroom against a 429 does. If both pinned providers
  are saturated, `char_ref_mod` and `output_mod` degrade through the ADR-025 posture rather than
  killing a paid book. That posture is the mitigation; widening back to DeepInfra is not.
- ADR-018's `prompted_gemma` baseline, the ADR-011 image backstop, and the pipeline reference and
  scene judges are all fixed by the one entry, because all four resolve through `VISION_PROVIDERS`.
  Verified, not assumed: `providers.py:193` (`judge`) and `:215` (`judge_with_metadata`, `route="openrouter"`).
- Reference draws stop being spent on redraws triggered by a judge that timed out. `corpus-smoke-c`
  wrote `unchecked_references: 2` on a two-character book; that number should go to 0, and if it
  does not, the cause is no longer routing.
- **A pin is a dated measurement, not a durable property.** ADR-002 says a probe result carries its
  provider with it; `providers.py:76` records `venice` sitting in a list with no endpoint for the
  model at all until 2026-08-27. Re-measure before trusting this table in a later phase.
- **Not fixed here, and worth stating so it is not later mistaken for fixed:**
  `_assert_field_order` passed on verdicts whose `differences_observed` was literally
  `"tin rooster"` and `"Contradictions:"` — fragments of the prompt and the schema, not
  observations. Field *order* is checked; field *content* is not.
- The deterministic suite cannot catch this class — every test mocks `providers.py`. The check is
  `uv run pytest -m "smoke and not smoke_image"` before any deploy that changes a provider
  (ADR-002, AGENTS.md *Testing bright line*).

**Alternatives:**

- **`ignore: ["deepinfra"]`.** Rejected — ADR-002 chose allowlists for the safety path and that
  reasoning is unchanged.
- **Pin Nebius alone.** Rejected, and this was the trap. It is the fastest and the only one never
  observed to stall, and on the evidence available before the two-sided test it was the obvious
  choice. It returns **0 contradictions on a reference that plainly violates its spec**. Pinning it
  alone would make the gate run, pass everything, and write `unchecked_references: 0` — trading a
  visibly broken gate for an invisibly broken one. It stays in the pool for availability, and the
  pool is not a correctness argument.
- **Pin Parasail alone.** Rejected. It stalls 1 in 4, and ADR-002 Instance 4 recorded a
  schema-fidelity failure on Parasail (prod row `558afb6d`). That was a different model on the
  text path, so it is a caution rather than a disqualification — but it is not a single point of
  failure to volunteer for.
- **Use `order` to prefer one within the allowlist.** Rejected. It adds a second mechanism to
  express a preference no measurement supports: on correctness the two are bad in opposite
  directions, and there is no ranking to encode.
- **Swap to a larger open-weight VLM** (`qwen/qwen3-vl-235b-a22b-instruct`, `z-ai/glm-4.6v`, both
  on OpenRouter and both ADR-015-clean). Rejected as out of scope, twice over: it is an ADR-002 and
  ADR-018 model decision, and ADR-018's gate is a comparison against *the incumbent the pipeline
  ships*, so replacing the incumbent to make the incumbent look better inverts the experiment.
- **Do nothing until the fine-tune lands.** Rejected. The fine-tune's ship/no-ship gate *is* a
  comparison against this model, so an unmeasurable incumbent does not become less of a problem by
  waiting; it becomes a problem discovered at the point where it invalidates a result.

**Escape hatch:** if a real run shows the two-provider pool saturating on the safety path, the
answer is the ADR-025 degradation posture or a judge-model decision under ADR-002 — not restoring
DeepInfra, which was removed on 5-of-5 measured failure. And the reference gate itself stays
untrustworthy in **both** directions until the ADR-018 fine-tune exists; every Objective 3 claim
resting on `ref_verdict` carries that caveat, and this ADR does not lift it.
