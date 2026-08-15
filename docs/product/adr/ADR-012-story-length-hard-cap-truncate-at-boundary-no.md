# ADR-012 — Story length: hard cap + truncate-at-boundary (no summarization)

**Status:** Accepted

**Context:** Over-length stories must be handled, but AI-summarizing the child's story means illustrating the *summary*, not their narrative — bad experience and an evaluation-validity problem.

**Decision:** **Hard word cap (~500–800 words, tunable)** with a live indicator; if exceeded, **truncate at a scene boundary** with a kid-friendly "let's make a book of the first part." **No silent summarization.**

**Consequences:** Captions and scenes always reflect the child's actual words. Very long stories lose their tail (acceptable; rare for the target age).

**Alternatives:** Auto-summarize — rejected (fidelity + validity). Chunk into chapters — possible Future Work.
