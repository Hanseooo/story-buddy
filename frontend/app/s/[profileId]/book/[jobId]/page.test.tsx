import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";
import BookPage from "./page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ profileId: "p1", jobId: "j1" }),
}));

const mockUseJob = vi.fn();
vi.mock("@/lib/useJob", () => ({
  useJob: (...args: unknown[]) => mockUseJob(...args),
  classify: vi.fn(),
}));

vi.mock("@/components/FailureScreen", () => ({
  default: ({ kind, countable, onReload }: { kind: string; countable?: boolean; onReload?: () => void }) => (
    <div data-testid="failure-screen" data-kind={kind} data-countable={String(countable ?? true)}>
      {onReload && <button onClick={onReload}>reload</button>}
    </div>
  ),
  resetFailChain: vi.fn(),
}));

import { resetFailChain } from "@/components/FailureScreen";

const mockCreateSignedUrls = vi.fn();
const mockGetSession = vi.fn();
const mockSingle = vi.fn();
vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: { getSession: (...args: unknown[]) => mockGetSession(...args) },
    storage: { from: () => ({ createSignedUrls: (...a: unknown[]) => mockCreateSignedUrls(...a) }) },
    from: () => ({ select: () => ({ eq: () => ({ single: () => mockSingle() }) }) }),
    channel: () => ({ on: () => ({ subscribe: () => ({}) }) }),
    removeChannel: vi.fn(),
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
  id: "j1", status: "complete", current_stage: "compose", profile_id: "p1",
  failure_reason: null, input_text: "x", title: "A Very Long Title That Keeps Going And Going", style_preset_id: null, pages: PAGES, reveal: null,
  approved_at: "2026-10-21T00:00:00Z", rejected_at: null,
};

const SIGNED = PAGES.map((p, i) => ({ signedUrl: `https://cdn/${i}.png`, error: null }));

function stubPdfFetch(fetchPdf: (...args: unknown[]) => unknown) {
  vi.stubGlobal("fetch", (url: string, init?: RequestInit) => url.endsWith("/me/notes")
    ? Promise.resolve(new Response("[]")) : fetchPdf(url, init));
}

beforeEach(() => {
  sessionStorage.clear(); // signPaths caches signed URLs across renders
  pushMock.mockClear();
  mockUseJob.mockReset();
  mockCreateSignedUrls.mockReset();
  mockGetSession.mockReset();
  mockSingle.mockReset();
  vi.unstubAllGlobals();
  vi.mocked(resetFailChain).mockReset();
});

describe("BookPage — teacher note", () => {
  it.each(["approved", "rejected", "pending"])("opens, closes and reopens a note without a %s verdict", async (review) => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: {
      ...COMPLETE_ROW, approved_at: review === "approved" ? COMPLETE_ROW.approved_at : null,
      rejected_at: review === "rejected" ? "2026-10-29T00:00:00Z" : null,
    } }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "synthetic" } } });
    let notes = [{ job_id: "j1", body: "Lovely story!", seen: false, updated_at: "2026-10-29T00:00:00Z" }];
    const network = vi.fn(async (_url: string, init?: RequestInit) => init?.method === "POST"
      ? new Response(null, { status: 204 })
      : new Response(JSON.stringify(notes)));
    vi.stubGlobal("fetch", network);
    await renderPage(makeParams());
    await waitFor(() => expect(screen.getByText("Lovely story!")).toBeVisible());
    await waitFor(() => expect(network).toHaveBeenCalledWith(expect.stringContaining("/jobs/j1/note/seen"), expect.objectContaining({
      method: "POST", body: JSON.stringify({ updated_at: "2026-10-29T00:00:00Z" }),
    })));
    const close = screen.getByRole("button", { name: "Close" });
    fireEvent.click(close);
    const control = screen.getByText("A note from your teacher");
    expect(control).toHaveFocus();
    expect(screen.getByText("Lovely story!")).not.toBeVisible();
    fireEvent.click(control);
    await waitFor(() => expect(screen.getByText("Lovely story!")).toBeVisible());
    fireEvent.keyDown(screen.getByText("Lovely story!"), { key: "Escape" });
    expect(control).toHaveFocus();
    expect(screen.getByText("Lovely story!")).not.toBeVisible();
    expect(document.body).not.toHaveTextContent(/\b(?:approved|rejected|pending)\b/i);
    notes = [{ job_id: "j1", body: "Your new ending is lovely!", seen: false, updated_at: "2026-10-29T01:00:00Z" }];
    fireEvent.focus(window);
    await waitFor(() => expect(screen.getByText("Your new ending is lovely!")).toBeVisible());
    expect(screen.queryByText("Lovely story!")).toBeNull();
    notes = [];
    fireEvent.focus(window);
    await waitFor(() => expect(screen.queryByText("A note from your teacher")).toBeNull());
  });

  it("keeps the reader usable when notes fail to load", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "synthetic" } } });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await renderPage(makeParams());
    await waitFor(() => expect(screen.getByRole("img")).toBeVisible());
    expect(screen.queryByText("A note from your teacher")).toBeNull();
  });
});

