# Failure Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide clear, honest, and safe failure explanations with actionable next steps to children and teachers without exposing raw errors or implementation details.

**Architecture:** A new classifier in the backend maps worker exceptions to one of 8 safe reasons before saving to `jobs.failure_reason`. The frontend reads this value to show distinct child-friendly copy, appropriate retry controls, and a compact story reference ID, while the teacher dashboard displays safe diagnostic labels.

**Tech Stack:** Python (FastAPI, RQ), Next.js (React), Supabase Postgres

## Global Constraints

- No unmoderated generated image ever reaches a child.
- Open-weight models only. Model IDs live in `backend/app/config.py`.
- Architecture is locked; ADR-038 must be accepted and relevant docs amended in the same change.
- `jobs.failure_reason` is text and requires no migration. Unknown values map to `system_error`.
- Deterministic tests mock every model call and must stay green.

---

### Task 1: Backend Classifier & Worker Modifications

**Files:**
- Create: `backend/worker/failure_classifier.py`
- Modify: `backend/worker/run_job.py`
- Modify: `backend/worker/run_worker.py`
- Modify: `backend/tests/test_run_job.py`
- Modify: `backend/tests/test_run_worker.py`
- Create: `backend/tests/test_failure_classifier.py`

**Interfaces:**
- Consumes: Raw exceptions raised by the LangGraph pipeline or RQ.
- Produces: `classify_failure_reason(exc: BaseException) -> str` which returns one of the 8 safe values.

- [ ] **Step 1: Write tests for the classifier and worker integration**

```python
# backend/tests/test_failure_classifier.py
import pytest
from httpx import NetworkError, HTTPStatusError
from openai import RateLimitError, InternalServerError
from worker.failure_classifier import classify_failure_reason

def test_classify_exact_sentinels():
    assert classify_failure_reason(Exception("content_flagged")) == "child_text"
    assert classify_failure_reason(Exception("ref_flagged")) == "character_safety"
    assert classify_failure_reason(Exception("output_moderation_failed")) == "scene_safety"
    assert classify_failure_reason(Exception("moderation_error")) == "service_busy"
    assert classify_failure_reason(Exception("image budget exceeded")) == "book_limit"

def test_classify_service_busy():
    assert classify_failure_reason(NetworkError("timeout")) == "service_busy"
    assert classify_failure_reason(InternalServerError("500", response=None, body=None)) == "service_busy"

def test_classify_service_limit():
    assert classify_failure_reason(RateLimitError("429", response=None, body={"error": {"code": "insufficient_quota"}})) == "service_limit"
    assert classify_failure_reason(Exception("HTTP 402 Insufficient credits")) == "service_limit"

def test_classify_system_error():
    assert classify_failure_reason(ValueError("bad value")) == "system_error"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest backend/tests/test_failure_classifier.py -v`
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement the failure classifier**

```python
# backend/worker/failure_classifier.py
import httpx
import openai
from typing import Optional

def classify_failure_reason(exc: BaseException) -> str:
    msg = str(exc)
    # Exact sentinels
    if msg == "content_flagged": return "child_text"
    if msg == "ref_flagged": return "character_safety"
    if msg == "output_moderation_failed": return "scene_safety"
    if msg == "moderation_error": return "service_busy"
    if msg == "image budget exceeded": return "book_limit"
    
    # Provider limits
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 402: return "service_limit"
    if isinstance(exc, openai.RateLimitError):
        code = getattr(exc, "code", None)
        if code == "insufficient_quota" or (isinstance(exc.body, dict) and exc.body.get("error", {}).get("code") == "insufficient_quota"):
            return "service_limit"
        return "service_busy"
        
    # Busy/Transient
    if isinstance(exc, (TimeoutError, httpx.TimeoutException, httpx.NetworkError)): return "service_busy"
    if isinstance(exc, openai.InternalServerError): return "service_busy"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500: return "service_busy"
    
    # Fallback
    return "system_error"
```

- [ ] **Step 4: Update run_job.py**

```python
# In backend/worker/run_job.py, import the classifier
from worker.failure_classifier import classify_failure_reason

# In run_storybook_job and resume_storybook_job except blocks, replace:
# failure_reason = "child_text" if msg == "content_flagged" else "machine"
# With:
failure_reason = classify_failure_reason(exc)
```

- [ ] **Step 5: Update run_worker.py**

```python
# In backend/worker/run_worker.py, in _report_failed
# Replace "failure_reason": "machine" with "failure_reason": "worker_stopped"
```

- [ ] **Step 6: Update existing run_job and run_worker tests**

```python
# Run uv run pytest to find failing tests in test_run_job.py and test_run_worker.py
# Update test_run_worker.py:
# assert payload["failure_reason"] == "worker_stopped"
# Update test_run_job.py assertions to match the new taxonomy instead of "machine"
```

- [ ] **Step 7: Run backend tests to verify pass**

