# Ticket 03: Adjudication Flow & Final Label Authoritative Resolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `/adjudicate` interface and server actions to surface conflicting annotation pairs and allow an adjudicator to submit an authoritative resolution.

**Architecture:** A distinct route (`/adjudicate`) governed by `profiles.is_adjudicator = true` and `role = 'researcher'`. The server action `getConflictedPair` retrieves a pair from `research_pairs` with `status = 'conflicted'`, ensuring the adjudicator is strictly not one of the two original annotators. It strips annotator identity before returning them to a client component. The client component (`AdjudicateClient`) displays the conflicts side-by-side using normalized set equality on `failure_reasons` and renders a taxonomy form identical to `annotate/` for the final decision. Submitting inserts the authoritative third row to `annotations` and updates `research_pairs.status = 'adjudicated'`.

**Tech Stack:** Next.js App Router (React 19), Supabase SSR Client (TypeScript), Tailwind CSS, vitest

## Global Constraints

- A pair is available for adjudication IF AND ONLY IF exactly 2 independent non-adjudicator annotations exist AND they conflict.
- Adjudicator MUST be a distinct researcher (`adjudicator_id != annotator_A_id` and `adjudicator_id != annotator_B_id`). Verified via `profiles.is_adjudicator = true` and `auth_role() = 'researcher'`.
- Blinded Competing Labels: Strip all annotator names, user IDs, emails, and submission timestamps.
- Normalized Set Equality: Taxonomy comparison between Annotator A and B uses normalized set equality (ignoring array ordering).
- Authoritative Ground Truth: Adjudicator submits an authoritative third row in `annotations` (or updates `research_pairs.status = 'adjudicated'`).

---

### Task 1: Adjudication Server Actions and Logic

**Files:**
- Create: `frontend/app/(research)/adjudicate/actions.ts`

**Interfaces:**
- Produces: `getConflictedPair()`, `submitAdjudication(pairId: string, failureReasons: string[], sameCharacter: boolean, anatomyIntact: boolean, textFree: boolean)`
- Produces types: `export type BlindAnnotation = { same_character: boolean, failure_reasons: string[], anatomy_intact: boolean, text_free: boolean };`

- [ ] **Step 1: Write `actions.ts`**
  - Implement `getConflictedPair` using `@supabase/supabase-js` admin client.
  - Query `research_pairs` for `status = 'conflicted'`.
  - For each pair, fetch `annotations` (exactly 2).
  - Verify `annotator_id !== user.id` for both annotations. Also verify they actually conflict using set equality.
  - Strip `annotator_id` and return `pair` + `annotationA` + `annotationB`.
  - Implement `submitAdjudication` with strict validation and idempotency checking (handling the 3-annotation state gracefully).

