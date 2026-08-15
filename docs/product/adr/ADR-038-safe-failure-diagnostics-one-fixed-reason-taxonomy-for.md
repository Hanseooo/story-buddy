# ADR-038 — Safe failure diagnostics: one fixed reason taxonomy for child and teacher recovery

**Status:** Accepted (2026-08-15; owner approved the design, written-spec review pending) · **amends
ADR-025 Decision 5** · no `StoryMemory` or database-shape change

**Context:** ADR-025 intended an extensible failure taxonomy, but the built worker collapses every
non-input failure into `machine`. The child sees “the machine got stuck” for a flagged generated
character, a provider outage, an exhausted allowance, an image-breaker trip, a graph defect, and a
dead RQ work process. The generic copy avoids blame but prevents useful recovery. Rendering
`jobs.error` would appear more precise while leaking exception internals, un-redacted text, provider
details, and unstable implementation language.

**Decision:**

1. `jobs.failure_reason` remains extensible text and uses the fixed safe values `child_text`,
   `character_safety`, `scene_safety`, `service_busy`, `service_limit`, `book_limit`,
   `worker_stopped`, and `system_error`. No migration or parallel diagnostic payload is added.
2. Known pipeline sentinels, installed provider exception types, and response status codes select a
   reason once in the existing worker terminal handlers. Arbitrary exception prose never selects
   child-facing copy. Null, old, ambiguous, and unknown values fall to `system_error`.
3. Only an explicit provider credit or quota response becomes `service_limit`. A response-token
   ceiling, malformed output, authentication/configuration failure, or ambiguous “limit” message
   remains `system_error`; the product does not guess at account state.
4. The RQ horse-death handler writes `worker_stopped` directly and retains its compare-and-set guard.
   A browser wait never becomes a crash verdict. Dead-container detection remains a separate worker
   infrastructure concern.
5. Children and teachers see the same safe cause in audience-appropriate language. Neither sees
   `jobs.error`, provider names, moderation categories, flagged phrases, or stack traces. A compact
   story reference exposes an abbreviated job ID and can copy the complete ID.
6. `service_limit` and `book_limit` omit the paid retry action and direct the child to a teacher.
   Other retry/revise actions retain the existing explicit-new-job behavior. No automatic retry,
   partial restart, heartbeat, or support workflow is introduced.

**Consequences:**

- Failure UX becomes specific enough to guide recovery without turning exception text into a public
  interface or a moderation-evasion tutorial.
- The existing `FailureScreen`, job row, Realtime subscription, terminal status, and retry economics
  remain the only mechanisms. The implementation adds classification and copy, not infrastructure.
- Provider exhaustion can be under-classified as `system_error` when the upstream response is
  ambiguous. That is preferable to falsely claiming that credits ran out.
- A dead container can still leave a running row until an external mechanism marks it terminal.
  The loading screen remains honest by saying only that the current stage is taking longer.

**Alternatives:**

- **Infer the cause from `current_stage`.** Rejected because stage identifies where execution last
  progressed, not why it stopped; it would produce confident but false explanations.
- **Add a structured diagnostic column or object.** Rejected because no consumer needs more than one
  safe cause and one recovery action.
- **Render sanitized fragments of `jobs.error`.** Rejected because sanitization would become a second,
  brittle public contract over provider and exception prose.
