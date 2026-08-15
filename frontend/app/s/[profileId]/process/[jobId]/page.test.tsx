import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";
import ProcessingPage from "./page";

const pushMock = vi.fn();
const replaceMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock, replace: replaceMock }),
}));

// Mock useJob at the module level — much simpler than wiring Supabase
const mockUseJob = vi.fn();
vi.mock("@/lib/useJob", () => ({
  useJob: (...args: unknown[]) => mockUseJob(...args),
  classify: vi.fn(),
}));

vi.mock("@/components/FailureScreen", () => ({
  default: ({ kind, reason, jobId, inputText }: { kind?: string; reason?: string; jobId?: string; inputText?: string }) => (
    <div data-testid="failure-screen" data-kind={kind} data-reason={reason} data-jobid={jobId} data-input={inputText} />
  ),
  resetFailChain: vi.fn(),
}));

const mockCreateSignedUrls = vi.fn();
vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    storage: { from: () => ({ createSignedUrls: (...a: unknown[]) => mockCreateSignedUrls(...a) }) },
    auth: { getSession: async () => ({ data: { session: { access_token: "test-token" } } }) },
  },
}));

const PROFILE_ID = "p1";

function makeParams(jobId = "j1") {
  const value = { profileId: PROFILE_ID, jobId };
  const p = Promise.resolve(value);
  (p as unknown as { status: string; value: typeof value }).status = "fulfilled";
  (p as unknown as { status: string; value: typeof value }).value = value;
  return p;
}

// Mock fetch for confirm actions
beforeEach(() => {
  sessionStorage.clear(); // signPaths caches signed URLs across renders
  pushMock.mockClear();
  replaceMock.mockClear();
  mockUseJob.mockReset();
  mockCreateSignedUrls.mockReset();
  mockCreateSignedUrls.mockResolvedValue({ data: null, error: null });
  global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 }) as unknown as typeof fetch;
});

const REFETCH = vi.fn();

function jobState(overrides: Partial<ReturnType<typeof mockUseJob>>) {
  return {
    bucket: "in-flight" as const,
    row: null,
    refetch: REFETCH,
    ...overrides,
  };
}

async function renderPage(paramsPromise: Promise<{ profileId: string; jobId: string }>) {
  let res: ReturnType<typeof render>;
  await act(async () => {
    res = render(<ProcessingPage params={paramsPromise} />);
  });
  return res!;
}

const RUNNING_ROW = {
  id: "j1", status: "running", current_stage: "analyze",
  failure_reason: null, input_text: "A story.", style_preset_id: null, pages: [], reveal: null,
};

const FAILED_MACHINE_ROW = {
  id: "j1", status: "failed", current_stage: "generate_scene",
  failure_reason: "machine", input_text: "A story.", style_preset_id: null, pages: [], reveal: null,
};

const FAILED_CHILD_ROW = { ...FAILED_MACHINE_ROW, failure_reason: "child_text" };

const PAUSED_ROW = {
  id: "j1", status: "awaiting_confirm", current_stage: "reveal",
  failure_reason: null, input_text: "A story.", style_preset_id: null, pages: [],
  reveal: {
    characters: [
      { char_id: "c0", name: "Kiko", image_path: "j1/ref-c0.png", chips: ["orange sock"] },
    ],
    taps_left: 2,
  },
};

const COMPLETE_ROW = {
  id: "j1", status: "complete", current_stage: "compose",
  failure_reason: null, input_text: "A story.", style_preset_id: null,
  pages: [{ scene_id: "s0", caption: "c", image_path: "p" }],
  reveal: null,
};

