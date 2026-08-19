# 02 — Annotation UI Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the `/annotate` Next.js route by enforcing server invariants, preventing adjudicators from the standard queue, randomizing presentation order per-annotator, and ensuring rigorous 3-tier testing.

**Architecture:** 
- The UI will be updated to explicitly track "Same Character" state, disabling failure taxonomy checkboxes when active.
- `actions.ts` will rigorously validate payloads (rejecting invalid combinations of `same_character` and `failure_reasons`), block adjudicators, handle double-submits idempotently via Supabase upsert, and pseudo-randomly shuffle pending pairs using a string hash of `pair_id + annotator_id` to eliminate sequential context effects.
- Tests will span Tier 1 (Vitest component), Tier 2 (Vitest server action), and Tier 3 (pytest DB isolation).

**Tech Stack:** Next.js (App Router), Supabase SSR, Vitest, pytest.

## Global Constraints

- `same_character = true` REQUIRES `failure_reasons = []`.
- `same_character = false` REQUIRES `failure_reasons.length >= 1`.
- `anatomy_intact` (bool) and `text_free` (bool) must be explicitly provided (no undefined values).
- Double-submit handled with first-write-wins idempotency (`ON CONFLICT DO NOTHING`).
- Adjudicator accounts (`profiles.is_adjudicator = true`) are blocked from submitting ordinary annotations on `/annotate`.
- Server actions return ONLY `{ pair: { id, canonical_signed_url, scene_signed_url } }`.
- **Caching:** The `/annotate` route must be dynamically rendered to ensure randomized pair presentation is not cached by Next.js Router.

---

### Task 1: Enforce Server Invariants & Roles

