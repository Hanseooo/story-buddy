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
let sessionUserId: string | null = "p1";
vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    storage: { from: () => ({ createSignedUrls: (...a: unknown[]) => mockCreateSignedUrls(...a) }) },
    auth: {
      getSession: async () => ({
        data: { session: sessionUserId ? { user: { id: sessionUserId } } : null },
      }),
    },
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
};

const SIGNED = PAGES.map((p, i) => ({ signedUrl: `https://cdn/${i}.png`, error: null }));

beforeEach(() => {
  sessionUserId = "p1";
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

  it("does not excerpt an untitled book because the URL names its owner", async () => {
    // The route segment is typed by whoever is browsing, so it cannot decide whether the excerpt
    // is authorized. RLS grants the read on `auth.uid() = profile_id` (0008_authorization_surface),
    // and that is the only identity the gate may compare against: a classmate who walks to
    // /s/<owner>/book/<job> otherwise reads the owner's raw story out of the heading.
    const peerUntitledRow = {
      ...COMPLETE_ROW,
      profile_id: "p1", // matches the mocked route param, not the signed-in reader
      title: null,
      input_text: "My name is Ana and I live on Mabini Street.",
    };
    sessionUserId = "classmate-2";
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: peerUntitledRow }));
    mockCreateSignedUrls.mockResolvedValue({ data: SIGNED, error: null });

    await renderPage(makeParams("j1"));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Untitled" })).toBeDefined();
    });
    expect(screen.queryByText(/Mabini Street/)).toBeNull();
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