```typescript
"use server";

import { revalidatePath } from "next/cache";
import { createSupabaseServerClient } from "@/utils/supabase/server";

export type BlindAnnotation = {
  same_character: boolean;
  failure_reasons: string[];
  anatomy_intact: boolean;
  text_free: boolean;
};

export async function submitAdjudication(
  pairId: string, 
  failureReasons: string[], 
  sameCharacter: boolean,
  anatomyIntact: boolean,
  textFree: boolean
) {
  const supabase = await createSupabaseServerClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();

  if (authError || !user) return { error: "Unauthorized" };

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  if (profileError || profile?.role !== "researcher" || !profile?.is_adjudicator) {
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

  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const { createClient } = await import("@supabase/supabase-js");
  const adminClient = createClient(supabaseUrl, serviceKey);

  // Validate that the pair is still conflicted
  const { data: pairInfo } = await adminClient
    .from("research_pairs")
    .select("status")
    .eq("id", pairId)
    .single();

  if (!pairInfo || pairInfo.status !== "conflicted") {
    return { error: "Pair is no longer conflicted" };
  }

  const { data: existingAnnotations } = await adminClient
    .from("annotations")
    .select("annotator_id")
    .eq("pair_id", pairId);

  if (!existingAnnotations || (existingAnnotations.length !== 2 && existingAnnotations.length !== 3)) {
    return { error: "Invalid pair state: requires exactly 2 prior annotations" };
  }

  if (existingAnnotations.length === 3) {
    if (existingAnnotations.some(a => a.annotator_id === user.id)) {
      // Idempotency: Already adjudicated by this user, just retry status update
      await adminClient.from("research_pairs").update({ status: "adjudicated" }).eq("id", pairId);
      return { success: true };
    }
    return { error: "Pair already adjudicated by another adjudicator" };
  }

  if (existingAnnotations.some(a => a.annotator_id === user.id)) {
    return { error: "Adjudicator cannot resolve their own annotations" };
  }

  // Insert the authoritative annotation (first-write-wins idempotency)
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
      onConflict: "pair_id,annotator_id",
      ignoreDuplicates: true,
    });

  if (insertError) {
    console.error("Failed to insert adjudication:", insertError);
    return { error: "Failed to save adjudication" };
  }

  // Update status to adjudicated
  const { error: updateError } = await adminClient
    .from("research_pairs")
    .update({ status: "adjudicated" })
    .eq("id", pairId);

  if (updateError) {
    console.error("Failed to update status:", updateError);
    return { error: "Saved, but failed to update pair status" };
  }

  revalidatePath("/(research)/adjudicate", "page");
  return { success: true };
}

export async function getConflictedPair() {
  const supabase = await createSupabaseServerClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();

  if (authError || !user) return { error: "Unauthorized" };

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  if (profileError || profile?.role !== "researcher" || !profile?.is_adjudicator) {
    return { error: "Unauthorized" };
  }

  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  const { createClient } = await import("@supabase/supabase-js");
  const adminClient = createClient(supabaseUrl, serviceKey);

  const { data: pairs, error: pairsError } = await adminClient
    .from("research_pairs")
    .select("id, canonical_storage_path, scene_storage_path")
    .eq("status", "conflicted")
    .order("created_at", { ascending: true })
    .limit(50);

  if (pairsError || !pairs || pairs.length === 0) {
    return { pair: null };
  }

  let selectedPair = null;
  let annotationA: BlindAnnotation | null = null;
  let annotationB: BlindAnnotation | null = null;

  for (const pair of pairs) {
    const { data: annotations } = await adminClient
      .from("annotations")
      .select("annotator_id, same_character, failure_reasons, anatomy_intact, text_free")
      .eq("pair_id", pair.id);

    if (annotations && annotations.length === 2 && !annotations.some(a => a.annotator_id === user.id)) {
      const [a1, a2] = annotations;
      
      const a1Reasons = Array.from(new Set(a1.failure_reasons || [])).sort();
      const a2Reasons = Array.from(new Set(a2.failure_reasons || [])).sort();

      const agree = a1.same_character === a2.same_character && 
                    a1.anatomy_intact === a2.anatomy_intact &&
                    a1.text_free === a2.text_free &&
                    JSON.stringify(a1Reasons) === JSON.stringify(a2Reasons);

      if (agree) continue; // Not truly conflicted

      selectedPair = pair;
      // Strip identities
      annotationA = {
        same_character: a1.same_character,
        failure_reasons: a1.failure_reasons,
        anatomy_intact: a1.anatomy_intact,
        text_free: a1.text_free,
      };
      annotationB = {
        same_character: a2.same_character,
        failure_reasons: a2.failure_reasons,
        anatomy_intact: a2.anatomy_intact,
        text_free: a2.text_free,
      };
      break;
    }
  }

  if (!selectedPair || !annotationA || !annotationB) {
    return { pair: null };
  }

  const { data: canonicalUrlData } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(selectedPair.canonical_storage_path, 3600);
    
  const { data: sceneUrlData } = await adminClient.storage
    .from("private_assets")
    .createSignedUrl(selectedPair.scene_storage_path, 3600);

  return {
    pair: {
      id: selectedPair.id,
      canonical_signed_url: canonicalUrlData?.signedUrl || "",
      scene_signed_url: sceneUrlData?.signedUrl || ""
    },
    annotationA,
    annotationB
  };
}
```

### Task 2: Unit Tests for Server Actions

**Files:**
- Create: `frontend/app/(research)/adjudicate/actions.test.ts`

- [ ] **Step 1: Write server actions tests**

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { submitAdjudication, getConflictedPair } from "./actions";

const mockGetUser = vi.fn();
const mockProfilesSelect = vi.fn();
const mockAnnotationsUpsert = vi.fn();

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: vi.fn(() => ({
    auth: { getUser: mockGetUser },
    from: vi.fn((table: string) => {
      if (table === "profiles") return { select: vi.fn(() => ({ eq: vi.fn(() => ({ single: mockProfilesSelect })) })) };
      if (table === "annotations") return { upsert: mockAnnotationsUpsert };
      return {};
    }),
  })),
}));

vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

