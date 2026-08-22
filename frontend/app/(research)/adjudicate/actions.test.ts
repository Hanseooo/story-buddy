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
      if (table === "annotations") return { insert: mockAnnotationsUpsert };
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

const createQueryMock = (resolvedValue: unknown) => {
  const chain: Record<string, unknown> = {
    eq: vi.fn(() => chain),
    in: vi.fn(() => chain),
    not: vi.fn(() => chain),
    order: vi.fn(() => chain),
    limit: vi.fn(() => chain),
    range: vi.fn(() => chain),
    then: (resolve: (v: unknown) => void) => resolve(resolvedValue)
  };
  return chain;
};

vi.mock("@supabase/supabase-js", () => ({
  createClient: vi.fn(() => ({
    from: vi.fn((table: string) => {
      const chainable = {
        select: vi.fn((cols: string, opts?: { count?: string; head?: boolean }) => {
          const res = mockAdminSelect(table, cols, opts);
          // If the mock returned a value (like from mockReturnValueOnce), use it.
          // Otherwise, build a chainable object.
          if (res) return res;
          const chain = {
            eq: vi.fn(() => chain),
            in: vi.fn(() => chain),
            not: vi.fn(() => chain),
            order: vi.fn(() => chain),
            limit: vi.fn(() => chain),
            range: vi.fn(() => chain),
            then: (resolve: (v: unknown) => void) => resolve({ data: [], error: null })
          };
          return chain;
        }),
        update: vi.fn((vals: Record<string, unknown>) => ({
          eq: vi.fn((col: string, val: string) => mockAdminUpdate(table, vals, col, val)),
        })),
      };
      return chainable;
    }),
    storage: {
      from: vi.fn(() => ({ createSignedUrl: mockAdminCreateSignedUrl })),
    },
  })),
}));

