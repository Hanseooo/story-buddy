# ADR-036 — The RQ job deadline is a latency bound, not a safety bound: raise it to 1800s and cap regenerations when it binds again

**Status:** Accepted (2026-08-14) · **supersedes the `900` in `ca2479c`** ("increase RQ job timeout to 900s to
prevent premature worker kills") · **does not amend ADR-025** (`IMAGE_BUDGET` keeps sole ownership of spend) ·
**does not amend ADR-024** (`RECURSION_LIMIT` keeps sole ownership of loop depth) · **restates one consequence
of ADR-033** without changing its decision · config constant only → **no schema change, no `schema_version`
bump**

**Context:** production job `37b21dc2` (2026-08-13, `cel` preset, 7 scenes) died on RQ's deadline. The
traceback lands inside `consistency_check.judge_attempt` → `providers._bounded`, and the last log line before
it is:

```
14:23:04  regenerate: scene_id=s7 attempt_n=2 failure_reasons=['wrong_colour', 'wrong_body_feature',
          'wrong_clothing', 'wrong_style', 'character_absent'] ... paid=True
14:23:15  HardJobTimeout: Task exceeded maximum timeout value (900 seconds)
```

**The last scene's last permitted attempt, eleven seconds in, one judge call short of `_finish`.** Working back
from the SIGALRM, the horse dequeued at ≈14:08:15; the row was created at 14:03, so ≈5 minutes were the reveal
pause and the queue, and the full 900s were the resume's own.

**This is a resume, and that is the load-bearing detail.** `resume_storybook_job` re-enters the graph at
`reveal`, which `pipeline/graph.py:117` places **ahead of every scene node**. So a resumed book draws all seven
scenes and every retry inside one fresh window — the same work a cold run does, on the same clock, after a
human has already spent thinking time at the reveal. The deadline was never sized for the entrypoint that does
the most work.

**900s was not wrong, it was thin.** Its immediate neighbours on the same day finished:

| job | scenes | regens | outcome |
|---|---|---|---|
| `3cc05c4b` | 6/7 | 4 | complete |
| `fd2a6025` | 3/7 | 7 | complete |
| `484651e2` | 5/9 | 5 | complete |
| `37b21dc2` | — | — | **killed at 900s** |

A retry-heavy 7-scene book crosses the line and a calm one does not, which is the signature of a threshold set
just under the working range rather than of a runaway.

### The finding that decides the shape of the fix

**The deadline is not what protects this project from a runaway job. Two tighter bounds already do, and both
sit ahead of it:**

| bound | value | what it actually stops | enforced at |
|---|---|---|---|
| `IMAGE_BUDGET` | `MAX_SCENES * 2 + 15` = **45** | paid fal draws — the money | `generate_scene.py:72`, `regenerate.py:40`, before any spend (ADR-025 D4) |
| `RECURSION_LIMIT` | `MAX_SCENES * 5 + 17` = **92** | super-steps — an unterminating graph | `run_job.py:191`, `:224` (ADR-024) |
| `JOB_TIMEOUT_SECONDS` | **900 → 1800** | wall clock only | RQ `SIGALRM`, via `run_worker._HardDeathPenalty` |

So raising the clock **does not** raise worst-case spend and **cannot** admit an infinite loop: a pathological
job hits 45 images or 92 super-steps and raises a real, attributable error long before either clock. What the
clock buys is the *legitimately slow* book, and what it costs is queue latency. That reframing is the decision.

> **⚠️ The two table rows above are superseded by ADR-037 (2026-08-15).** With `MAX_SCENES` 15 → **10**,
> `IMAGE_BUDGET` is now `MAX_SCENES * 4 + 15` = **55** and `RECURSION_LIMIT` is `MAX_SCENES * 7 + 17` = **87**.
> The *argument* above is unchanged and is why ADR-037 kept both breakers ahead of the clock — only the
> numbers moved. `app/config.py` and `test_config.py` are authoritative; the line references in the
> "enforced at" column predate the `check_image_budget` extraction.

**Corollary, stated plainly because it is the thing a future reader will get backwards: a deadline cannot tell
a slow book from a broken one.** It is the crudest bound in the system and the only one whose error message
names nothing useful — `Task exceeded maximum timeout value` identifies no scene, no character, no provider.
Every bump trades diagnosability for headroom. This is the last one that should be made on those terms.

### Decision

1. **`JOB_TIMEOUT_SECONDS = 1800`**, in `app/main.py`, applied at **both** enqueue sites
   (`main.py:122` cold, `:166` resume). One named constant rather than two literals: the two entrypoints share
   one graph and one deadline, and the resume is the path that needs the room, so they must not drift.
2. **Both entrypoints keep the same value.** A larger budget for the resume alone was considered and rejected —
   it encodes the accident that `reveal` sits early, and it would silently become wrong the moment the reveal
   moves.
3. **This is the last bump.** When 1800s binds again, the answer is **a cap on total regenerations per book**,
   not 3600s. A regen cap fails with a number attached (*"book exhausted 12 regenerations"*), degrades to a
   finished book of best-of attempts rather than to nothing, and bounds the thing that actually consumes the
   clock. The deadline then goes back to being what it should be: a backstop against a hung process, not a
   budget.
4. **`CALL_TIMEOUT_SECONDS` is unchanged at 120s.** It bounds one provider call, is orthogonal to this, and was
   not implicated — `_bounded` had not run out when the SIGALRM landed.

### Consequences

- **Worst-case wait for a queued child doubles, 15 → 30 minutes.** This is the real cost and it lands on a
  classroom, where children submit in a burst against a single-process worker. Against ADR-017's pilot (N≈8–15)
  a tail job now blocks the queue twice as long. Accepted because the alternative on the table was a book that
  fails outright after 15 minutes, which is worse for the same child.
- **ADR-033's direct connection is now held up to 30 minutes, not 15.** Its *count* is unchanged — the worker
  is single-process, so it remains at most one direct connection at a time, and that ADR's decision stands
  exactly as written. What moves is duration, which makes its own ⚠️ consequence bite harder: **checking
  `max_connections` before raising worker replicas is now more urgent, not less.** A held connection that lasts
  twice as long makes an N-replica move fail sooner and more reliably.
- **Worst-case spend is unchanged.** `IMAGE_BUDGET` is the money bound and this does not touch it. A job that
  now runs 30 minutes still cannot draw a 46th image.
- **ADR-002's amendment gains headroom it was told it did not have.** Its own note reads *"~180s of timeout plus
  ≤120s of backoff … fits inside the 900s RQ job timeout for one call, not for several in the same book"*, and
  names the RQ deadline as the first suspect if books start dying there. That prediction came true on
  `37b21dc2`. The arithmetic now fits for roughly twice as many saturated calls per book. **The figure `900` in
  that amendment, in ADR-033's consequence, and in ADR-033's closing qualification is superseded by this ADR;
  those passages are frozen and were deliberately not edited.**
- **`ca2479c`'s reasoning is preserved, only its number is replaced.** It raised the deadline to stop premature
  worker kills; this raises it further for the same reason, on an entrypoint that did not exist in its form when
  that commit was written.
- **Diagnosability gets worse before it gets better.** Between this ADR and the regen cap, a book that exhausts
  1800s still fails with a message naming nothing. Until the cap lands, the log line immediately preceding the
  traceback — `regenerate: scene_id=… attempt_n=…` — is the only thing that identifies where a killed book was.
  Do not remove it.

### Alternatives

- **A regeneration cap now, instead of the bump.** The right end state (decision 3) and rejected only as the
  *immediate* fix: it needs a threshold nobody has data for yet. `fd2a6025` completed at 7 regens, so any cap
  worth having sits above that, and choosing it from four jobs would be guessing at the number this ADR is
  supposed to stop guessing at. Bump first, gather the distribution, then cap.
- **Move `reveal` after scene generation** so a resume re-enters late and cheaply. Rejected: it contradicts
  ADR-029, whose entire point is that the child approves the *characters* before the book is drawn. Drawing
  first and asking after is the spend this project is organised to avoid.
- **Per-scene deadlines instead of one job deadline.** Genuinely better shaped — it fails naming a scene — but
  RQ arms one SIGALRM per job, so this means owning timing inside the graph. Reconsider it together with the
  regen cap, which needs per-scene accounting anyway.
- **3600s.** Rejected. It is this decision again with a worse queue and no new information, and it would make
  the regen cap easier to keep postponing.
- **Concurrent workers, so one slow book stops blocking the queue.** Rejected here, and not because it is a bad
  idea — it is squarely an ADR-033 database decision (N replicas = N held direct connections against a fixed
  ceiling, failing as `FATAL: too many connections` before the first checkpoint is written). It needs its own
  ADR and its own session, not a paragraph in a timeout change.
