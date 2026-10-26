import { describe, it, expect } from "vitest";
import { guardRequest, guardOnboarding } from "./middleware";

const UUID_A = "00000000-0000-0000-0000-000000000001";
const UUID_B = "00000000-0000-0000-0000-000000000002";

describe("current profile onboarding gate", () => {
  it("blocks product paths but leaves the caller's password route reachable", () => {
    const profile = { role: "student", password_reset_version: 2, password_completed_version: 1 };
    for (const path of [`/s/${UUID_A}`, `/s/${UUID_A}/gallery`, "/classroom", "/settings", "/join"])
      expect(guardOnboarding(path, UUID_A, profile)).toBe(`/s/${UUID_A}/change-password`);
    expect(guardOnboarding(`/s/${UUID_A}/change-password`, UUID_A, profile)).toBeNull();
  });
  it("fails closed on unknown state and preserves the legacy exemption", () => {
    expect(guardOnboarding(`/s/${UUID_A}`, UUID_A, null)).toBe(`/s/${UUID_A}/change-password`);
    expect(guardOnboarding(`/s/${UUID_A}`, UUID_A,
      { role: "student", password_reset_version: 0, password_completed_version: 0 })).toBeNull();
    expect(guardOnboarding("/settings", UUID_A, { role: "teacher" })).toBeNull();
  });
});

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

  it("unauthenticated /classroom → /login?next=/classroom", () => {
    expect(guardRequest("/classroom", null)).toBe("/login?next=/classroom");
  });

  it("unauthenticated /settings → /login?next=/settings", () => {
    expect(guardRequest("/settings", null)).toBe("/login?next=/settings");
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

  it("authenticated on / → /classroom", () => {
    expect(guardRequest("/", UUID_A)).toBe("/classroom");
  });

  it("authenticated on /login → /classroom", () => {
    expect(guardRequest("/login", UUID_A)).toBe("/classroom");
  });

  it("authenticated on /signup → /classroom", () => {
    expect(guardRequest("/signup", UUID_A)).toBe("/classroom");
  });
});

// §9 test 21 — /classroom + /settings guards
describe("guardRequest — teacher routes", () => {
  it("redirects logged-out user from /classroom to /login", () => {
    expect(guardRequest("/classroom", null)).toBe("/login?next=/classroom");
  });

  it("redirects logged-out user from /settings to /login", () => {
    expect(guardRequest("/settings", null)).toBe("/login?next=/settings");
  });

  it("redirects logged-in user away from /login to /classroom", () => {
    expect(guardRequest("/login", UUID_A)).toBe("/classroom");
  });

  it("does not redirect logged-in user on /classroom", () => {
    expect(guardRequest("/classroom", UUID_A)).toBeNull();
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

describe("guardRequest — research run browser", () => {
  it("unauthenticated run detail → /login?next=...", () => {
    expect(guardRequest(`/research/metrics/${UUID_A}`, null)).toBe(
      `/login?next=/research/metrics/${UUID_A}`
    );
  });

  it("the run list stays public", () => {
    expect(guardRequest("/research/metrics", null)).toBeNull();
  });

  it("a signed-in run detail request passes", () => {
    expect(guardRequest(`/research/metrics/${UUID_A}`, UUID_B)).toBeNull();
  });
});
