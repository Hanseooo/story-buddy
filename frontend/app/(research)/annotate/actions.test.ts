import { describe, it, expect, vi, beforeEach } from "vitest";
import { submitAnnotation, getNextPair } from "./actions";

// Mock Supabase SSR server client
const mockGetUser = vi.fn();
const mockProfilesSelect = vi.fn();
const mockAnnotationsUpsert = vi.fn();

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: vi.fn(() => ({
    auth: {
      getUser: mockGetUser,
    },
    from: vi.fn((table: string) => {
      if (table === "profiles") {
        return {
          select: vi.fn(() => ({
            eq: vi.fn(() => ({
              single: mockProfilesSelect,
            })),
          })),
        };
      }
      if (table === "annotations") {
        return {
          insert: mockAnnotationsUpsert,
        };
      }
      return {};
    }),
  })),
}));

// Mock Next.js cache
vi.mock("next/cache", () => ({
  revalidatePath: vi.fn(),
}));

// Mock @supabase/supabase-js for service role admin client
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
      from: vi.fn(() => ({
        createSignedUrl: mockAdminCreateSignedUrl,
      })),
    },
  })),
}));

describe("Tier 2: Server Action Unit Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.SUPABASE_SERVICE_ROLE_KEY = "test-service-key";
    process.env.NEXT_PUBLIC_SUPABASE_URL = "https://test.supabase.co";

    // Default authenticated researcher
    mockGetUser.mockResolvedValue({
      data: { user: { id: "user-researcher-1" } },
      error: null,
    });
    mockProfilesSelect.mockResolvedValue({
      data: { role: "researcher", is_adjudicator: false },
      error: null,
    });
    mockAnnotationsUpsert.mockResolvedValue({ error: null });
  });

  describe("submitAnnotation Invariant Validation", () => {
    it("rejects same_character=true when failure_reasons are provided", async () => {
      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: ["wrong_colour"], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Invalid state: same_character is true but failure reasons provided");
    });

    it("rejects same_character=false when failure_reasons is empty", async () => {
      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: false, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Invalid state: same_character is false but no failure reasons provided");
    });

    it("rejects undefined or non-boolean anatomy_intact and text_free", async () => {
      // @ts-expect-error test invalid type
      const res1 = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: undefined, textFree: true });
      expect(res1.error).toBe("Invalid state: anatomy_intact and text_free must be explicitly provided");

      // @ts-expect-error test invalid type
      const res2 = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: null });
      expect(res2.error).toBe("Invalid state: anatomy_intact and text_free must be explicitly provided");
    });

    it("accepts valid same_character=true payload with empty failure_reasons", async () => {
      mockAdminSelect.mockReturnValue({
        eq: vi.fn().mockResolvedValue({ count: 1, error: null }),
      });

      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBeUndefined();
      expect(res.success).toBe(true);
      expect(mockAnnotationsUpsert).toHaveBeenCalledWith(
        {
          pair_id: "pair-1",
          annotator_id: "user-researcher-1",
          same_character: true,
          anatomy_intact: true,
          text_free: true,
          failure_reasons: [],
        }
      );
    });

    it("accepts valid same_character=false payload with non-empty failure_reasons", async () => {
      mockAdminSelect.mockReturnValue({
        eq: vi.fn().mockResolvedValue({ count: 1, error: null }),
      });

      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: ["wrong_clothing", "wrong_style"], sameCharacter: false, anatomyIntact: false, textFree: true });
      expect(res.error).toBeUndefined();
      expect(res.success).toBe(true);
      expect(mockAnnotationsUpsert).toHaveBeenCalledWith(
        {
          pair_id: "pair-1",
          annotator_id: "user-researcher-1",
          same_character: false,
          anatomy_intact: false,
          text_free: true,
          failure_reasons: ["wrong_clothing", "wrong_style"],
        }
      );
    });
  });

  describe("Role Isolation & Security Checks", () => {
    it("rejects unauthenticated user in submitAnnotation", async () => {
      mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: new Error("No session") });
      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects adjudicator account (is_adjudicator=true) in submitAnnotation", async () => {
      mockProfilesSelect.mockResolvedValueOnce({
        data: { role: "researcher", is_adjudicator: true },
        error: null,
      });
      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects non-researcher role in submitAnnotation", async () => {
      mockProfilesSelect.mockResolvedValueOnce({
        data: { role: "student", is_adjudicator: false },
        error: null,
      });
      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects adjudicator account in getNextPair", async () => {
      mockProfilesSelect.mockResolvedValueOnce({
        data: { role: "researcher", is_adjudicator: true },
        error: null,
      });
      const res = await getNextPair();
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects unauthenticated caller in getNextPair", async () => {
      mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: null });
      const res = await getNextPair();
      expect(res.error).toBe("Unauthorized");
    });
  });

  describe("Queue Status Progression in submitAnnotation", () => {
    it("transitions status to partially_annotated on first annotation", async () => {
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValueOnce({ count: 1, error: null }),
      });

      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.success).toBe(true);
      expect(mockAdminUpdate).toHaveBeenCalledWith(
        "research_pairs",
        { status: "partially_annotated" },
        "id",
        "pair-1"
      );
    });

    it("transitions status to complete on second agreeing annotation", async () => {
      // First select is for count
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValueOnce({ count: 2, error: null }),
      });
      // Second select is fetching both annotations
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValueOnce({
          data: [
            { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true },
            { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true },
          ],
          error: null,
        }),
      });

      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: [], sameCharacter: true, anatomyIntact: true, textFree: true });
      expect(res.success).toBe(true);
      expect(mockAdminUpdate).toHaveBeenCalledWith(
        "research_pairs",
        { status: "complete" },
        "id",
        "pair-1"
      );
    });

    it("transitions status to conflicted on second disagreeing annotation", async () => {
      // First select is for count
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValueOnce({ count: 2, error: null }),
      });
      // Second select is fetching both annotations
      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValueOnce({
          data: [
            { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true },
            { same_character: false, failure_reasons: ["wrong_colour"], anatomy_intact: true, text_free: true },
          ],
          error: null,
        }),
      });

      const res = await submitAnnotation({ pairId: "pair-1", failureReasons: ["wrong_colour"], sameCharacter: false, anatomyIntact: true, textFree: true });
      expect(res.success).toBe(true);
      expect(mockAdminUpdate).toHaveBeenCalledWith(
        "research_pairs",
        { status: "conflicted" },
        "id",
        "pair-1"
      );
    });
  });

  describe("getNextPair Strict Blinding & Randomized Delivery", () => {
    it("returns strictly allowlisted payload with signed URLs and NO database metadata", async () => {
      const mockPairs = [
        {
          id: "pair-1",
          canonical_storage_path: "storage/canonical-1.png",
          scene_storage_path: "storage/scene-1.png",
          char_id: "char-secret-uuid",
          split: "train",
          is_pilot: true,
          is_constructed_negative: false,
        },
      ];

      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [], error: null }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: mockPairs, error: null }));

      mockAdminCreateSignedUrl
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/canonical-1" }, error: null })
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/scene-1" }, error: null });

      const res = await getNextPair();
      expect(res.error).toBeUndefined();
      expect(res.pair).toBeDefined();

      // Check strictly allowed fields
      expect(res.pair).toEqual({
        id: "pair-1",
        canonical_signed_url: "https://signed.url/canonical-1",
        scene_signed_url: "https://signed.url/scene-1",
      });

      // Assert that blind metadata is NOT leaked in the return object
      expect((res.pair as Record<string, unknown>).char_id).toBeUndefined();
      expect((res.pair as Record<string, unknown>).split).toBeUndefined();
      expect((res.pair as Record<string, unknown>).is_pilot).toBeUndefined();
      expect((res.pair as Record<string, unknown>).is_constructed_negative).toBeUndefined();
      expect((res.pair as Record<string, unknown>).canonical_storage_path).toBeUndefined();
      expect((res.pair as Record<string, unknown>).scene_storage_path).toBeUndefined();
    });

    it("returns null pair when all queue items are annotated", async () => {
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [{ pair_id: "pair-1" }], error: null }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: [], error: null }));

      const res = await getNextPair();
      expect(res.pair).toBeNull();
    });

    it("paginates beyond page 0 when user has annotated the first 50 pairs", async () => {
      const annotatedPairs = Array.from({ length: 50 }, (_, i) => ({ pair_id: `pair-${i}` }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: annotatedPairs, error: null }));

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

      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: page0Pairs, error: null }));
      mockAdminSelect.mockReturnValueOnce(createQueryMock({ data: page1Pairs, error: null }));

      mockAdminCreateSignedUrl
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/canonical-50" }, error: null })
        .mockResolvedValueOnce({ data: { signedUrl: "https://signed.url/scene-50" }, error: null });

      const res = await getNextPair();
      expect(res.error).toBeUndefined();
      expect(res.pair?.id).toBe("pair-50");
      expect(res.pair?.canonical_signed_url).toBe("https://signed.url/canonical-50");
      expect(res.pair?.scene_signed_url).toBe("https://signed.url/scene-50");
    });
  });
});
