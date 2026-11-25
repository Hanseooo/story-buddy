import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { expect, it, describe, vi, beforeEach, afterEach } from "vitest";
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

// Each test can swap the profiles query result to simulate a failed read.
const db = vi.hoisted(() => ({
  profiles: null as null | { data: unknown; error: unknown },
}));

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
              order: () => Promise.resolve(db.profiles ?? { data: mockProfiles, error: null }),
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
    db.profiles = null;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
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

  it("shows an error with Retry when the roster fails to load, and Retry loads it", async () => {
    db.profiles = { data: null, error: { message: "network down" } };
    render(<RosterPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load the roster.");
    db.profiles = null;
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Super Hero")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("closes the remove dialog before showing the failure toast", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("boom", { status: 500 })));
    render(<RosterPage />);
    fireEvent.click((await screen.findAllByRole("button", { name: /student actions/i }))[0]);
    fireEvent.click(screen.getByRole("menuitem", { name: /remove/i }));
    const confirm = screen.getByRole("heading", { name: "Remove Super Hero?" }).closest("dialog")!;
    expect(confirm).toHaveAttribute("open");
    fireEvent.click(within(confirm).getByRole("button", { name: "Remove" }));
    expect(await screen.findByText("Could not remove — try again")).toBeInTheDocument();
    expect(confirm).not.toHaveAttribute("open");
  });

  it("shows the reset slip in a named modal dialog; Escape closes it and focus returns to the row button", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json(
      { profile_id: "s1", display_nickname: "Super Hero", nickname: "hero", password: "maple-otter" },
    )));
    render(<RosterPage />);
    const trigger = (await screen.findAllByRole("button", { name: /student actions/i }))[0];
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("menuitem", { name: /reset word/i }));
    const slip = await screen.findByRole("dialog", { name: "Word reset" });
    expect(slip).toHaveAttribute("open");
    expect(within(slip).getByText("maple-otter")).toBeInTheDocument();
    expect(slip).toHaveClass("max-h-[90dvh]", "overflow-y-auto");

    // Escape on a modal <dialog> fires "cancel"; jsdom has no native Escape handling.
    fireEvent(slip, new Event("cancel", { bubbles: true }));
    await waitFor(() => expect(slip).not.toHaveAttribute("open"));
    expect(screen.queryByText("maple-otter")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
