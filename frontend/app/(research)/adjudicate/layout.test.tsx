import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AdjudicateLayout from "./layout";

const mockGetUser = vi.fn();
const mockProfilesSelect = vi.fn();

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: vi.fn(() => ({
    auth: { getUser: mockGetUser },
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
      return {};
    }),
  })),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn((url: string) => {
    throw new Error(`REDIRECT:${url}`);
  }),
}));

describe("AdjudicateLayout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("redirects to /login if user is not authenticated", async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null } });

    await expect(
      AdjudicateLayout({ children: <div>Child Content</div> })
    ).rejects.toThrow("REDIRECT:/login");
  });

  it("redirects to / if user is a non-researcher", async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: "user-1" } } });
    mockProfilesSelect.mockResolvedValueOnce({
      data: { role: "student", is_adjudicator: true },
    });

    await expect(
      AdjudicateLayout({ children: <div>Child Content</div> })
    ).rejects.toThrow("REDIRECT:/");
  });

  it("redirects to / if researcher is not an adjudicator (is_adjudicator=false)", async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: "user-1" } } });
    mockProfilesSelect.mockResolvedValueOnce({
      data: { role: "researcher", is_adjudicator: false },
    });

    await expect(
      AdjudicateLayout({ children: <div>Child Content</div> })
    ).rejects.toThrow("REDIRECT:/");
  });

  it("renders children for authorized adjudicator (researcher with is_adjudicator=true)", async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: "user-1" } } });
    mockProfilesSelect.mockResolvedValueOnce({
      data: { role: "researcher", is_adjudicator: true },
    });

    const jsx = await AdjudicateLayout({
      children: <div>Child Content</div>,
    });
    render(jsx);

    expect(screen.getByText("Child Content")).toBeInTheDocument();
  });
});
