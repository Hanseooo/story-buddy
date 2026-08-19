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
          upsert: mockAnnotationsUpsert,
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
      const res = await submitAnnotation("pair-1", ["wrong_colour"], true, true, true);
      expect(res.error).toBe("Invalid state: same_character is true but failure reasons provided");
    });

    it("rejects same_character=false when failure_reasons is empty", async () => {
      const res = await submitAnnotation("pair-1", [], false, true, true);
      expect(res.error).toBe("Invalid state: same_character is false but no failure reasons provided");
    });

    it("rejects undefined or non-boolean anatomy_intact and text_free", async () => {
      // @ts-expect-error test invalid type
      const res1 = await submitAnnotation("pair-1", [], true, undefined, true);
      expect(res1.error).toBe("Invalid state: anatomy_intact and text_free must be explicitly provided");

      // @ts-expect-error test invalid type
      const res2 = await submitAnnotation("pair-1", [], true, true, null);
      expect(res2.error).toBe("Invalid state: anatomy_intact and text_free must be explicitly provided");
    });

    it("accepts valid same_character=true payload with empty failure_reasons", async () => {
      mockAdminSelect.mockReturnValue({
        eq: vi.fn().mockResolvedValue({ count: 1, error: null }),
      });

      const res = await submitAnnotation("pair-1", [], true, true, true);
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
        },
        {
          onConflict: "pair_id,annotator_id",
          ignoreDuplicates: true,
        }
      );
    });

    it("accepts valid same_character=false payload with non-empty failure_reasons", async () => {
      mockAdminSelect.mockReturnValue({
        eq: vi.fn().mockResolvedValue({ count: 1, error: null }),
      });

      const res = await submitAnnotation("pair-1", ["wrong_clothing", "wrong_style"], false, false, true);
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
        },
        {
          onConflict: "pair_id,annotator_id",
          ignoreDuplicates: true,
        }
      );
    });
  });

  describe("Role Isolation & Security Checks", () => {
    it("rejects unauthenticated user in submitAnnotation", async () => {
      mockGetUser.mockResolvedValueOnce({ data: { user: null }, error: new Error("No session") });
      const res = await submitAnnotation("pair-1", [], true, true, true);
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects adjudicator account (is_adjudicator=true) in submitAnnotation", async () => {
      mockProfilesSelect.mockResolvedValueOnce({
        data: { role: "researcher", is_adjudicator: true },
        error: null,
      });
      const res = await submitAnnotation("pair-1", [], true, true, true);
      expect(res.error).toBe("Unauthorized");
    });

    it("rejects non-researcher role in submitAnnotation", async () => {
      mockProfilesSelect.mockResolvedValueOnce({
        data: { role: "student", is_adjudicator: false },
        error: null,
      });
      const res = await submitAnnotation("pair-1", [], true, true, true);
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

      const res = await submitAnnotation("pair-1", [], true, true, true);
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

      const res = await submitAnnotation("pair-1", [], true, true, true);
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

      const res = await submitAnnotation("pair-1", ["wrong_colour"], false, true, true);
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

      mockAdminSelect.mockReturnValueOnce({
        in: vi.fn().mockReturnValue({
          order: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({ data: mockPairs, error: null }),
          }),
        }),
      });

      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [], error: null }),
      });

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
      const mockPairs = [
        { id: "pair-1", canonical_storage_path: "p1", scene_storage_path: "p1" },
      ];

      mockAdminSelect.mockReturnValueOnce({
        in: vi.fn().mockReturnValue({
          order: vi.fn().mockReturnValue({
            limit: vi.fn().mockResolvedValue({ data: mockPairs, error: null }),
          }),
        }),
      });

      mockAdminSelect.mockReturnValueOnce({
        eq: vi.fn().mockResolvedValue({ data: [{ pair_id: "pair-1" }], error: null }),
      });

      const res = await getNextPair();
      expect(res.pair).toBeNull();
    });
  });
});