const mockAdminSelect = vi.fn();
const mockAdminUpdate = vi.fn();
const mockAdminCreateSignedUrl = vi.fn();

vi.mock("@supabase/supabase-js", () => ({
  createClient: vi.fn(() => ({
    from: vi.fn((table: string) => ({
      select: vi.fn((cols: string, opts?: { count?: string; head?: boolean }) => {
        return mockAdminSelect(table, cols, opts);
      }),
      update: vi.fn((vals: Record<string, unknown>) => ({
        eq: vi.fn((col: string, val: string) => mockAdminUpdate(table, vals, col, val)),
      })),
    })),
    storage: {
      from: vi.fn(() => ({ createSignedUrl: mockAdminCreateSignedUrl })),
    },
  })),
}));

describe("Adjudication Server Actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.SUPABASE_SERVICE_ROLE_KEY = "test-key";
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test";

    mockGetUser.mockResolvedValue({ data: { user: { id: "adjudicator-1" } }, error: null });
    mockProfilesSelect.mockResolvedValue({ data: { role: "researcher", is_adjudicator: true }, error: null });
  });

  describe("submitAdjudication Invariants", () => {
    it("rejects non-adjudicator", async () => {
      mockProfilesSelect.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: false }, error: null });
      const res = await submitAdjudication("pair-1", [], true, true, true);
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects when adjudicator is one of original annotators", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "adjudicator-1" }, { annotator_id: "other" }], error: null })
      });
      const res = await submitAdjudication("pair-1", [], true, true, true);
      expect(res.error).toBe("Adjudicator cannot resolve their own annotations");
    });

    it("handles idempotency when adjudicator already submitted but status update failed", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "other-1" }, { annotator_id: "other-2" }, { annotator_id: "adjudicator-1" }], error: null })
      });
      mockAdminUpdate.mockResolvedValue({ error: null });

      const res = await submitAdjudication("pair-1", [], true, true, true);
      expect(res.success).toBe(true);
      expect(mockAdminUpdate).toHaveBeenCalledWith("research_pairs", { status: "adjudicated" }, "id", "pair-1");
    });

    it("rejects when already adjudicated by another adjudicator", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "other-1" }, { annotator_id: "other-2" }, { annotator_id: "another-adjudicator" }], error: null })
      });
      const res = await submitAdjudication("pair-1", [], true, true, true);
      expect(res.error).toBe("Pair already adjudicated by another adjudicator");
    });

    it("successfully submits and updates status", async () => {
      mockAnnotationsUpsert.mockResolvedValue({ error: null });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "other-1" }, { annotator_id: "other-2" }], error: null })
      });
      mockAdminUpdate.mockResolvedValue({ error: null });

      const res = await submitAdjudication("pair-1", [], true, true, true);
      expect(res.success).toBe(true);
      expect(mockAdminUpdate).toHaveBeenCalledWith("research_pairs", { status: "adjudicated" }, "id", "pair-1");
    });
  });

  describe("getConflictedPair Logic", () => {
    it("returns null if no conflicted pairs exist", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ order: vi.fn().mockReturnValue({ limit: vi.fn().mockResolvedValue({ data: [] }) }) })
      });
      const res = await getConflictedPair();
      expect(res.pair).toBeNull();
    });

    it("skips pair if user is one of the original annotators and returns the valid one", async () => {
      const mockPairs = [{ id: "pair-1" }, { id: "pair-2" }];
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ order: vi.fn().mockReturnValue({ limit: vi.fn().mockResolvedValue({ data: mockPairs }) }) })
      });
      // Pair 1 query: user is annotator
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "adjudicator-1", same_character: true }, { annotator_id: "other", same_character: false }] })
      });
      // Pair 2 query: valid
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ 
          data: [
            { annotator_id: "other-1", same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true }, 
            { annotator_id: "other-2", same_character: false, failure_reasons: [], anatomy_intact: true, text_free: true }
          ] 
        })
      });

      mockAdminCreateSignedUrl.mockResolvedValue({ data: { signedUrl: "url" } });

      const res = await getConflictedPair();
      expect(res.pair?.id).toBe("pair-2");
      expect(res.annotationA?.same_character).toBe(true);
      expect(res.annotationB?.same_character).toBe(false);
      // Ensure IDs are stripped
      expect((res.annotationA as any).annotator_id).toBeUndefined();
    });
  });
});
```

### Task 3: Client Component & Page Route

**Files:**
- Modify: `frontend/app/(research)/adjudicate/page.tsx`
- Create: `frontend/app/(research)/adjudicate/AdjudicateClient.tsx`

**Interfaces:**
- Consumes: `getConflictedPair` and `submitAdjudication`

- [ ] **Step 1: Replace `page.tsx`**

```tsx
import { getConflictedPair } from "./actions";
import AdjudicateClient from "./AdjudicateClient";

