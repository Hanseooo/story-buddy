# 04 — Make evaluation locking and held-out resume fail closed

**What to build:** Held-out evaluation starts only from a fully validated immutable lock, and an interrupted run resumes from its already-written prediction evidence. Invalid lock fields, checkpoint identity drift, or modified prediction artifacts stop the run before held-out access continues.

**Blocked by:** 02 — Reconcile the Batch 3 implementation baseline.

**Status:** completed
**Labels:** `criticality:critical`, `complexity:high`

- [x] Lock creation and validation require the exact schema version, non-blank registered identifiers, normalized SHA-256 values, and a checkpoint whose path and digest match the selected candidate.
- [x] Held-out reservation and its audit event occur before any test manifest or test asset is read.
- [x] Completed immutable prediction files are hash-verified and reused on resume; only missing judge predictions are generated.
- [x] The access ledger distinguishes initial reservation, resume, completion, and failure without exposing story content or direct asset paths.
- [x] Concurrent or repeated lock creation cannot return ambiguous success or silently replace a different lock.
- [x] Failure tests cover malformed digests, checkpoint mismatch, invalid schema data, tampered predictions, partial completion, and a repeated resume.
- [x] Verification uses synthetic fixtures only and makes no provider, GPU, or real held-out calls.


## Verification (2026-08-28)

Criteria confirmed against committed code, not self-reported. Implementing commit: `1ecde5a`
"fix(obj4): fail closed on held-out resume" (2026-08-25, 5 files, +382/-81).

| Criterion | Evidence |
|---|---|
| Lock records schema version, normalized digests, checkpoint identity, required artifacts | `evaluate.py:371-436` |
| Lock creation cannot resolve ambiguously | `_publish_exclusive`, `evaluate.py:244` |
| Access ledger distinguishes reservation from completion | `evaluate.py:879`, status literal `"reserved" \| "resumed" \| "completed" \| "failed"` |
| Resume is hash-verified before held-out data is opened | `evaluate.py:371-436` with tests below |
| Failure coverage | `test_finetune_evaluate.py:246, 254, 269, 274, 280, 342, 439, 468, 1033` |

The boxes were previously unticked while the implementation was complete; this reconciles the
record. No code changed for this ticket.
