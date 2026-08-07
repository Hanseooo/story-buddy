import { render, screen } from "@testing-library/react";
import { expect, it, vi, beforeEach } from "vitest";
import StudentLayout from "./layout";

const mockSingle = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    from: () => ({
      select: () => ({
        eq: () => ({
          single: mockSingle,
        }),
      }),
    }),
  }),
}));

vi.mock("next/headers", () => ({
  cookies: () => ({
    get: vi.fn(),
  }),
}));

describe("Student Shell Layout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the student shell with greeting when profile is a valid student", async () => {
    mockSingle.mockResolvedValueOnce({
      data: { display_nickname: "Juan", role: "student", classroom_id: "cls_1" },
    });

    const jsx = await StudentLayout({
      children: <div>Child Content</div>,
      params: Promise.resolve({ profileId: "123" }),
    });

    render(jsx);

    expect(screen.getByText(/hi, juan!/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /log out/i })).toBeDefined();
    expect(screen.getByText("Child Content")).toBeDefined();
  });

  it("renders setup error when profile is missing", async () => {
    mockSingle.mockResolvedValueOnce({ data: null });

    const jsx = await StudentLayout({
      children: <div>Child Content</div>,
      params: Promise.resolve({ profileId: "missing" }),
    });

    render(jsx);

    expect(
      screen.getByText(/your class isn't set up anymore. ask your teacher./i)
    ).toBeDefined();
    expect(screen.getByRole("button", { name: /log out/i })).toBeDefined();
  });

  it("renders student notice when user is not a student", async () => {
    mockSingle.mockResolvedValueOnce({
      data: { display_nickname: "Ms. Teacher", role: "teacher", classroom_id: "cls_1" },
    });

    const jsx = await StudentLayout({
      children: <div>Child Content</div>,
      params: Promise.resolve({ profileId: "teacher_1" }),
    });

    render(jsx);

    expect(screen.getByText(/this part is for students/i)).toBeDefined();
    expect(screen.getByRole("link", { name: /go to teacher area/i })).toHaveAttribute(
      "href",
      "/classroom"
    );
  });
});
