import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AnnotateLayout from "./layout";

const mockGetUser = vi.fn();
const mockSingle = vi.fn();

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: vi.fn(() => ({
    auth: { getUser: mockGetUser },
    from: vi.fn(() => ({ select: vi.fn(() => ({ eq: vi.fn(() => ({ single: mockSingle })) })) })),
  })),
}));

vi.mock("next/navigation", () => ({ usePathname: () => "/annotate" }));

describe("AnnotateLayout", () => {
  beforeEach(() => vi.clearAllMocks());

  it("refuses the adjudicator", async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: "r-2" } } });
    mockSingle.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: true } });

    await expect(AnnotateLayout({ children: <div>Queue</div> })).rejects.toThrow("Unauthorized");
  });

  it("renders the research header above an annotator's queue", async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: { id: "r-1" } } });
    mockSingle.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: false, display_name: "Ana" } });

    render(await AnnotateLayout({ children: <div>Queue</div> }));

    expect(screen.getByRole("navigation", { name: "Research" })).toBeInTheDocument();
    expect(screen.getByText("Queue")).toBeInTheDocument();
  });
});
