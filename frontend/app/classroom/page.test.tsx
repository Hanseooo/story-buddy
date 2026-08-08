import { render, screen } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import ClassroomPickerPage from "./page";

let classroomRows: { id: string; name: string; code: string }[] = [];

vi.mock("@supabase/ssr", () => ({
  // ClassroomPicker uses the browser client only for the create-classroom POST
  createBrowserClient: () => ({
    auth: { getSession: vi.fn().mockResolvedValue({ data: { session: null } }) },
  }),
  createServerClient: () => ({
    from: (table: string) => {
      if (table === "profiles") {
        return {
          select: () => ({
            eq: () => ({
              single: () =>
                Promise.resolve({
                  data: {
                    id: "teacher-abc",
                    role: "teacher",
                    display_name: "Ms. Garcia",
                  },
                }),
            }),
          }),
        };
      }
      return {
        select: () => ({
          eq: () => ({
            order: () => Promise.resolve({ data: classroomRows }),
          }),
        }),
      };
    },
    auth: {
      getUser: vi.fn().mockResolvedValue({
        data: { user: { id: "teacher-abc" } },
      }),
    },
  }),
}));

vi.mock("next/headers", () => ({
  cookies: () => ({ getAll: () => [], set: vi.fn() }),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn((url: string) => {
    throw new Error(`REDIRECT:${url}`);
  }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

async function renderPage() {
  render(await ClassroomPickerPage());
}

describe("/classroom picker", () => {
  beforeEach(() => vi.clearAllMocks());

  it("redirects server-side when the teacher has exactly one classroom", async () => {
    classroomRows = [{ id: "c-1", name: "Grade 3 – Alon", code: "ABC123" }];

    let thrown = "";
    try {
      await ClassroomPickerPage();
    } catch (e: unknown) {
      thrown = (e as Error).message;
    }
    expect(thrown).toBe("REDIRECT:/classroom/c-1");
  });

  it("renders the empty state when the teacher has no classrooms", async () => {
    classroomRows = [];
    await renderPage();
    expect(screen.getByText("Welcome to your desk!")).toBeDefined();
  });

  it("renders every classroom when the teacher has more than one", async () => {
    classroomRows = [
      { id: "c-1", name: "Grade 3 – Alon", code: "ABC123" },
      { id: "c-2", name: "Grade 4 – Bagyo", code: "XYZ789" },
    ];
    await renderPage();
    expect(screen.getByText("Grade 3 – Alon")).toBeDefined();
    expect(screen.getByText("Grade 4 – Bagyo")).toBeDefined();
  });
});
