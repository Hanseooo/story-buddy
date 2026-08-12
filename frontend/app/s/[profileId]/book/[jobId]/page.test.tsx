import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";
import BookPage from "./page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

const mockUseJob = vi.fn();
vi.mock("@/lib/useJob", () => ({
  useJob: (...args: unknown[]) => mockUseJob(...args),
  classify: vi.fn(),
}));

vi.mock("@/components/FailureScreen", () => ({
  default: ({ kind, countable }: { kind: string; countable?: boolean }) => (
    <div data-testid="failure-screen" data-kind={kind} data-countable={String(countable ?? true)} />
  ),
  resetFailChain: vi.fn(),
}));

import { resetFailChain } from "@/components/FailureScreen";

const mockCreateSignedUrls = vi.fn();
vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    storage: { from: () => ({ createSignedUrls: (...a: unknown[]) => mockCreateSignedUrls(...a) }) },
  },
}));

function makeParams(jobId = "j1") {
  const p = Promise.resolve({ jobId });
  (p as unknown as { status: string; value: { jobId: string } }).status = "fulfilled";
  (p as unknown as { status: string; value: { jobId: string } }).value = { jobId };
  return p;
}

async function renderPage(paramsPromise: Promise<{ jobId: string }>) {
  let res: ReturnType<typeof render>;
  await act(async () => {
    res = render(<BookPage params={paramsPromise} />);
  });
  return res!;
}

async function renderAndSwitchToPages(paramsPromise: Promise<{ jobId: string }>) {
  const res = await renderPage(paramsPromise);
  await waitFor(() => expect(screen.getByLabelText("Pages View")).toBeDefined());
  fireEvent.click(screen.getByLabelText("Pages View"));
  return res;
}

const REFETCH = vi.fn();

function jobState(overrides: Partial<ReturnType<typeof mockUseJob>>) {
  return { bucket: "in-flight" as const, row: null, refetch: REFETCH, ...overrides };
}

const PAGES = [
  { scene_id: "s0", caption: "The dog ran.", image_path: "j1/s0-1.png" },
  { scene_id: "s1", caption: "It found a stick.", image_path: "j1/s1-1.png" },
];

const COMPLETE_ROW = {
  id: "j1", status: "complete", current_stage: "compose",
  failure_reason: null, input_text: "x", style_preset_id: null, pages: PAGES, reveal: null,
};

const SIGNED = PAGES.map((p, i) => ({ signedUrl: `https://cdn/${i}.png`, error: null }));

beforeEach(() => {
  sessionStorage.clear(); // signPaths caches signed URLs across renders
  pushMock.mockClear();
  mockUseJob.mockReset();
  mockCreateSignedUrls.mockReset();
  vi.mocked(resetFailChain).mockReset();
});

describe("BookPage — bucket routing (spec invariant 1)", () => {
  it("failed row renders machine FailureScreen — not the wait state (S3 §7 regression)", async () => {
    mockUseJob.mockReturnValue(jobState({
      bucket: "terminal-failure",
      row: {
        id: "j1", status: "failed", current_stage: null, failure_reason: "machine",
        input_text: "x", style_preset_id: null, pages: [], reveal: null,
      },
    }));
    await renderPage(makeParams("j1"));
    expect(screen.getByTestId("failure-screen").getAttribute("data-kind")).toBe("retry");
    expect(screen.queryByText(/loading/i)).toBeNull();
  });

  it("queued row renders the wait state (four-bucket rule, spec §4.7)", async () => {
    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { id: "j1", status: "queued", current_stage: null, failure_reason: null, input_text: "x", style_preset_id: null, pages: [], reveal: null },
    }));
    await renderPage(makeParams("j1"));
    // Should NOT show the reader — shows a loading/wait state
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("not-found renders not-found FailureScreen", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "not-found", row: null }));
    await renderPage(makeParams("j1"));
    expect(screen.getByTestId("failure-screen").getAttribute("data-kind")).toBe("not-found");
  });
});

describe("BookPage — reader (terminal-success)", () => {
  it("renders first page image and caption; signs all paths in one batch", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    expect(screen.getByRole("img")).toHaveAttribute("src", "https://cdn/0.png");
    expect(mockCreateSignedUrls).toHaveBeenCalledTimes(1);
    expect(mockCreateSignedUrls).toHaveBeenCalledWith(["j1/s0-1.png", "j1/s1-1.png"], 3600);
  });

  it("image alt = caption; visible caption is aria-hidden (spec §4.3 double-read fix)", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    expect(screen.getByRole("img")).toHaveAttribute("alt", "The dog ran.");
    const caption = screen.getByText("The dog ran.");
    expect(caption).toHaveAttribute("aria-hidden", "true");
  });

  it("shows page indicator k / N", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByLabelText("Page 1 of 2")).toBeDefined());
  });

  it("right tap zone advances to next page", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    fireEvent.click(screen.getByTestId("nav-next"));
    await waitFor(() => {
      expect(screen.getByRole("img")).toHaveAttribute("src", "https://cdn/1.png");
    });
  });

  it("left tap zone goes back a page", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    fireEvent.click(screen.getByTestId("nav-next"));
    await waitFor(() => {
      expect(screen.getByRole("img")).toHaveAttribute("src", "https://cdn/1.png");
    });
    fireEvent.click(screen.getByTestId("nav-prev"));
    await waitFor(() => {
      expect(screen.getByRole("img")).toHaveAttribute("src", "https://cdn/0.png");
    });
  });

  it("one-page book: no nav zones rendered", async () => {
    const onePageRow = { ...COMPLETE_ROW, pages: [PAGES[0]] };
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: onePageRow }));
    mockCreateSignedUrls.mockResolvedValue({
      data: [SIGNED[0]], error: null,
    });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    expect(screen.queryByTestId("nav-next")).toBeNull();
    expect(screen.queryByTestId("nav-prev")).toBeNull();
  });

  it("calls resetFailChain when signed pages render (not just on bucket change)", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    expect(resetFailChain).toHaveBeenCalledTimes(1);
  });

  it("signing failure retries once automatically before showing failure screen", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls
      .mockResolvedValueOnce({ data: null, error: new Error("network") })
      .mockResolvedValueOnce({ data: SIGNED, error: null });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    expect(mockCreateSignedUrls).toHaveBeenCalledTimes(2);
  });

  it("signing fails twice → machine FailureScreen with countable=false (spec §4.3, §4.5)", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: null, error: new Error("network") });

    await renderPage(makeParams("j1"));

    await waitFor(() => expect(screen.getByTestId("failure-screen")).toBeDefined());
    expect(screen.getByTestId("failure-screen").getAttribute("data-kind")).toBe("retry");
    // countable=false prevents bumpChain() on press — signing failure is not a failed story
    expect(screen.getByTestId("failure-screen").getAttribute("data-countable")).toBe("false");
  });

  it("no jobs.error or moderation category rendered in any bucket (spec invariant 4)", async () => {
    const rowWithError = {
      ...COMPLETE_ROW,
      status: "failed",
      pages: [],
      error: "SENTINEL_MODERATION_DETAIL",
    };
    mockUseJob.mockReturnValue(jobState({
      bucket: "terminal-failure",
      row: { ...rowWithError, failure_reason: "machine" },
    }));
    await renderPage(makeParams("j1"));
    expect(screen.queryByText("SENTINEL_MODERATION_DETAIL")).toBeNull();
  });
});