describe("Adjudication Server Actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAdminSelect.mockReset();
    mockAdminUpdate.mockReset();
    mockAdminCreateSignedUrl.mockReset();
    mockAnnotationsUpsert.mockReset();
    process.env.SUPABASE_SERVICE_ROLE_KEY = "test-key";
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test";

    mockGetUser.mockResolvedValue({ data: { user: { id: "adjudicator-1" } }, error: null });
    mockProfilesSelect.mockResolvedValue({ data: { role: "researcher", is_adjudicator: true }, error: null });
    mockAnnotationsUpsert.mockResolvedValue({ error: null });
  });

  describe("submitAdjudication Invariants & Role Isolation", () => {
    it("rejects unauthenticated user", async () => {
      mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: new Error("No session") });
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects non-adjudicator (is_adjudicator=false)", async () => {
      mockProfilesSelect.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: false }, error: null });
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects non-researcher role", async () => {
      mockProfilesSelect.mockResolvedValueOnce({ data: { role: "student", is_adjudicator: true }, error: null });
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects same_character=true when failure_reasons are provided", async () => {
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: ["wrong_colour"], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Invalid state: same_character is true but failure reasons provided");
    });

    it("rejects same_character=false when failure_reasons is empty", async () => {
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: false, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Invalid state: same_character is false but no failure reasons provided");
    });

    it("rejects non-boolean anatomy_intact or text_free", async () => {
      // @ts-expect-error test invalid type
      const res1 = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: undefined, textFree: true });
      expect(res1.error).toBe("Invalid state: anatomy_intact and text_free must be explicitly provided");

      // @ts-expect-error test invalid type
      const res2 = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: null });
      expect(res2.error).toBe("Invalid state: anatomy_intact and text_free must be explicitly provided");
    });

    it("rejects if pair is no longer conflicted", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "complete" } }) })
      });
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Pair is no longer conflicted");
    });

    it("rejects if pair does not have exactly 2 prior annotations", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "annotator-1" }], error: null })
      });
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Invalid pair state: requires exactly 2 prior annotations");
    });

    it("rejects when adjudicator is one of original annotators", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "adjudicator-1" }, { annotator_id: "other" }], error: null })
      });
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Adjudicator cannot resolve their own annotations");
    });

    it("rejects when either prior annotation belongs to an adjudicator", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "other-1" }, { annotator_id: "other-2" }], error: null })
      });
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [{ id: "other-1" }], error: null }));

      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Invalid pair state: prior annotations must be from ordinary annotators");
    });

    it("handles idempotency when adjudicator already submitted but status update failed", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "other-1" }, { annotator_id: "other-2" }, { annotator_id: "adjudicator-1" }], error: null })
      });
      mockAdminUpdate.mockResolvedValue({ error: null });

      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.success).toBe(true);
      expect(mockAdminUpdate).toHaveBeenCalledWith("research_pairs", { status: "adjudicated" }, "id", "pair-1");
    });

    it("does not repair status when an idempotent adjudication has a non-ordinary prior row", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({
          data: [
            { annotator_id: "other-adjudicator" },
            { annotator_id: "ordinary-1" },
            { annotator_id: "adjudicator-1" },
          ],
          error: null,
        })
      });
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [{ id: "other-adjudicator" }], error: null }));

      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Invalid pair state: prior annotations must be from ordinary annotators");
    });

    it("rejects when already adjudicated by another adjudicator", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "other-1" }, { annotator_id: "other-2" }, { annotator_id: "another-adjudicator" }], error: null })
      });
      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Pair already adjudicated by another adjudicator");
    });

    it("successfully submits third annotation and updates pair status to adjudicated", async () => {
      mockAnnotationsUpsert.mockResolvedValue({ error: null });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockReturnValue({ single: vi.fn().mockResolvedValue({ data: { status: "conflicted" } }) })
      });
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "other-1" }, { annotator_id: "other-2" }], error: null })
      });
      mockAdminUpdate.mockResolvedValue({ error: null });

      const res = await submitAdjudication({ pairId: "pair-1", failureReasons: ["wrong_colour"], sameCharacter: false, anatomyIntact: true, textFree: false });
      expect(res.success).toBe(true);
      expect(mockAnnotationsUpsert).toHaveBeenCalledWith(
        {
          pair_id: "pair-1",
          annotator_id: "adjudicator-1",
          same_character: false,
          anatomy_intact: true,
          text_free: false,
          failure_reasons: ["wrong_colour"],
        }
      );
      expect(mockAdminUpdate).toHaveBeenCalledWith("research_pairs", { status: "adjudicated" }, "id", "pair-1");
    });
  });

  describe("getConflictedPair Logic", () => {
    it("returns unauthorized if user is not an adjudicator", async () => {
      mockProfilesSelect.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: false }, error: null });
      const res = await getConflictedPair();
      expect(res.error).toBe("Unauthorized");
    });

    it("returns null if no conflicted pairs exist", async () => {
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] })); // userAnnotations
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] })); // adjudicator profiles
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] })); // research_pairs
      const res = await getConflictedPair();
      expect(res.pair).toBeNull();
    });

    it("skips pair if user is one of the original annotators and returns the valid one", async () => {
      const mockPairs = [{ id: "pair-1", canonical_storage_path: "path/c1.png", scene_storage_path: "path/s1.png" }, { id: "pair-2", canonical_storage_path: "path/c2.png", scene_storage_path: "path/s2.png" }];
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] })); // userAnnotations
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] })); // adjudicator profiles
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: mockPairs })); // research_pairs
      // Pair 1 query: user is annotator
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ annotator_id: "adjudicator-1", same_character: true }, { annotator_id: "other", same_character: false }] })
      });
      // Pair 2 query: valid conflict
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ 
          data: [
            { annotator_id: "other-1", same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true }, 
            { annotator_id: "other-2", same_character: false, failure_reasons: ["wrong_colour"], anatomy_intact: true, text_free: true }
          ] 
        })
      });

      mockAdminCreateSignedUrl
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/canonical-2" } })
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/scene-2" } });

      const res = await getConflictedPair();
      expect(res.pair?.id).toBe("pair-2");
      expect(res.pair?.canonical_signed_url).toBe("https://signed.url/canonical-2");
      expect(res.pair?.scene_signed_url).toBe("https://signed.url/scene-2");
      expect(res.annotationA?.same_character).toBe(true);
      expect(res.annotationB?.same_character).toBe(false);
      // Ensure annotator identities are stripped
      expect((res.annotationA as Record<string, unknown>).annotator_id).toBeUndefined();
      expect((res.annotationB as Record<string, unknown>).annotator_id).toBeUndefined();
    });

    it("skips pair if annotations agree under normalized set equality", async () => {
      const mockPairs = [{ id: "pair-agree" }];
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] })); // userAnnotations
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] })); // adjudicator profiles
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: mockPairs })); // research_pairs
      // Annotations agree despite different order/duplicates of failure reasons
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ 
          data: [
            { annotator_id: "other-1", same_character: false, failure_reasons: ["wrong_style", "wrong_colour"], anatomy_intact: true, text_free: true }, 
            { annotator_id: "other-2", same_character: false, failure_reasons: ["wrong_colour", "wrong_style", "wrong_colour"], anatomy_intact: true, text_free: true }
          ] 
        })
      });

      const res = await getConflictedPair();
      expect(res.pair).toBeNull();
    });

    it("paginates beyond page 0 when all 50 pairs on page 0 are ineligible", async () => {
      // 50 pairs on page 0 that are all already annotated by the adjudicator
      const annotatedPairs = Array.from({ length: 50 }, (_, i) => ({ pair_id: `pair-${i}` }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: annotatedPairs })); // userAnnotations
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] })); // adjudicator profiles

      const page0Pairs = Array.from({ length: 50 }, (_, i) => ({
        id: `pair-${i}`,
        canonical_storage_path: `path/c-${i}.png`,
        scene_storage_path: `path/s-${i}.png`,
      }));
      const page1Pairs = [
        {
          id: "pair-50",
          canonical_storage_path: "path/c-50.png",
          scene_storage_path: "path/s-50.png",
        },
      ];

      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: page0Pairs })); // page 0
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: page1Pairs })); // page 1

      // Conflict query for pair-50
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({
          data: [
            { annotator_id: "other-1", same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true },
            { annotator_id: "other-2", same_character: false, failure_reasons: ["wrong_colour"], anatomy_intact: true, text_free: true },
          ],
        }),
      });

      mockAdminCreateSignedUrl
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/canonical-50" } })
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/scene-50" } });

      const res = await getConflictedPair();
      expect(res.pair?.id).toBe("pair-50");
      expect(res.pair?.canonical_signed_url).toBe("https://signed.url/canonical-50");
      expect(res.pair?.scene_signed_url).toBe("https://signed.url/scene-50");
      expect(res.annotationA?.same_character).toBe(true);
      expect(res.annotationB?.same_character).toBe(false);
    });

    it("returns an error instead of a labelable pair when URL signing fails", async () => {
      const pair = { id: "pair-1", canonical_storage_path: "ref.png", scene_storage_path: "scene.png" };
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [pair] }));
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({
          data: [
            { annotator_id: "other-1", same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true },
            { annotator_id: "other-2", same_character: false, failure_reasons: ["wrong_colour"], anatomy_intact: true, text_free: true },
          ],
        }),
      });
      mockAdminCreateSignedUrl
        .mockResolvedValueOnce({ data: null, error: { message: "signing failed" } })
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/scene" }, error: null });

      const res = await getConflictedPair();
      expect(res).toEqual({ error: "Failed to load adjudication images" });
    });

    it("returns an error instead of queue complete when competing labels cannot be read", async () => {
      const pair = { id: "pair-1", canonical_storage_path: "ref.png", scene_storage_path: "scene.png" };
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [] }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [pair] }));
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: null, error: { message: "database unavailable" } }),
      });

      const res = await getConflictedPair();
      expect(res).toEqual({ error: "Failed to load adjudication queue" });
    });
  });
});
