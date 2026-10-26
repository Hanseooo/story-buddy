import { beforeEach, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";
import { middleware } from "@/middleware";

const { profile } = vi.hoisted(() => ({ profile: { role: "student", password_reset_version: 0, password_completed_version: 0 } }));

vi.mock("@supabase/ssr", () => ({
  createServerClient: (_url: string, _key: string, options: {
    cookies: { setAll: (cookies: { name: string; value: string; options: { httpOnly: boolean; path: string } }[]) => void };
  }) => ({
    auth: { getUser: async () => {
      options.cookies.setAll([{ name: "sb-test-auth-token", value: "refreshed-fixture", options: { httpOnly: true, path: "/" } }]);
      return { data: { user: { id: "student-1" } }, error: null };
    } },
    from: () => ({ select: () => ({ eq: () => ({ single: async () => ({ data: profile, error: null }) }) }) }),
  }),
}));

beforeEach(() => { profile.password_reset_version = 0; });

it("returns refreshed cookies on a completed student's product response", async () => {
  const response = await middleware(new NextRequest("https://storybuddy.example/s/student-1"));
  expect(response.status).toBe(200);
  expect(response.cookies.get("sb-test-auth-token")).toMatchObject({ value: "refreshed-fixture", httpOnly: true, path: "/" });
});

it("keeps refreshed cookies when redirecting a required student", async () => {
  profile.password_reset_version = 1;
  const response = await middleware(new NextRequest("https://storybuddy.example/s/student-1/gallery"));
  expect(response.headers.get("location")).toBe("https://storybuddy.example/s/student-1/change-password");
  expect(response.cookies.get("sb-test-auth-token")).toMatchObject({ value: "refreshed-fixture", httpOnly: true, path: "/" });
});
