import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import fixture from "./__fixtures__/run.json";
import { loadRun } from "./loadRun";

const JOB = "3f9a1c2e-0000-4000-8000-000000000001";
const mockSession = vi.hoisted(() => vi.fn());

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: async () => ({ auth: { getSession: mockSession } }),
}));

const answer = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });

describe("loadRun", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://api.test");
    mockSession.mockResolvedValue({ data: { session: { access_token: "tok" } } });
  });
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("signed out never calls the backend", async () => {
    mockSession.mockResolvedValue({ data: { session: null } });
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    expect(await loadRun(JOB)).toEqual({ kind: "signed_out" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("sends the bearer token, uncached, and returns the run", async () => {
    const fetchMock = vi.fn().mockResolvedValue(answer(200, fixture));
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadRun(JOB);

    expect(fetchMock).toHaveBeenCalledWith(`http://api.test/research/runs/${JOB}`, {
      headers: { Authorization: "Bearer tok" },
      cache: "no-store",
    });
    expect(result.kind === "ok" && result.run.job.title).toBe("The Red Kite");
  });

  it.each([
    [401, { detail: "Not authenticated" }, { kind: "signed_out" }],
    [403, { detail: "not_approved" }, { kind: "forbidden", reason: "not_approved" }],
    [403, { detail: "researchers_only" }, { kind: "forbidden", reason: "researchers_only" }],
    [404, { detail: "not_found" }, { kind: "not_found" }],
    [422, { detail: [] }, { kind: "not_found" }],
  ])("maps %i %j", async (status, body, expected) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(answer(status, body)));
    expect(await loadRun(JOB)).toEqual(expected);
  });

  it("throws on a server error so error.tsx shows Retry", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(answer(500, { detail: "boom" })));
    await expect(loadRun(JOB)).rejects.toThrow("500");
  });
});
