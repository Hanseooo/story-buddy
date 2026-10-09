import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import fixture from "./__fixtures__/run.json";
import type { RunDetail } from "./types";
import RunPage from "./page";

const RUN = fixture as unknown as RunDetail;
const JOB = RUN.job.id;
const mockSession = vi.hoisted(() => vi.fn());
const mockFetch = vi.hoisted(() => vi.fn());
const mockRedirect = vi.hoisted(() =>
  vi.fn(() => {
    throw new Error("NEXT_REDIRECT");
  })
);

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: async () => ({ auth: { getSession: mockSession } }),
}));
vi.mock("next/navigation", () => ({ redirect: mockRedirect }));

const renderPage = async () => render(await RunPage({ params: Promise.resolve({ jobId: JOB }) }));

describe("RunPage states", () => {
  beforeEach(() => {
    mockRedirect.mockClear();
    mockSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
    vi.stubGlobal("fetch", mockFetch);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("sends a signed-out reader to log in and back", async () => {
    mockSession.mockResolvedValue({ data: { session: null } });
    await expect(renderPage()).rejects.toThrow("NEXT_REDIRECT");
    expect(mockRedirect).toHaveBeenCalledWith(`/login?next=${encodeURIComponent(`/research/metrics/${JOB}`)}`);
  });

  it.each([
    [404, "not_found", "Run not found"],
    [403, "not_approved", "Not approved yet"],
    [403, "researchers_only", "Researchers only"],
  ])("%i %s shows %s with a way back", async (status, detail, heading) => {
    mockFetch.mockResolvedValue(new Response(JSON.stringify({ detail }), { status }));
    await renderPage();
    expect(screen.getByRole("heading", { level: 1, name: heading })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All runs" })).toBeInTheDocument();
  });

  it("a run with no checkpoint shows the row and says so", async () => {
    mockFetch.mockResolvedValue(new Response(JSON.stringify({
      ...RUN,
      checkpointed: false,
      steps: [],
      story: null,
      characters: [],
      scenes: [],
      cost: null,
      state: null,
      moderation: null,
    })));
    await renderPage();
    expect(screen.getByRole("heading", { level: 1, name: "The Red Kite" })).toBeInTheDocument();
    expect(screen.getByText("No recorded steps for this run")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Pages" })).toBeNull();
  });

  it("a run blocked at the input gate says its safety result was not recorded", async () => {
    mockFetch.mockResolvedValue(new Response(JSON.stringify({
      ...RUN,
      job: { ...RUN.job, status: "failed", failure_reason: "child_text" },
      moderation: { input: null },
      ended_on: { node: "input_gate", kind: "failed" },
    })));
    await renderPage();
    expect(screen.getByText("Input safety result not recorded")).toBeInTheDocument();
    expect(screen.getByText("Content blocked")).toBeInTheDocument();
  });
});