describe("ProcessingPage — bucket routing", () => {
  it("in-flight shows the stepper heading", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "in-flight", row: RUNNING_ROW }));
    await renderPage(makeParams("j1"));
    expect(screen.getByText(/making your book/i)).toBeDefined();
  });

  it("in-flight: analyze stage highlights step 1 with Reading your story", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "in-flight", row: RUNNING_ROW }));
    await renderPage(makeParams("j1"));
    expect(screen.getByText(/reading your story/i)).toBeDefined();
  });

  it("in-flight: generate_scene:3/8 highlights step 3 with Drawing picture 3 of 8", async () => {
    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...RUNNING_ROW, current_stage: "generate_scene:3/8" },
    }));
    await renderPage(makeParams("j1"));
    expect(screen.getByText(/drawing picture 3 of 8/i)).toBeDefined();
  });

  it("in-flight: unrecognised current_stage shows heading only, does not crash", async () => {
    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...RUNNING_ROW, current_stage: "unknown_future_node" },
    }));
    await renderPage(makeParams("j1"));
    expect(screen.getByText(/making your book/i)).toBeDefined();
  });

  it("terminal-success pushes to /book", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-success", row: COMPLETE_ROW }));
    await renderPage(makeParams("j1"));
    await waitFor(() =>
      expect(replaceMock).toHaveBeenCalledWith(`/s/${PROFILE_ID}/book/j1`)
    );
  });

  it("terminal-failure with machine reason renders retry FailureScreen", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-failure", row: FAILED_MACHINE_ROW }));
    await renderPage(makeParams("j1"));
    const el = screen.getByTestId("failure-screen");
    expect(el.getAttribute("data-kind")).toBe("retry");
    expect(el.getAttribute("data-input")).toBe("A story.");
  });

  it("terminal-failure with child_text reason renders revise FailureScreen", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "terminal-failure", row: FAILED_CHILD_ROW }));
    await renderPage(makeParams("j1"));
    expect(screen.getByTestId("failure-screen").getAttribute("data-kind")).toBe("revise");
  });

  it("not-found renders not-found FailureScreen", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "not-found", row: null }));
    await renderPage(makeParams("j1"));
    expect(screen.getByTestId("failure-screen").getAttribute("data-kind")).toBe("not-found");
  });
});

