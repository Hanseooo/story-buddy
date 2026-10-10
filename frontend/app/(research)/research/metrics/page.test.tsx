import { beforeEach, describe, expect, it, test, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { renderToStaticMarkup } from "react-dom/server";
import LangfuseButton from "@/components/LangfuseButton";
import RunsPage from "./page";
import { computeAggregates, JobRow } from "@/utils/metrics";

test("aggregate math matches expected values", () => {
  const jobs: JobRow[] = [
    { id: "1", status: "complete", created_at: "2026-08-10", regen_count: 2, scenes_total: 5, scenes_passed: 4, usd_estimate: 0.25 },
    { id: "2", status: "complete", created_at: "2026-08-10", regen_count: 0, scenes_total: 5, scenes_passed: 5, usd_estimate: 0.125 },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.totalRuns).toBe(2);
  expect(stats.complete).toBe(2);
  expect(stats.totalRegens).toBe(2);
  expect(stats.estCost).toBe(0.375);
  expect(stats.scenePassRate).toBe(9 / 10);
  expect(stats.jobPassRate).toBe(1);
});

test("handles jobs with NULL/missing cost columns safely", () => {
  const jobs: JobRow[] = [
    { id: "3", status: "failed", created_at: "2026-08-10", regen_count: null, scenes_total: null, scenes_passed: null, usd_estimate: null },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.estCost).toBe(0);
  expect(stats.scenePassRate).toBe(0);
  expect(stats.jobPassRate).toBe(0);
});

// The bug this page shipped with: failed jobs never write scenes_total, so they fell out of
// BOTH sides of the scene fraction and the tile read 100% next to a column of failures.
test("jobPassRate counts failures that never recorded a scene", () => {
  const jobs: JobRow[] = [
    { id: "1", status: "complete", created_at: "2026-08-10", scenes_total: 4, scenes_passed: 4 },
    ...Array.from({ length: 7 }, (_, i) => ({
      id: `f${i}`,
      status: "failed",
      created_at: "2026-08-10",
    })),
  ];
  const stats = computeAggregates(jobs);
  expect(stats.scenePassRate).toBe(1);
  expect(stats.jobPassRate).toBe(1 / 8);
});

test("in-progress statuses are counted so the tiles sum to totalRuns", () => {
  const jobs: JobRow[] = [
    { id: "1", status: "complete", created_at: "2026-08-10" },
    { id: "2", status: "failed", created_at: "2026-08-10" },
    { id: "3", status: "awaiting_confirm", created_at: "2026-08-10" },
    { id: "4", status: "queued", created_at: "2026-08-10" },
    { id: "5", status: "running", created_at: "2026-08-10" },
  ];
  const stats = computeAggregates(jobs);
  expect(stats.inProgress).toBe(3);
  expect(stats.complete + stats.failed + stats.inProgress).toBe(stats.totalRuns);
  // Unconcluded runs must not drag the job pass rate down.
  expect(stats.jobPassRate).toBe(1 / 2);
});

const RUN_ID = "3f9a1c2e-0000-4000-8000-000000000001";
const TRACE = "https://cloud.langfuse.com/project/p/traces/secret";

// Every element of `type` in a server component's output. Client component props reach the browser.
function elementsOf(node: unknown, type: unknown): unknown[] {
  if (Array.isArray(node)) return node.flatMap((child) => elementsOf(child, type));
  if (!node || typeof node !== "object" || !("props" in node)) return [];
  const element = node as { type: unknown; props: { children?: unknown } };
  return [...(element.type === type ? [element] : []), ...elementsOf(element.props.children, type)];
}
const mockViewer = vi.hoisted(() => vi.fn());
const mockRows = vi.hoisted(() => vi.fn());
const mockSelect = vi.hoisted(() => vi.fn());
vi.mock("../../_shared/getResearchViewer", () => ({ getResearchViewer: mockViewer }));
vi.mock("@supabase/supabase-js", () => ({
  createClient: () => ({ from: () => ({ select: mockSelect }) }),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: vi.fn() }),
  usePathname: () => "/research/metrics",
  useSearchParams: () => new URLSearchParams(),
}));

describe("RunsPage", () => {
  beforeEach(() => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "false");
    mockSelect.mockReturnValue({ order: mockRows });
    mockRows.mockResolvedValue({
      data: [{ id: RUN_ID, status: "failed", created_at: "2026-10-01T10:00:00Z",
        title: "Secret Kite", approved_at: null, failure_reason: "machine", style_preset_id: "cel",
        langfuse_trace_url: TRACE }],
      error: null,
    });
    mockViewer.mockResolvedValue(null);
  });

  it("signed out: no title in the HTML and a sign-in link to the run", async () => {
    const page = await RunsPage({ searchParams: Promise.resolve({}) });
    expect(renderToStaticMarkup(page)).not.toContain("Secret Kite");
    render(page);
    expect(screen.getAllByRole("link", { name: "Sign in to view" })[0]).toHaveAttribute(
      "href", `/login?next=/research/metrics/${RUN_ID}`
    );
    expect(mockSelect.mock.calls.at(-1)?.[0].replace(/\s/g, "")).toBe(
      "id,status,created_at,style_preset_id,failure_reason,regen_count,image_count,scenes_total,scenes_passed,scenes_unchecked,usd_estimate,langfuse_trace_url,approved_at,title"
    );
    expect(screen.queryByRole("button", { name: /Langfuse/ })).toBeNull();
  });

  // #103: the button renders nothing with the flag off, but the URL in its props would still ship.
  it("flag off: no trace URL leaves the server", async () => {
    const page = await RunsPage({ searchParams: Promise.resolve({}) });
    expect(elementsOf(page, LangfuseButton)).toEqual([]);
  });

  it("flag on: each row gets the button with its trace", async () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "true");
    const page = await RunsPage({ searchParams: Promise.resolve({}) });
    expect(elementsOf(page, LangfuseButton).map((el) => (el as { props: { url: string } }).props.url)).toEqual([TRACE, TRACE]);
  });

  it("adjudicator: the row is a link named after the title", async () => {
    mockViewer.mockResolvedValue({ id: "r-2", role: "researcher", isAdjudicator: true, displayName: null });
    render(await RunsPage({ searchParams: Promise.resolve({}) }));
    expect(screen.getAllByRole("link", { name: "Open run Secret Kite" })[0]).toHaveAttribute(
      "href", `/research/metrics/${RUN_ID}`
    );
  });
});
