import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import fixture from "./__fixtures__/run.json";
import type { RunDetail } from "./types";
import LangfuseButton from "@/components/LangfuseButton";
import RunPage from "./page";

const RUN = fixture as unknown as RunDetail;

// Every element of `type` in a server component's output. Client component props reach the browser.
function elementsOf(node: unknown, type: unknown): unknown[] {
  if (Array.isArray(node)) return node.flatMap((child) => elementsOf(child, type));
  if (!node || typeof node !== "object" || !("props" in node)) return [];
  const element = node as { type: unknown; props: { children?: unknown } };
  return [...(element.type === type ? [element] : []), ...elementsOf(element.props.children, type)];
}
const JOB = RUN.job.id;
const mockSession = vi.hoisted(() => vi.fn());
const mockFetch = vi.hoisted(() => vi.fn());

vi.mock("@/utils/supabase/server", () => ({
  createSupabaseServerClient: async () => ({ auth: { getSession: mockSession } }),
}));

const renderPage = async () => render(await RunPage({ params: Promise.resolve({ jobId: JOB }) }));

describe("RunPage states", () => {
  beforeEach(() => {
    mockSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
    vi.stubGlobal("fetch", mockFetch);
  });
  afterEach(() => vi.unstubAllGlobals());

  // Middleware is the only auth gate (AGENTS.md). Redirecting a signed-in user to /login would
  // bounce them to /classroom, so a session the backend rejects throws to error.tsx instead.
  it("a rejected session throws instead of redirecting", async () => {
    mockFetch.mockResolvedValue(new Response(null, { status: 401 }));
    await expect(renderPage()).rejects.toThrow("Unauthorized");
  });

  it("flag off: the trace URL stays on the server", async () => {
    const trace = "https://cloud.langfuse.com/project/p/traces/secret";
    mockFetch.mockResolvedValue(new Response(JSON.stringify({ ...RUN, job: { ...RUN.job, langfuse_trace_url: trace } })));
    expect(elementsOf(await RunPage({ params: Promise.resolve({ jobId: JOB }) }), LangfuseButton)).toEqual([]);
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

  it("a checkpointed run shows the graph before the story", async () => {
    mockFetch.mockResolvedValue(new Response(JSON.stringify(RUN)));
    await renderPage();
    const headings = screen.getAllByRole("heading", { level: 2 }).map((heading) => heading.textContent);
    expect(headings.slice(0, 2)).toEqual(["Path through the pipeline", "Story"]);
  });
});