**Files:**
- Modify: `frontend/app/(research)/annotate/actions.ts`
- Modify: `supabase/migrations/` (if `is_adjudicator` doesn't exist)

**Interfaces:**
- Consumes: `submitAnnotation`, `getNextPair` from current codebase.
- Produces: Updated `submitAnnotation` and `getNextPair` with explicit Auth/error handling, `is_adjudicator` check, explicit validation, and idempotency logic.

- [ ] **Step 1: Update `submitAnnotation` validation, Auth checks, and idempotency**

Modify `frontend/app/(research)/annotate/actions.ts`. Ensure strict Auth error handling. Add `is_adjudicator` to the profiles query and handle missing column/schema errors gracefully (fail secure). Add validation logic for the invariants. Use `.upsert` with `ignoreDuplicates: true`. At the end, call `revalidatePath` to clear Next.js Router cache for the route.

```typescript
// Replace the top of submitAnnotation:
import { revalidatePath } from 'next/cache';

export async function submitAnnotation(
  pairId: string, 
  failureReasons: string[], 
  sameCharacter: boolean,
  anatomyIntact: boolean,
  textFree: boolean
) {
  const supabase = await createSupabaseServerClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();

  if (authError || !user) { return { error: "Unauthorized" }; }

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  // Fail secure: if is_adjudicator doesn't exist or query fails, deny access
  if (profileError || profile?.role !== "researcher" || profile?.is_adjudicator) {
    console.error("Authorization error or invalid role:", profileError);
    return { error: "Unauthorized" };
  }

  // Server-Side Invariant Validation
  if (sameCharacter && failureReasons.length > 0) {
    return { error: "Invalid state: same_character is true but failure reasons provided" };
  }
  if (!sameCharacter && failureReasons.length === 0) {
    return { error: "Invalid state: same_character is false but no failure reasons provided" };
  }
  if (typeof anatomyIntact !== "boolean" || typeof textFree !== "boolean") {
    return { error: "Invalid state: anatomy_intact and text_free must be explicitly provided" };
  }

  // Insert annotation with first-write-wins idempotency
  const { error: insertError } = await supabase
    .from("annotations")
    .upsert({
      pair_id: pairId,
      annotator_id: user.id,
      same_character: sameCharacter,
      anatomy_intact: anatomyIntact,
      text_free: textFree,
      failure_reasons: failureReasons,
    }, {
      onConflict: 'pair_id,annotator_id',
      ignoreDuplicates: true
    });
    
  if (insertError) {
    console.error("Failed to insert annotation:", insertError);
    return { error: "Failed to save annotation" };
  }
  
  // Clear router cache to ensure the next fetch retrieves a fresh randomized pair
  revalidatePath('/(research)/annotate', 'page');
  
  // ... rest remains unchanged
```

- [ ] **Step 2: Update `getNextPair` role check and handle Auth errors**

Update the profile check in `getNextPair` in `frontend/app/(research)/annotate/actions.ts` to strictly handle `getUser()` errors and reject adjudicators securely.

```typescript
// In getNextPair:
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  if (authError || !user) { return { error: "Unauthorized" }; }

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  if (profileError || profile?.role !== "researcher" || profile?.is_adjudicator) {
    return { error: "Unauthorized" };
  }
```

### Task 2: Prevent Next.js Caching & Implement Pseudo-Random Pair Assignment

**Files:**
- Modify: `frontend/app/(research)/annotate/actions.ts`
- Modify: `frontend/app/(research)/annotate/page.tsx`

**Interfaces:**
- Produces: Reproducible hash-shuffled ordering for pairs per user that bypasses static caching.

- [ ] **Step 1: Force dynamic rendering on `/annotate/page.tsx`**

To prevent the Next.js App Router from caching the shuffled presentation order, explicitly opt out of static rendering on the page.

```tsx
// At the top of frontend/app/(research)/annotate/page.tsx
export const dynamic = 'force-dynamic';
```

- [ ] **Step 2: Implement hash-based shuffle in `getNextPair`**

Update the logic in `getNextPair` (after fetching pairs and `userAnnotations`) to sort the unannotated pairs pseudo-randomly before picking `nextPair`.

```typescript
// Replace the filtering and finding of nextPair:
  const annotatedPairIds = new Set((userAnnotations || []).map(a => a.pair_id));
  const unannotatedPairs = pairs.filter(p => !annotatedPairIds.has(p.id));
  
  if (unannotatedPairs.length === 0) {
    return { pair: null };
  }

  // Reproducible pseudo-random shuffle per annotator
  const hashedSort = unannotatedPairs.map(p => {
    let hash = 0;
    const str = p.id + user.id;
    for (let i = 0; i < str.length; i++) {
      hash = (Math.imul(31, hash) + str.charCodeAt(i)) | 0;
    }
    return { ...p, sortVal: hash };
  }).sort((a, b) => a.sortVal - b.sortVal);

  const nextPair = hashedSort[0];
```

### Task 3: Harden the Annotation UI, Transitions & Tier 1 Tests

**Files:**
- Modify: `frontend/app/(research)/annotate/AnnotationClient.tsx`
- Create: `frontend/app/(research)/annotate/AnnotationClient.test.tsx`

- [ ] **Step 1: Add Explicit "Same Character" State and `useTransition`**

Modify `AnnotationClient.tsx` to maintain an explicit `isSameCharacter` state and use `useTransition` for form submission to prevent concurrent requests and display pending states.

```tsx
// Add state to AnnotationClient.tsx:
  const [explicitSameCharacter, setExplicitSameCharacter] = useState(false);
  const [isPending, startTransition] = useTransition();

  // Update failureReasons calculation to rely on explicit checks:
  const failureReasons = (Object.keys(taxonomy) as Array<keyof TaxonomyState>).filter(k => taxonomy[k]);
  const sameCharacter = explicitSameCharacter;

  // Add explicit toggle function:
  const toggleSameCharacter = useCallback(() => {
    setExplicitSameCharacter(true);
    setTaxonomy(INITIAL_TAXONOMY);
  }, []);

  const toggle = useCallback((key: keyof TaxonomyState) => {
    setExplicitSameCharacter(false);
    setTaxonomy(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);
  
  // Wrap submission in transition
  const handleSubmit = () => {
    startTransition(async () => {
       await submitAnnotation(...);
       // handle success/refresh
    });
  };
```

- [ ] **Step 2: Add Same Character Checkbox in UI with Accessibility**

In `AnnotationClient.tsx`, render an explicit checkbox for "Same Character" above the taxonomy list. Ensure inputs are disabled while `isPending` is true to prevent race conditions.

```tsx
// Above the taxonomy mapping, add:
          <label className={`flex items-center gap-3 cursor-pointer group p-2 hover:bg-green-50 rounded transition-colors mb-2 border border-gray-200 bg-gray-50 ${isPending ? 'opacity-50 cursor-not-allowed' : ''}`}>
            <input
              type="checkbox"
              checked={explicitSameCharacter}
              onChange={toggleSameCharacter}
              disabled={isPending}
              data-testid="same-character-checkbox"
              aria-label="Mark as same character"
              className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500 disabled:bg-gray-200"
            />
            <span className="flex-1 text-sm font-bold text-green-800">Same Character</span>
            <kbd className="px-2 py-1 bg-white border border-gray-200 rounded text-xs text-gray-500 font-mono">0</kbd>
          </label>

// Also update the handleKeyDown to support '0' and prevent action if pending:
      if (e.key === "0" && !isPending) {
        e.preventDefault();
        toggleSameCharacter();
        return;
      }
```

- [ ] **Step 3: Create Tier 1 UI Test (Vitest)**

Create `frontend/app/(research)/annotate/AnnotationClient.test.tsx`:

```tsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import AnnotationClient from "./AnnotationClient";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() })
}));
vi.mock("./actions", () => ({
  submitAnnotation: vi.fn().mockResolvedValue({ success: true })
}));

describe("AnnotationClient", () => {
  const mockPair = {
    id: "pair-123",
    canonical_signed_url: "https://example.com/canonical",
    scene_signed_url: "https://example.com/scene",
  };

  it("asserts NO metadata leaks in DOM", () => {
    const { container } = render(<AnnotationClient pair={mockPair} />);
    // DOM should strictly only contain signed URLs, no char_id, no metadata
    expect(container.innerHTML).not.toContain("char_id");
    expect(container.innerHTML).not.toContain("is_pilot");
  });

  it("handles form state transitions properly", () => {
    render(<AnnotationClient pair={mockPair} />);
    const sameCharCheckbox = screen.getByTestId("same-character-checkbox");
    const wrongColorCheckbox = screen.getByLabelText(/Wrong Color/i);

    // Clicking Same Character clears others
    fireEvent.click(wrongColorCheckbox);
    expect(wrongColorCheckbox).toBeChecked();
    
    fireEvent.click(sameCharCheckbox);
    expect(sameCharCheckbox).toBeChecked();
    expect(wrongColorCheckbox).not.toBeChecked();
    
    // Clicking taxonomy clears Same Character
    fireEvent.click(wrongColorCheckbox);
    expect(wrongColorCheckbox).toBeChecked();
    expect(sameCharCheckbox).not.toBeChecked();
  });
});
```

### Task 4: Add Tier 2 Server Action Unit Tests

**Files:**
- Create: `frontend/app/(research)/annotate/actions.test.ts`

- [ ] **Step 1: Write `actions.test.ts`**

Create `frontend/app/(research)/annotate/actions.test.ts`. Mock Supabase client to test the invariants.

```typescript
import { describe, it, expect, vi } from "vitest";
import { submitAnnotation } from "./actions";

// Mock Supabase
vi.mock("@/utils/supabase/server", () => {
  return {
    createSupabaseServerClient: vi.fn(() => ({
      auth: { getUser: vi.fn().mockResolvedValue({ data: { user: { id: "test-user" } }, error: null }) },
      from: vi.fn(() => ({
        select: vi.fn().mockReturnThis(),
        eq: vi.fn().mockReturnThis(),
        single: vi.fn().mockResolvedValue({ data: { role: "researcher", is_adjudicator: false }, error: null }),
        upsert: vi.fn().mockResolvedValue({ error: null })
      }))
    }))
  };
});

// Mock Next.js cache
vi.mock("next/cache", () => ({
  revalidatePath: vi.fn()
}));

describe("Server Action Invariants: submitAnnotation", () => {
  it("rejects same_character=true with failure_reasons", async () => {
    const res = await submitAnnotation("pair-1", ["wrong_color"], true, true, true);
    expect(res.error).toMatch(/Invalid state/);
  });

  it("rejects same_character=false with empty failure_reasons", async () => {
    const res = await submitAnnotation("pair-1", [], false, true, true);
    expect(res.error).toMatch(/Invalid state/);
  });

  it("accepts valid payloads", async () => {
    const res = await submitAnnotation("pair-1", [], true, true, true);
    expect(res.error).toBeUndefined();
    // Assuming success is true or the error is simply undefined
  });
});
```

### Task 5: Add Tier 3 DB / RLS Integration Tests (pytest)

**Files:**
- Modify: `backend/tests/test_annotations_rls.py`

- [ ] **Step 1: Add tests for `research_pairs` read restrictions and `is_adjudicator`**

Open `backend/tests/test_annotations_rls.py`. Add the new test blocks at the end. Note: `is_adjudicator` is assumed to be on the `profiles` table.

```python
# Add to the end of backend/tests/test_annotations_rls.py

def test_researcher_cannot_select_research_pairs(conn):
    a = _researcher(conn, "A")
    _as_user(conn, a)
    # RLS should block direct selection of research_pairs by researchers.
    # The server action uses a service key to bypass this.
    rows = conn.execute("SELECT * FROM research_pairs").fetchall()
    assert rows == []  # Expected to see no rows due to RLS

def test_researcher_cannot_update_is_adjudicator(conn):
    a = _researcher(conn, "A")
    _as_user(conn, a)
    # Attempt to elevate privileges
    try:
        conn.execute(
            "UPDATE profiles SET is_adjudicator = true WHERE id = %s", (a,)
        )
    except Exception:
        pass # RLS or lack of permissions may throw
    # Re-read using superuser or bypass
    _reset_role(conn)
    is_adj = conn.execute(
        "SELECT is_adjudicator FROM profiles WHERE id = %s", (a,)
    ).fetchone()[0]
    assert is_adj is False
```
