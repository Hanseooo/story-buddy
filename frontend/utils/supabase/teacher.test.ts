import { describe, it, expect, vi, beforeEach } from "vitest";

const mockGetUser = vi.fn();
const mockProfileSingle = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    auth: { getUser: mockGetUser },
    from: () => ({
      select: () => ({
        eq: () => ({
          single: mockProfileSingle,
          order: () => Promise.resolve({ data: [] }),
        }),
      }),
    }),
  }),
}));

vi.mock("next/headers", () => ({
  cookies: async () => ({ getAll: () => [], set: vi.fn() }),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn((url: string) => {
    throw new Error(`REDIRECT:${url}`);
  }),
}));

import { getTeacherContext } from "./teacher";

describe("getTeacherContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockProfileSingle.mockResolvedValue({ data: null });
  });

  // Middleware already guards /classroom for anonymous users. If the render
  // disagrees, redirecting to /login sends the browser straight back here
  // (middleware.ts:21) — an infinite 307 loop and a white screen. /auth/signout
  // clears the cookies first, so the loop cannot close.
  it("routes a wedged session through /auth/signout, never /login", async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } });

    await expect(getTeacherContext()).rejects.toThrow(
      "REDIRECT:/auth/signout"
    );
  });

  it("surfaces the Postgres error when the profiles row is unreadable", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "user-1" } } });

    await expect(getTeacherContext()).rejects.toThrow(
      /no profiles row for authenticated user user-1/
    );
  });

  it("routes a researcher to annotation instead of the student tree", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "researcher-1" } } });
    mockProfileSingle.mockResolvedValue({
      data: { id: "researcher-1", role: "researcher", is_adjudicator: false },
    });

    await expect(getTeacherContext()).rejects.toThrow("REDIRECT:/annotate");
  });

  it("routes an adjudicating researcher to adjudication", async () => {
    mockGetUser.mockResolvedValue({ data: { user: { id: "researcher-1" } } });
    mockProfileSingle.mockResolvedValue({
      data: { id: "researcher-1", role: "researcher", is_adjudicator: true },
    });

    await expect(getTeacherContext()).rejects.toThrow("REDIRECT:/adjudicate");
  });
});