describe("ProcessingPage — reveal (paused bucket)", () => {
  it("paused: shows character name and chip when taps_left > 0", async () => {
    mockCreateSignedUrls.mockResolvedValue({ data: [{ signedUrl: "http://example.com/c0.png" }], error: null });
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByText(/Kiko/)).toBeDefined());
    expect(screen.getByText("orange sock")).toBeDefined();
  });

  it("paused: shows Use this one! button regardless of taps_left", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: /they look great|use this one/i })).toBeDefined());
  });

  it("paused: chips not rendered when taps_left == 0", async () => {
    const zeroTaps = {
      ...PAUSED_ROW,
      reveal: { ...PAUSED_ROW.reveal!, taps_left: 0 },
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: zeroTaps }));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: /they look great|use this one/i })).toBeDefined());
    expect(screen.queryByText("orange sock")).toBeNull();
  });

  it("chip tap POSTs try_again action and calls refetch", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByText("orange sock")).toBeDefined());

    await act(async () => {
      fireEvent.click(screen.getByText("orange sock"));
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/j1/confirm"),
      expect.objectContaining({
        body: JSON.stringify({ action: "try_again", char_id: "c0", attribute: "orange sock" }),
      })
    ));
    await waitFor(() => expect(REFETCH).toHaveBeenCalled());
  });

  it("Use this one! POSTs confirm action and calls refetch", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: /they look great|use this one/i })).toBeDefined());

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /they look great|use this one/i }));
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/j1/confirm"),
      expect.objectContaining({ body: JSON.stringify({ action: "confirm", char_id: null, attribute: null }) })
    ));
    await waitFor(() => expect(REFETCH).toHaveBeenCalled());
  });

  it("confirm sends the Bearer token", async () => {
    // Regression, prod job 4cb31620 (2026-08-11): the reveal shipped without an Authorization
    // header, so every "Use this one!" tap returned 401 {"detail":"missing token"} and the child
    // was stranded on the pause screen with no way forward. /storybooks, /me/avatar, /classrooms
    // and /jobs/{id}/review all attach the session token; this call was the only one that didn't.
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: /they look great|use this one/i })).toBeDefined());

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /they look great|use this one/i }));
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/j1/confirm"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    ));
  });

  it("while the stage has not moved off the reveal, in-flight shows Drawing it again… not the stepper", async () => {
    let fetchResolve!: () => void;
    global.fetch = vi.fn().mockReturnValue(
      new Promise<Response>(r => { fetchResolve = () => r({ ok: true, status: 200 } as Response); })
    ) as unknown as typeof fetch;

    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPage(paramsPromise);

    await waitFor(() => expect(screen.getByRole("button", { name: /they look great|use this one/i })).toBeDefined());

    act(() => { fireEvent.click(screen.getByRole("button", { name: /they look great|use this one/i })); });

    // Status flips to running before the graph advances — stage is still the reveal it paused on.
    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...PAUSED_ROW, status: "running", reveal: null },
    }));
    await act(async () => {
      view.rerender(<ProcessingPage params={paramsPromise} />);
    });

    // Should show the redraw placeholder, not the stepper
    expect(screen.getByText(/drawing it again/i)).toBeDefined();

    fetchResolve();
  });

  it("the redraw bridge lifts as soon as the stage moves — live progress is not hidden behind it", async () => {
    // Regression: `justConfirmed` was a ref cleared only on terminal states and on
    // in-flight→paused, never on confirm→in-flight. So after "They look great!" the page was
    // pinned to "Drawing it again…" for the whole run: every `generate_scene:n/8` UPDATE arrived
    // and re-rendered behind the placeholder, and the child saw the real progress only by
    // reloading, which reset the ref.
    let fetchResolve!: () => void;
    global.fetch = vi.fn().mockReturnValue(
      new Promise<Response>(r => { fetchResolve = () => r({ ok: true, status: 200 } as Response); })
    ) as unknown as typeof fetch;

    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPage(paramsPromise);

    await waitFor(() => expect(screen.getByRole("button", { name: /they look great|use this one/i })).toBeDefined());
    act(() => { fireEvent.click(screen.getByRole("button", { name: /they look great|use this one/i })); });

    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...RUNNING_ROW, current_stage: "generate_scene:5/8" },
    }));
    await act(async () => {
      view.rerender(<ProcessingPage params={paramsPromise} />);
    });

    expect(screen.getByText(/drawing picture 5 of 8/i)).toBeDefined();
    expect(screen.queryByText(/drawing it again/i)).toBeNull();

    fetchResolve();
  });

  it("confirm returning 200 with non-queued status shows no error — refetch reclassifies", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 }) as unknown as typeof fetch;
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: /they look great|use this one/i })).toBeDefined());

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /they look great|use this one/i }));
    });

    await waitFor(() => expect(REFETCH).toHaveBeenCalled());
    expect(screen.queryByTestId("failure-screen")).toBeNull();
  });

  it("reveal signing fails twice — still renders Use this one! (spec §7, not a failure screen)", async () => {
    mockCreateSignedUrls.mockResolvedValue({ data: null, error: new Error("net") });
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));

    await waitFor(() => expect(screen.getByRole("button", { name: /they look great|use this one/i })).toBeDefined());
    expect(screen.getByText(/Kiko/)).toBeDefined();
    expect(screen.queryByTestId("failure-screen")).toBeNull();
  });
});

describe("ProcessingPage — stall timer (spec §4.1)", () => {
  it("stall line appears after STALL_MS of no stage change", async () => {
    vi.useFakeTimers();
    mockUseJob.mockReturnValue(jobState({ bucket: "in-flight", row: RUNNING_ROW }));
    await renderPage(makeParams("j1"));

    expect(screen.queryByText(/taking longer than usual/i)).toBeNull();
    await act(async () => { vi.advanceTimersByTime(90_001); });
    expect(screen.getByText(/taking longer than usual/i)).toBeDefined();

    vi.useRealTimers();
  });

  it("stall line disappears when stage changes (new UPDATE)", async () => {
    vi.useFakeTimers();
    mockUseJob.mockReturnValue(jobState({ bucket: "in-flight", row: RUNNING_ROW }));
    const paramsPromise = makeParams("j1");
    const view = await renderPage(paramsPromise);

    await act(async () => { vi.advanceTimersByTime(90_001); });
    expect(screen.getByText(/taking longer than usual/i)).toBeDefined();

    // Stage changes — stall timer resets
    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...RUNNING_ROW, current_stage: "generate_scene:1/3" },
    }));
    await act(async () => {
      view.rerender(<ProcessingPage params={paramsPromise} />);
    });

    expect(screen.queryByText(/taking longer than usual/i)).toBeNull();
    vi.useRealTimers();
  });
});
