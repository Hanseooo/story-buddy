import { beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

const mockSignOut = vi.hoisted(() => vi.fn());

vi.mock("@supabase/ssr", () => ({
  createServerClient: () => ({
    auth: { signOut: mockSignOut },
  }),
}));

import { GET, POST } from "./route";

function makeRequest(method: "GET" | "POST") {
  return new NextRequest("http://localhost:3000/auth/signout", {
    method,
    headers: {
      cookie: "sb-project-auth-token=access; sb-project-auth-token.0=chunk; keep=1",
    },
  });
}

describe("/auth/signout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSignOut.mockResolvedValue({ error: null });
  });

  it("redirects to login and clears every Supabase session cookie", async () => {
    const response = await POST(makeRequest("POST"));

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
    expect(mockSignOut).toHaveBeenCalledTimes(1);

    const clearedCookies = response.cookies
      .getAll()
      .filter(({ name }) => name.startsWith("sb-"));
    expect(clearedCookies.map(({ name }) => name)).toEqual([
      "sb-project-auth-token",
      "sb-project-auth-token.0",
    ]);
    expect(clearedCookies.every(({ value }) => value === "")).toBe(true);
  });

  it("still clears the local session when Supabase signout fails", async () => {
    mockSignOut.mockRejectedValueOnce(new Error("stale session"));

    const response = await GET(makeRequest("GET"));

    expect(response.status).toBe(303);
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
    expect(response.cookies.getAll().some(({ name }) => name === "sb-project-auth-token")).toBe(true);
  });
});
