import { describe, it, expect } from "vitest";
import { guardRequest } from "./middleware";

const UUID_A = "00000000-0000-0000-0000-000000000001";
const UUID_B = "00000000-0000-0000-0000-000000000002";

// §9 test 1
describe("guardRequest — unauthenticated protected routes", () => {
  it("unauthenticated /s/<uuid> → /join?next=...", () => {
    expect(guardRequest(`/s/${UUID_A}`, null)).toBe(`/join?next=/s/${UUID_A}`);
  });

  it("unauthenticated /s/<uuid>/write → /join?next=...", () => {
    expect(guardRequest(`/s/${UUID_A}/write`, null)).toBe(
      `/join?next=/s/${UUID_A}/write`
    );
  });

  it("unauthenticated /dashboard → /login?next=/dashboard", () => {
    expect(guardRequest("/dashboard", null)).toBe("/login?next=/dashboard");
  });

  it("unauthenticated /dashboard/settings → /login?next=...", () => {
    expect(guardRequest("/dashboard/settings", null)).toBe(
      "/login?next=/dashboard/settings"
    );
  });
});

// §9 test 2
describe("guardRequest — profile mismatch", () => {
  it("authenticated, profileId ≠ sub → /s/<sub>", () => {
    expect(guardRequest(`/s/${UUID_A}`, UUID_B)).toBe(`/s/${UUID_B}`);
  });

  it("authenticated, profileId ≠ sub on nested route → /s/<sub>", () => {
    expect(guardRequest(`/s/${UUID_A}/write`, UUID_B)).toBe(`/s/${UUID_B}`);
  });
});

// §9 test 3
describe("guardRequest — signed-in on a door", () => {
  it("authenticated on /join → /s/<sub>", () => {
    expect(guardRequest("/join", UUID_A)).toBe(`/s/${UUID_A}`);
  });

  it("authenticated on /join/[code] → /s/<sub>", () => {
    expect(guardRequest("/join/abc123", UUID_A)).toBe(`/s/${UUID_A}`);
  });

  it("authenticated on /login → /dashboard", () => {
    expect(guardRequest("/login", UUID_A)).toBe("/dashboard");
  });

  it("authenticated on /signup → /dashboard", () => {
    expect(guardRequest("/signup", UUID_A)).toBe("/dashboard");
  });
});

// §9 test 4 — pass-through cases
describe("guardRequest — no redirect", () => {
  it("authenticated on own /s/<sub> → null", () => {
    expect(guardRequest(`/s/${UUID_A}`, UUID_A)).toBeNull();
  });

  it("authenticated on own /s/<sub>/write → null", () => {
    expect(guardRequest(`/s/${UUID_A}/write`, UUID_A)).toBeNull();
  });

  it("unauthenticated / → null (public)", () => {
    expect(guardRequest("/", null)).toBeNull();
  });

  it("unauthenticated /login → null (public)", () => {
    expect(guardRequest("/login", null)).toBeNull();
  });

  it("unauthenticated /join → null (public)", () => {
    expect(guardRequest("/join", null)).toBeNull();
  });
});