Run: `uv run pytest -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat(backend): implement safe failure reason classifier"
```

---

### Task 2: Frontend FailureScreen UI

**Files:**
- Modify: `frontend/components/FailureScreen.tsx`
- Modify: `frontend/components/FailureScreen.test.tsx`
- Modify: `frontend/lib/types/jobs.ts`

**Interfaces:**
- Consumes: The `failure_reason` string and `jobId` passed as props.

- [ ] **Step 1: Update type definitions**

```typescript
# frontend/lib/types/jobs.ts
export type FailureReason = 
  | "child_text" 
  | "character_safety" 
  | "scene_safety" 
  | "service_busy" 
  | "service_limit" 
  | "book_limit" 
  | "worker_stopped" 
  | "system_error"
  | "machine" // legacy
  | null;
```

- [ ] **Step 2: Write tests for FailureScreen**

```typescript
// Add to frontend/components/FailureScreen.test.tsx
import { render, screen } from '@testing-library/react';
import { FailureScreen } from './FailureScreen';

describe('FailureScreen safe reasons', () => {
  it('renders child_text', () => {
    render(<FailureScreen reason="child_text" />);
    expect(screen.getByText("Some words need changing before we can make this book.")).toBeInTheDocument();
    expect(screen.getByRole('button', { name: "Change my words" })).toBeInTheDocument();
  });
  
  it('renders service_limit with no retry', () => {
    render(<FailureScreen reason="service_limit" jobId="1234567890" />);
    expect(screen.getByText("The story-making allowance has run out.")).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: "Try again" })).not.toBeInTheDocument();
    expect(screen.getByText("12345678")).toBeInTheDocument(); // Story ref
  });
  
  it('renders system_error for unknown values', () => {
    render(<FailureScreen reason="unknown_garbage" />);
    expect(screen.getByText("Something interrupted your story.")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Update FailureScreen.tsx**

Update the component to map the `reason` prop to the exact child-facing explanations in the spec.
Add a story reference block using `jobId.slice(0, 8)` with a button to copy the full `jobId` to clipboard, providing an accessible label and visual confirmation without relying on color alone. Use `role="alert"` for the error messages.
Ensure the component enforces accessibility and interaction constraints:
- Retry controls must disable while submitting.
- Retry controls must retain a 44px minimum target.
- Expose an inline failure if the new submission cannot be created.
- Repeating decorative motion must stop under `prefers-reduced-motion: reduce`.
- Error copy must remain readable at 320px and 200% zoom.

- [ ] **Step 4: Run component tests**

Run: `pnpm test components/FailureScreen.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): update FailureScreen with safe taxonomy and story reference"
```

---

### Task 3: Frontend Integration & Documentation

**Files:**
- Modify: `frontend/app/s/[profileId]/process/[jobId]/page.tsx`
- Modify: `frontend/app/s/[profileId]/process/[jobId]/page.test.tsx`
- Modify: `frontend/app/s/[profileId]/book/[jobId]/page.tsx`
- Modify: `frontend/app/classroom/[classroomId]/books/page.tsx`
- Modify: `frontend/app/classroom/[classroomId]/books/page.test.tsx`
- Modify: `docs/specs/kid-flow-failure-semantics.md`
- Modify: `docs/specs/kid-flow-reader-and-wait-states.md`
- Modify: `docs/specs/teacher-review-and-approval.md`

**Interfaces:**
- Connects the database values to the updated components and amends docs to accept ADR-038.

- [ ] **Step 1: Update process page logic**

In `frontend/app/s/[profileId]/process/[jobId]/page.tsx`, pass `reason={row?.failure_reason}` to `FailureScreen`.
Update the stall text at 90 seconds from `"Still going..."` to:
`"This step is taking longer than usual. Your progress is saved, so you can leave and come back."`
Ensure `aria-live="polite"` is used. Update `page.test.tsx` to assert this new text.

- [ ] **Step 2: Update book page logic**

In `frontend/app/s/[profileId]/book/[jobId]/page.tsx`, pass `reason={row?.failure_reason}` and `jobId={jobId}` to `FailureScreen` in terminal branches.

- [ ] **Step 3: Update teacher dashboard**

In `frontend/app/classroom/[classroomId]/books/page.tsx`, within `FailedBookRow`, display `job.id.slice(0, 8)` with a copy control.
Add a switch statement to map `job.failure_reason` to the exact teacher-facing labels (e.g. `service_busy` -> "A required story-making service was temporarily unavailable.") with `system_error` as the fallback.
Update `page.test.tsx` to verify the mapping.

- [ ] **Step 4: Update Documentation**

Edit the three spec files to reflect the 8-value taxonomy, replacing any mentions of the old two-value ("child_text" / "machine") assertions, as required by ADR-038.

- [ ] **Step 5: Run tests to verify all pass**

Run: `pnpm test`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/ docs/
git commit -m "feat(frontend): integrate failure reasons in pages and update docs"
```
