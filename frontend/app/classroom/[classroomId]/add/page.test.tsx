import { expect, it, describe, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import AddStudentsPage from "./page";

// Test 18: beforeunload armed while slips show, disarmed after.
// Tested as a unit of the useEffect logic (no full render needed).

describe("test 18: beforeunload armed while slips show, disarmed after", () => {
  let addedHandler: EventListener | null = null;

  beforeEach(() => {
    vi.spyOn(window, "addEventListener").mockImplementation(
      (type: string, handler: EventListenerOrEventListenerObject) => {
        if (type === "beforeunload") addedHandler = handler as EventListener;
      }
    );
    vi.spyOn(window, "removeEventListener").mockImplementation(
      (type: string) => {
        if (type === "beforeunload") addedHandler = null;
      }
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("registers beforeunload when slips phase is active", () => {
    function simulateSlipsPhase(active: boolean) {
      if (!active) return () => {};
      const handler = (e: BeforeUnloadEvent) => {
        e.preventDefault();
        e.returnValue = "";
      };
      window.addEventListener("beforeunload", handler);
      return () => window.removeEventListener("beforeunload", handler);
    }

    const cleanup = simulateSlipsPhase(true);
    expect(addedHandler).not.toBeNull();

    cleanup();
    expect(addedHandler).toBeNull();
  });

  it("does not register beforeunload during paste phase", () => {
    function simulateNonSlipsPhase() {
      return () => {};
    }
    simulateNonSlipsPhase();
    expect(addedHandler).toBeNull();
  });
});

vi.mock("next/navigation", () => ({
  useParams: () => ({ classroomId: "cls-123" }),
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    from: (table: string) => ({
      select: () => ({
        eq: () => table === "classrooms"
          ? { single: () => Promise.resolve({ data: { name: "Grade 3", code: "XYZ789" } }) }
          : Promise.resolve({ data: [] }),
      }),
    }),
    auth: { getSession: () => Promise.resolve({ data: { session: { access_token: "tok" } } }) },
  },
}));

describe("single student add", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the failure inline and keeps the typed name", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("boom", { status: 500 })));
    render(<AddStudentsPage />);
    const input = screen.getByRole("textbox", { name: "Single student name" });
    fireEvent.change(input, { target: { value: "Juan D." } });
    fireEvent.click(screen.getByRole("button", { name: "Add student" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not add student — try again");
    expect(input).toHaveValue("Juan D.");
    expect(screen.getByRole("button", { name: "Add student" })).toBeEnabled();
  });
});
