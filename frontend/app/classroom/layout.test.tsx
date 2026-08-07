import { render, screen } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import ClassroomLayout from "./layout";
import TeacherShell from "@/components/TeacherShell";

const mockSelect = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    from: (table: string) => {
      if (table === "profiles") {
        return { select: mockSelect };
      }
      // classrooms query — return empty list
      return {
        select: () => ({
          eq: () => ({ order: () => Promise.resolve({ data: [] }) }),
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
  cookies: () => ({ get: vi.fn() }),
}));

vi.mock("next/navigation", () => ({
  redirect: vi.fn((url: string) => {
    throw new Error(`REDIRECT:${url}`);
  }),
  usePathname: vi.fn().mockReturnValue("/classroom"),
}));

vi.mock("next/link", () => ({
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

describe("ClassroomLayout / TeacherShell", () => {
  beforeEach(() => vi.clearAllMocks());

  it("test 20a: redirects a student to /s/{userId}", async () => {
    mockSelect.mockReturnValue({
      eq: () => ({
        single: () =>
          Promise.resolve({
            data: { id: "student-1", role: "student", display_name: null },
          }),
      }),
    });

    let thrown = "";
    try {
      await TeacherShell({ children: <div /> });
    } catch (e: unknown) {
      thrown = (e as Error).message;
    }
    expect(thrown).toMatch(/REDIRECT:\/s\/student-1/);
  });

  it("test 20b: redirects a profile-less user to /login", async () => {
    mockSelect.mockReturnValue({
      eq: () => ({ single: () => Promise.resolve({ data: null }) }),
    });

    let thrown = "";
    try {
      await TeacherShell({ children: <div /> });
    } catch (e: unknown) {
      thrown = (e as Error).message;
    }
    expect(thrown).toMatch(/REDIRECT:\/login/);
  });

  it("test 21: renders shell for a valid teacher", async () => {
    mockSelect.mockReturnValue({
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
    });

    // Call TeacherShell directly so its async resolution is awaited before render
    const jsx = await TeacherShell({ children: <div>Content</div> });
    render(jsx);
    expect(screen.getByText("Content")).toBeDefined();
  });
});