describe("BookPage — PDF download", () => {
  it.each(["peer", "owner", "read_failure"])("reconciles denied PDF access for %s without a Realtime update", async (kind) => {
    const { useJob } = await vi.importActual<typeof import("@/lib/useJob")>("@/lib/useJob");
    mockUseJob.mockImplementation(useJob);
    const row = { ...COMPLETE_ROW, profile_id: kind === "owner" ? "p1" : "classmate-1" };
    mockSingle.mockResolvedValueOnce({ data: row, error: null }).mockResolvedValue({
      data: kind === "owner" ? { ...row, approved_at: null } : null,
      error: kind === "owner" ? null : { code: kind === "peer" ? "PGRST116" : "503" },
    });
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
    stubPdfFetch(vi.fn().mockResolvedValue(new Response(null, { status: kind === "owner" ? 409 : 404 })));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: /download pdf/i })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: /download pdf/i }));
    if (kind === "peer") {
      await waitFor(() => expect(screen.queryByRole("img")).toBeNull());
      expect(screen.queryByRole("button", { name: /download pdf/i })).toBeNull();
    } else if (kind === "owner") {
      await waitFor(() => expect(screen.getByRole("button", { name: /download pdf/i })).toBeDisabled());
      expect(screen.getByText("Ask your teacher about downloading this book")).toBeDefined();
      expect(screen.queryByRole("alert")).toBeNull();
    } else {
      await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("We couldn't download your book. Try again."));
      expect(screen.getByRole("button", { name: /download pdf/i })).toBeEnabled();
      expect(screen.getByRole("img")).toHaveAttribute("src", "https://cdn/0.png");
    }
  });

  it.each(["own", "peer"])("downloads an approved %s PDF with preparation feedback and preserves reading mode", async (kind) => {
    const row = kind === "peer" ? { ...COMPLETE_ROW, profile_id: "classmate-1" } : COMPLETE_ROW;
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
    let finish!: (response: Response) => void;
    const fetchPdf = vi.fn(() => new Promise<Response>(resolve => { finish = resolve; }));
    stubPdfFetch(fetchPdf);
    const createUrl = vi.fn(() => "blob:storybook");
    const revokeUrl = vi.fn();
    vi.stubGlobal("URL", { createObjectURL: createUrl, revokeObjectURL: revokeUrl });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: /download pdf/i })).toBeEnabled());
    expect(screen.queryByText("Ask your teacher about downloading this book")).toBeNull();
    expect(screen.getByRole("button", { name: /download pdf/i })).not.toHaveAttribute("aria-describedby");
    expect(document.body).not.toHaveTextContent(/\b(?:approve|approved|rejected|pending)\b/i);
    fireEvent.click(screen.getByLabelText("Scroll View"));
    fireEvent.click(screen.getByRole("button", { name: /download pdf/i }));
    await waitFor(() => expect(fetchPdf).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: /preparing pdf/i })).toBeDisabled();
    expect(screen.getByLabelText("Back to bookshelf")).toHaveAttribute("href", "/s/p1");
    finish(new Response("%PDF-1.7", {
      headers: { "content-type": "application/pdf", "content-disposition": 'attachment; filename="storybuddy-My-Story.pdf"' },
    }));
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    expect(click.mock.instances[0]).toHaveAttribute("download", "storybuddy-My-Story.pdf");
    expect(fetchPdf).toHaveBeenCalledWith(expect.stringContaining("/jobs/j1/pdf"), expect.objectContaining({
      headers: { Authorization: "Bearer test-token" }, signal: expect.any(AbortSignal),
    }));
    expect(screen.getByLabelText("Scroll View")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /download pdf/i })).toBeEnabled();
    click.mockRestore();
  });

  it("offers retry after a failed download and cancels an unfinished request on leaving", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "test-token" } } });
    const fetchPdf = vi.fn().mockRejectedValueOnce(new Error("network unavailable"))
      .mockImplementationOnce(() => new Promise(() => {}));
    stubPdfFetch(fetchPdf);
    const { unmount } = await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: /download pdf/i })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: /download pdf/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("We couldn't download your book. Try again."));
    expect(screen.getByRole("img")).toHaveAttribute("src", "https://cdn/0.png");
    fireEvent.click(screen.getByRole("button", { name: /download pdf/i }));
    await waitFor(() => expect(fetchPdf).toHaveBeenCalledTimes(2));
    const signal = fetchPdf.mock.calls[1][1].signal as AbortSignal;
    unmount();
    expect(signal.aborted).toBe(true);
  });

  it.each(["pending", "rejected", "peer_pending", "peer_rejected"])("does not enable PDF export for a %s book", async (kind) => {
    const row = { ...COMPLETE_ROW,
      approved_at: null,
      ...(kind.startsWith("peer") ? { profile_id: "someone-else" } : {}),
      ...(kind.endsWith("rejected") ? { rejected_at: "2026-10-21T01:00:00Z" } : {}),
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    if (kind.startsWith("peer")) expect(screen.queryByRole("button", { name: /download pdf/i })).toBeNull();
    else {
      expect(screen.getByRole("button", { name: /download pdf/i })).toBeDisabled();
      expect(screen.getByText("Ask your teacher about downloading this book")).toHaveAttribute("id", "pdf-approval-hint");
      expect(screen.getByRole("button", { name: /download pdf/i })).toHaveAttribute("aria-describedby", "pdf-approval-hint");
    }
    expect(document.body).not.toHaveTextContent(/\b(?:approve|approved|rejected|pending)\b/i);
  });
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

  it("defaults to pages view mode automatically", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderPage(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("img")).toBeDefined());
    expect(screen.getByRole("img")).toHaveAttribute("src", "https://cdn/0.png");
  });

  it("renders back button linking to student bookshelf", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderPage(makeParams("j1"));

    await waitFor(() => expect(screen.getByLabelText("Back to bookshelf")).toBeDefined());
    const backBtn = screen.getByLabelText("Back to bookshelf");
    expect(backBtn.getAttribute("href")).toBe("/s/p1");
  });

  it("renders the full book title as the reader heading", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderPage(makeParams("j1"));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /A Very Long Title That Keeps Going And Going/ })).toBeDefined();
    });
  });

  it("does not excerpt a classmate's story into the heading of their untitled book", async () => {
    // story-titles §5: the excerpt fallback is computed "only from text already authorized for
    // that viewer". `jobs.input_text` is the raw pre-redaction story, and RLS hands the whole row
    // to any classmate who opens an approved book from the shared gallery — so on someone else's
    // legacy untitled book the excerpt is not ours to render.
    const peerUntitledRow = {
      ...COMPLETE_ROW,
      profile_id: "someone-else",
      title: null,
      input_text: "My name is Ana and I live on Mabini Street.",
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: peerUntitledRow }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderPage(makeParams("j1"));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Untitled" })).toBeDefined();
    });
    expect(screen.queryByText(/Mabini Street/)).toBeNull();
    expect(screen.queryByText(/Ana/)).toBeNull();
  });

  it("still excerpts the reader's own untitled book", async () => {
    const ownUntitledRow = { ...COMPLETE_ROW, title: null, input_text: "The dog ran far away." };
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: ownUntitledRow }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderPage(makeParams("j1"));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "The dog ran far away." })).toBeDefined();
    });
  });

  it("renders Pages view button before Scroll view button in toggle pill", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderPage(makeParams("j1"));

    await waitFor(() => expect(screen.getByLabelText("Pages View")).toBeDefined());
    const buttons = screen.getAllByRole("button").filter(b => 
      b.getAttribute("aria-label") === "Pages View" || b.getAttribute("aria-label") === "Scroll View"
    );
    expect(buttons[0].getAttribute("aria-label")).toBe("Pages View");
    expect(buttons[1].getAttribute("aria-label")).toBe("Scroll View");
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

  it("identifies the current page when jumping with the page controls", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderAndSwitchToPages(makeParams("j1"));

    await waitFor(() => expect(screen.getByLabelText("Page 1 of 2")).toBeDefined());
    expect(screen.getByRole("button", { name: "Go to page 1" })).toHaveAttribute("aria-current", "page");
    fireEvent.click(screen.getByRole("button", { name: "Go to page 2" }));
    await waitFor(() => expect(screen.getByLabelText("Page 2 of 2")).toBeDefined());
    expect(screen.getByRole("button", { name: "Go to page 2" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("button", { name: "Go to page 1" })).not.toHaveAttribute("aria-current");
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

  it("signing fails twice → read-failure FailureScreen with countable=false (spec §4.3, §4.5)", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: null, error: new Error("network") });

    await renderPage(makeParams("j1"));

    await waitFor(() => expect(screen.getByTestId("failure-screen")).toBeDefined());
    expect(screen.getByTestId("failure-screen").getAttribute("data-kind")).toBe("read-failed");
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

describe("BookPage — a finished book whose pictures will not load (spec §4)", () => {
  it("offers re-reading, not a new paid book, and does not count against the chain", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: [], error: null });

    await renderPage(makeParams("j1"));

    await waitFor(() =>
      expect(screen.getByTestId("failure-screen").getAttribute("data-kind")).toBe("read-failed")
    );
    expect(screen.getByTestId("failure-screen").getAttribute("data-countable")).toBe("false");
    // Two attempts: the automatic re-sign already in signPages, and nothing more.
    expect(mockCreateSignedUrls).toHaveBeenCalledTimes(2);
  });

  it("reloading re-signs the same paths and renders the book", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    mockCreateSignedUrls.mockResolvedValue({ data: [], error: null });

    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByTestId("failure-screen")).toBeDefined());

    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "reload" }));
    });

    await waitFor(() => expect(screen.queryByTestId("failure-screen")).toBeNull());
    expect(mockCreateSignedUrls).toHaveBeenCalledTimes(3);
  });
});
