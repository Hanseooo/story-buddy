import { render, screen, fireEvent } from "@testing-library/react";
import { expect, it, describe, vi, beforeEach } from "vitest";
import RosterPage from "./page";

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => ({ classroomId: "cls-123" }),
  useRouter: () => ({ push: mockPush, replace: mockReplace }),
}));

const mockProfiles = [
  { id: "s1", nickname: "hero", display_nickname: "Super Hero", removed_at: null, avatar_id: "av1" },
  { id: "s2", nickname: "star", display_nickname: "Rising Star", removed_at: null, avatar_id: "av2" },
];

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    from: (table: string) => {
      if (table === "classrooms") {
        return {
          select: () => ({
            eq: () => ({
              single: () => Promise.resolve({ data: { name: "Grade 3", code: "XYZ789" } }),
            }),
          }),
        };
      }
      if (table === "profiles") {
        return {
          select: () => ({
            eq: () => ({
              order: () => Promise.resolve({ data: mockProfiles }),
            }),
          }),
        };
      }
      return {};
    },
    auth: {
      getSession: () => Promise.resolve({ data: { session: { access_token: "tok" } } }),
    },
  },
}));

describe("RosterPage & RowMenu Stacking & Interaction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders active student list correctly", async () => {
    render(<RosterPage />);
    expect(await screen.findByText("Super Hero")).toBeInTheDocument();
    expect(screen.getByText("Rising Star")).toBeInTheDocument();
  });

  it("opens RowMenu and displays Reset word and Remove options", async () => {
    render(<RosterPage />);
    expect(await screen.findByText("Super Hero")).toBeInTheDocument();

    const actionBtns = screen.getAllByRole("button", { name: /student actions/i });
    expect(actionBtns.length).toBe(2);

    // Menu should initially be closed
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    // Click the first student action button
    fireEvent.click(actionBtns[0]);

    // Menu should open and show action items
    const menu = await screen.findByRole("menu");
    expect(menu).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /reset word/i })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /remove/i })).toBeInTheDocument();

    // Verify row container has z-index elevation class/style when menu is open
    const firstStudentRow = actionBtns[0].closest("div[class*='bg-surface']");
    expect(firstStudentRow).toHaveClass("z-20");
  });
});