export const dynamic = "force-dynamic";

export default async function AdjudicatePage() {
  const result = await getConflictedPair();
  const pair = result?.pair;
  const annotationA = result?.annotationA;
  const annotationB = result?.annotationB;
  const error = result?.error;

  return (
    <div className="w-full max-w-6xl px-4 flex flex-col items-center pb-20 mt-8">
      <h1 className="text-2xl font-bold mb-6 text-purple-900">Adjudicate Conflicts</h1>
      
      {error || !pair || !annotationA || !annotationB ? (
        <div className="p-8 bg-white rounded-lg shadow text-center w-full">
          <p className="text-gray-500">No conflicted pairs pending adjudication found.</p>
        </div>
      ) : (
        <AdjudicateClient pair={pair} annotationA={annotationA} annotationB={annotationB} />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write `AdjudicateClient.tsx`**

```tsx
"use client";

import { useState, useTransition, useCallback } from "react";
import { useRouter } from "next/navigation";
import { submitAdjudication, type BlindAnnotation } from "./actions";

export type ResearchPair = {
  id: string;
  canonical_signed_url: string;
  scene_signed_url: string;
};

type TaxonomyState = {
  wrong_colour: boolean; wrong_species: boolean; wrong_body_feature: boolean;
  wrong_clothing: boolean; wrong_style: boolean; different_face: boolean; character_absent: boolean;
};
const INITIAL_TAXONOMY: TaxonomyState = { wrong_colour: false, wrong_species: false, wrong_body_feature: false, wrong_clothing: false, wrong_style: false, different_face: false, character_absent: false };

const TAXONOMY_LABELS: Record<keyof TaxonomyState, string> = {
  wrong_colour: "Wrong Color", wrong_species: "Wrong Species", wrong_body_feature: "Wrong Body Feature",
  wrong_clothing: "Wrong Clothing", wrong_style: "Wrong Style", different_face: "Different Face", character_absent: "Character Absent",
};

function hasConflict(a: BlindAnnotation, b: BlindAnnotation, field: keyof BlindAnnotation) {
  if (field === "failure_reasons") {
    // Fixed: Normalize set equality to ignore duplicates
    const aSorted = Array.from(new Set(a.failure_reasons || [])).sort();
    const bSorted = Array.from(new Set(b.failure_reasons || [])).sort();
    return JSON.stringify(aSorted) !== JSON.stringify(bSorted);
  }
  return a[field] !== b[field];
}

export default function AdjudicateClient({ pair, annotationA, annotationB }: { pair: ResearchPair, annotationA: BlindAnnotation, annotationB: BlindAnnotation }) {
  const router = useRouter();
  const [explicitSameCharacter, setExplicitSameCharacter] = useState(false);
  const [taxonomy, setTaxonomy] = useState<TaxonomyState>(INITIAL_TAXONOMY);
  const [brokenAnatomy, setBrokenAnatomy] = useState(false);
  const [textVisible, setTextVisible] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const failureReasons = (Object.keys(taxonomy) as Array<keyof TaxonomyState>).filter(k => taxonomy[k]);
  const sameCharacter = explicitSameCharacter;

  const handleSubmit = useCallback(async () => {
    if (isPending) return;
    setError(null);
    startTransition(async () => {
      const result = await submitAdjudication(pair.id, failureReasons, sameCharacter, !brokenAnatomy, !textVisible);
      if (result.error) { setError(result.error); return; }
      setTaxonomy(INITIAL_TAXONOMY); setExplicitSameCharacter(false); setBrokenAnatomy(false); setTextVisible(false);
      router.refresh();
    });
  }, [isPending, pair.id, failureReasons, sameCharacter, brokenAnatomy, textVisible, router]);

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Visual Conflict Summary */}
      <div className="w-full bg-orange-50 border border-orange-200 p-4 rounded-lg flex flex-col md:flex-row md:items-start gap-4">
        <div className="font-semibold text-orange-900 w-48">Conflicts Detected:</div>
        <div className="flex-1 grid grid-cols-3 gap-4 text-sm">
          <div className="font-medium text-gray-500">Field</div>
          <div className="font-semibold">Annotator 1</div>
          <div className="font-semibold">Annotator 2</div>
          
          {hasConflict(annotationA, annotationB, "same_character") && (
            <><div className="text-red-600 font-medium">Same Character</div><div>{String(annotationA.same_character)}</div><div>{String(annotationB.same_character)}</div></>
          )}
          {hasConflict(annotationA, annotationB, "failure_reasons") && (
            <><div className="text-red-600 font-medium">Failure Reasons</div><div>{Array.from(new Set(annotationA.failure_reasons || [])).join(", ") || "None"}</div><div>{Array.from(new Set(annotationB.failure_reasons || [])).join(", ") || "None"}</div></>
          )}
          {hasConflict(annotationA, annotationB, "anatomy_intact") && (
            <><div className="text-red-600 font-medium">Broken Anatomy</div><div>{String(!annotationA.anatomy_intact)}</div><div>{String(!annotationB.anatomy_intact)}</div></>
          )}
          {hasConflict(annotationA, annotationB, "text_free") && (
            <><div className="text-red-600 font-medium">Text Visible</div><div>{String(!annotationA.text_free)}</div><div>{String(!annotationB.text_free)}</div></>
          )}
        </div>
      </div>

      <div className="w-full flex gap-8">
        {/* Images */}
        <div className="flex-1 flex flex-col gap-4">
           {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={pair.canonical_signed_url} alt="Canonical" className="aspect-square object-contain bg-gray-200 rounded border border-gray-300" />
          <p className="text-center font-medium text-sm text-gray-500">Canonical Reference</p>
        </div>
        <div className="flex-1 flex flex-col gap-4">
           {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={pair.scene_signed_url} alt="Scene" className="aspect-square object-contain bg-gray-200 rounded border border-gray-300" />
          <p className="text-center font-medium text-sm text-gray-500">Generated Scene</p>
        </div>
        
        {/* Resolution Control Panel */}
        <div className="w-80 flex-shrink-0 bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex flex-col">
          <h2 className="font-semibold mb-2 border-b pb-2 text-purple-900">Authoritative Label</h2>
          
          <div className="flex-1 flex flex-col gap-3 mt-4">
            <label className="flex items-center gap-3 cursor-pointer group p-2 hover:bg-green-50 border border-gray-200 rounded bg-gray-50">
              <input type="checkbox" checked={explicitSameCharacter} onChange={() => { setExplicitSameCharacter(p => !p); if(!explicitSameCharacter) setTaxonomy(INITIAL_TAXONOMY); }} disabled={isPending} className="w-5 h-5 rounded text-green-600 focus:ring-green-500" />
              <span className="font-bold text-green-800">Same Character</span>
            </label>

            {(Object.entries(TAXONOMY_LABELS) as [keyof TaxonomyState, string][]).map(([key, label]) => (
              <label key={key} className="flex items-center gap-3 cursor-pointer p-2 hover:bg-gray-50 rounded">
                <input type="checkbox" checked={taxonomy[key]} onChange={() => { setTaxonomy(prev => ({...prev, [key]: !prev[key]})); setExplicitSameCharacter(false); }} disabled={isPending} className="w-5 h-5 rounded text-blue-600 focus:ring-blue-500" />
                <span className="font-medium text-gray-700">{label}</span>
              </label>
            ))}
            
            <div className="border-t my-2 pt-2"></div>
            <label className="flex items-center gap-3 cursor-pointer p-2 hover:bg-gray-50 rounded">
              <input type="checkbox" checked={brokenAnatomy} onChange={() => setBrokenAnatomy(p => !p)} disabled={isPending} className="w-5 h-5 rounded text-purple-600 focus:ring-purple-500" />
              <span className="font-medium text-gray-700">Broken Anatomy</span>
            </label>
            <label className="flex items-center gap-3 cursor-pointer p-2 hover:bg-gray-50 rounded">
              <input type="checkbox" checked={textVisible} onChange={() => setTextVisible(p => !p)} disabled={isPending} className="w-5 h-5 rounded text-purple-600 focus:ring-purple-500" />
              <span className="font-medium text-gray-700">Text Visible</span>
            </label>
          </div>

          <div className="mt-6 pt-4 border-t">
            {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
            <button onClick={handleSubmit} disabled={isPending} className="w-full py-3 bg-purple-600 text-white rounded font-medium hover:bg-purple-700 disabled:opacity-50">
              {isPending ? "Submitting..." : "Submit Final Decision"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```
