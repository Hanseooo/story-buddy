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
  mockCreateSignedUrls.mockImplementation(async (paths: string[]) => ({
    data: paths.map((path) => ({ path, signedUrl: `http://example.com/${path.split("/").pop()}` })),
    error: null,
  }));
  global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 }) as unknown as typeof fetch;
});

const REFETCH = vi.fn();

beforeEach(() => {
  REFETCH.mockReset();
  REFETCH.mockResolvedValue(true);
});

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

async function loadVisibleImages() {
  const images = await screen.findAllByRole("img");
  await act(async () => {
    images.forEach((image) => fireEvent.load(image));
  });
}

async function renderPausedPage(paramsPromise = makeParams("j1")) {
  const view = await renderPage(paramsPromise);
  await loadVisibleImages();
  return view;
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

  it("in-flight shows the stored title as context", async () => {
    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...RUNNING_ROW, title: "My Dragon Book" },
    }));
    await renderPage(makeParams("j1"));
    expect(screen.getByText("My Dragon Book")).toBeDefined();
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

  it("paused: shows Use these characters button regardless of taps_left", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Use these characters" })).toBeDefined());
  });

  it("paused: chips not rendered when taps_left == 0", async () => {
    const zeroTaps = {
      ...PAUSED_ROW,
      reveal: { ...PAUSED_ROW.reveal!, taps_left: 0 },
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: zeroTaps }));
    await renderPausedPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Use these characters" })).toBeDefined());
    expect(screen.queryByText("orange sock")).toBeNull();
  });

  it.each([
    [3, "3 redraws left for this book"],
    [2, "2 redraws left for this book"],
    [1, "1 redraw left for this book"],
  ])("shows the server allowance as shared book-wide copy", async (tapsLeft, copy) => {
    mockUseJob.mockReturnValue(jobState({
      bucket: "paused",
      row: { ...PAUSED_ROW, reveal: { ...PAUSED_ROW.reveal!, taps_left: tapsLeft } },
    }));
    await renderPausedPage();

    expect(screen.getByText(copy)).toBeDefined();
    expect(screen.getByText("Shared by all your characters.")).toBeDefined();
  });

  it("explains a spent allowance and leaves continue and exit available", async () => {
    mockUseJob.mockReturnValue(jobState({
      bucket: "paused",
      row: { ...PAUSED_ROW, reveal: { ...PAUSED_ROW.reveal!, taps_left: 0 } },
    }));
    await renderPausedPage();

    expect(screen.getByText(
      "No redraws left for this book. You can use these characters or go back to your bookshelf."
    )).toBeDefined();
    expect(screen.queryByRole("button", { name: "orange sock" })).toBeNull();
    expect(screen.getByRole("button", { name: "Use these characters" })).toBeEnabled();
    expect(screen.getByRole("link", { name: /bookshelf/i })).toBeDefined();
  });

  it("selecting is free and explicit redraw sends the selected trait once", async () => {
    let resolveFetch!: (value: Response) => void;
    global.fetch = vi.fn().mockReturnValue(
      new Promise<Response>((resolve) => { resolveFetch = resolve; })
    ) as unknown as typeof fetch;
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPausedPage();

    const trait = await screen.findByRole("button", { name: "orange sock" });
    fireEvent.click(trait);

    expect(global.fetch).not.toHaveBeenCalled();
    expect(trait).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText(
      "We'll draw a new picture, paying extra attention to orange sock. Other details may change."
    )).toBeDefined();

    const redraw = screen.getByRole("button", { name: "Redraw Kiko" });
    fireEvent.click(redraw);
    fireEvent.click(redraw);

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/j1/confirm"),
      expect.objectContaining({
        body: JSON.stringify({ action: "try_again", char_id: "c0", attribute: "orange sock" }),
      })
    ));
    expect(trait).toBeDisabled();
    expect(screen.getByRole("button", { name: "Use these characters" })).toBeDisabled();

    resolveFetch({ ok: true, status: 200 } as Response);
    await waitFor(() => expect(REFETCH).toHaveBeenCalledTimes(1));
  });

  it("keeps one selection across the screen and Cancel clears it", async () => {
    const twoCharacters = {
      ...PAUSED_ROW,
      reveal: {
        ...PAUSED_ROW.reveal!,
        characters: [
          ...PAUSED_ROW.reveal!.characters,
          { char_id: "c1", name: "Maya", image_path: "j1/ref-c1.png", chips: ["blue hat"] },
        ],
      },
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: twoCharacters }));
    await renderPausedPage();

    const sock = screen.getByRole("button", { name: "orange sock" });
    const hat = screen.getByRole("button", { name: "blue hat" });
    fireEvent.click(sock);
    fireEvent.click(hat);

    expect(sock).toHaveAttribute("aria-pressed", "false");
    expect(hat).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("button", { name: "Redraw Kiko" })).toBeNull();
    expect(screen.getByRole("button", { name: "Redraw Maya" })).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(hat).toHaveAttribute("aria-pressed", "false");
    expect(screen.queryByRole("button", { name: /Redraw/ })).toBeNull();
    expect(global.fetch).not.toHaveBeenCalled();

    fireEvent.click(sock);
    fireEvent.click(sock);
    expect(sock).toHaveAttribute("aria-pressed", "false");
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("Use these characters POSTs confirm action and calls refetch", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPausedPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Use these characters" })).toBeDefined());

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Use these characters" }));
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/j1/confirm"),
      expect.objectContaining({ body: JSON.stringify({ action: "confirm", char_id: null, attribute: null }) })
    ));
    await waitFor(() => expect(REFETCH).toHaveBeenCalled());
  });

  it("confirm sends the Bearer token", async () => {
    // Regression, prod job 4cb31620 (2026-08-11): the reveal shipped without an Authorization
    // header, so every "Use these characters" tap returned 401 {"detail":"missing token"} and the child
    // was stranded on the pause screen with no way forward. /storybooks, /me/avatar, /classrooms
    // and /jobs/{id}/review all attach the session token; this call was the only one that didn't.
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPausedPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Use these characters" })).toBeDefined());

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Use these characters" }));
    });

    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/jobs/j1/confirm"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    ));
  });

  it("while the stage has not moved off the reveal, in-flight shows the named redraw state", async () => {
    let fetchResolve!: () => void;
    global.fetch = vi.fn().mockReturnValue(
      new Promise<Response>(r => { fetchResolve = () => r({ ok: true, status: 200 } as Response); })
    ) as unknown as typeof fetch;

    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);

    await waitFor(() => expect(screen.getByRole("button", { name: "Use these characters" })).toBeDefined());

    fireEvent.click(screen.getByRole("button", { name: "orange sock" }));
    fireEvent.click(screen.getByRole("button", { name: "Redraw Kiko" }));

    // Spec §3.5 wants the dispatch announced. That happens here, on the reveal screen, in a live
    // region that was already mounted and holding other text — the only kind that announces. The
    // in-flight screen below states the same thing visually, and asserting `aria-live` on it was
    // asserting nothing: a region mounted together with its text is silent.
    const announcement = screen.getByText("Redrawing Kiko…");
    expect(announcement.closest("[aria-live='polite']")).not.toBeNull();

    // Status flips to running before the graph advances — stage is still the reveal it paused on.
    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...PAUSED_ROW, status: "running", reveal: null },
    }));
    await act(async () => {
      view.rerender(<ProcessingPage params={paramsPromise} />);
    });

    // Should show the named redraw placeholder, not the stepper
    expect(screen.getByRole("heading", { name: "Redrawing Kiko…" })).toBeDefined();

    fetchResolve();
  });

  it("the redraw bridge lifts as soon as the stage moves — live progress is not hidden behind it", async () => {
    // Regression: the redraw bridge must lift as soon as the stage changes, rather than
    // pinned to the redraw state for the whole run: every `generate_scene:n/8` UPDATE arrived
    // and re-rendered behind the placeholder, and the child saw the real progress only by
    // reloading, which reset the ref.
    let fetchResolve!: () => void;
    global.fetch = vi.fn().mockReturnValue(
      new Promise<Response>(r => { fetchResolve = () => r({ ok: true, status: 200 } as Response); })
    ) as unknown as typeof fetch;

    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);

    await waitFor(() => expect(screen.getByRole("button", { name: "Use these characters" })).toBeDefined());
    fireEvent.click(screen.getByRole("button", { name: "orange sock" }));
    fireEvent.click(screen.getByRole("button", { name: "Redraw Kiko" }));

    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...RUNNING_ROW, current_stage: "generate_scene:5/8" },
    }));
    await act(async () => {
      view.rerender(<ProcessingPage params={paramsPromise} />);
    });

    expect(screen.getByText(/drawing picture 5 of 8/i)).toBeDefined();
    expect(screen.queryByText("Redrawing Kiko…")).toBeNull();

    fetchResolve();
  });

  it("confirm returning 200 with non-queued status shows no error — refetch reclassifies", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, status: 200 }) as unknown as typeof fetch;
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPausedPage();
    await waitFor(() => expect(screen.getByRole("button", { name: "Use these characters" })).toBeDefined());

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Use these characters" }));
    });

    await waitFor(() => expect(REFETCH).toHaveBeenCalled());
    expect(screen.queryByText("We couldn't send that choice. Please try again.")).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("clears selection when the authoritative reveal changes", async () => {
    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);
    fireEvent.click(await screen.findByRole("button", { name: "orange sock" }));

    const updated = {
      ...PAUSED_ROW,
      reveal: {
        characters: [
          { char_id: "c0", name: "Kiko", image_path: "j1/ref-c0-v2.png", chips: ["green scarf"] },
        ],
        taps_left: 1,
      },
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: updated }));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));

    expect(screen.queryByRole("button", { name: "Redraw Kiko" })).toBeNull();
    expect(screen.getByText("1 redraw left for this book")).toBeDefined();
    expect(screen.getByText("The character choices were updated.")).toBeDefined();
  });

  it("clears selection after a redraw round-trip that still suggests the same trait", async () => {
    // The reveal fingerprint is only compared while paused. Leaving the pause used to forget it,
    // so a redraw whose replacement kept the same suggestion came back with the child's spent
    // selection and its "we'll draw a new picture" panel still on screen.
    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);

    fireEvent.click(await screen.findByRole("button", { name: "orange sock" }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Redraw Kiko" }));
    });

    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...PAUSED_ROW, status: "running", reveal: null },
    }));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));

    const redrawn = {
      ...PAUSED_ROW,
      reveal: {
        characters: [
          { char_id: "c0", name: "Kiko", image_path: "j1/ref-c0-v2.png", chips: ["orange sock"] },
        ],
        taps_left: 1,
      },
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: redrawn }));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));

    expect(screen.queryByRole("button", { name: "Redraw Kiko" })).toBeNull();
    expect(screen.getByText("1 redraw left for this book")).toBeDefined();
  });

  it("announces the pending redraw before the job row moves off the pause", async () => {
    let fetchResolve!: () => void;
    global.fetch = vi.fn().mockReturnValue(
      new Promise<Response>(r => { fetchResolve = () => r({ ok: true, status: 200 } as Response); })
    ) as unknown as typeof fetch;

    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPausedPage();

    fireEvent.click(await screen.findByRole("button", { name: "orange sock" }));
    fireEvent.click(screen.getByRole("button", { name: "Redraw Kiko" }));

    const pending = screen.getByText("Redrawing Kiko…");
    expect(pending.closest("[aria-live='polite']")).not.toBeNull();

    fetchResolve();
  });

  it("continuing never claims a redraw is happening", async () => {
    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Use these characters" }));
    });

    mockUseJob.mockReturnValue(jobState({
      bucket: "in-flight",
      row: { ...PAUSED_ROW, status: "running", reveal: null },
    }));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));

    expect(screen.queryByText(/Redrawing/)).toBeNull();
    expect(screen.queryByText(/previous picture/i)).toBeNull();
  });

  it("stops announcing an updated choice once the child picks again", async () => {
    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);
    fireEvent.click(await screen.findByRole("button", { name: "orange sock" }));

    const updated = {
      ...PAUSED_ROW,
      reveal: {
        characters: [
          { char_id: "c0", name: "Kiko", image_path: "j1/ref-c0-v2.png", chips: ["green scarf"] },
        ],
        taps_left: 1,
      },
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: updated }));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));
    expect(screen.getByText("The character choices were updated.")).toBeDefined();

    await loadVisibleImages();
    fireEvent.click(screen.getByRole("button", { name: "green scarf" }));

    expect(screen.queryByText("The character choices were updated.")).toBeNull();
  });

  it("a reveal with no characters still lets the child move on", async () => {
    mockUseJob.mockReturnValue(jobState({
      bucket: "paused",
      row: { ...PAUSED_ROW, reveal: { characters: [], taps_left: 2 } },
    }));
    await renderPage(makeParams("j1"));

    expect(screen.getByRole("button", { name: "Use these characters" })).not.toBeDisabled();
  });

  it("does not re-enable redraw after a failed request reveals a consumed pause", async () => {
    const paramsPromise = makeParams("j1");
    let current = jobState({ bucket: "paused", row: PAUSED_ROW });
    const reconcile = vi.fn(async () => {
      current = jobState({ bucket: "in-flight", row: { ...PAUSED_ROW, status: "running", reveal: null } });
      return true;
    });
    mockUseJob.mockImplementation(() => ({ ...current, refetch: reconcile }));
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 409 }) as unknown as typeof fetch;
    const view = await renderPausedPage(paramsPromise);

    fireEvent.click(await screen.findByRole("button", { name: "orange sock" }));
    fireEvent.click(screen.getByRole("button", { name: "Redraw Kiko" }));
    await waitFor(() => expect(reconcile).toHaveBeenCalledTimes(1));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));

    expect(global.fetch).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: "Redraw Kiko" })).toBeNull();
    expect(screen.queryByText("We couldn't send that choice. Please try again.")).toBeNull();
  });

  it("says the choice could not be sent when dispatch fails into a still-valid pause", async () => {
    // Spec §4: "Show 'We couldn't send that choice. Please try again.' Refresh the row before
    // enabling another submission; retain selection only if it is still offered in the same pause."
    const reconcile = vi.fn().mockResolvedValue(true);
    mockUseJob.mockReturnValue({ ...jobState({ bucket: "paused", row: PAUSED_ROW }), refetch: reconcile });
    global.fetch = vi.fn().mockRejectedValue(new Error("network down")) as unknown as typeof fetch;
    await renderPausedPage();

    fireEvent.click(await screen.findByRole("button", { name: "orange sock" }));
    fireEvent.click(screen.getByRole("button", { name: "Redraw Kiko" }));

    expect(await screen.findByText("We couldn't send that choice. Please try again.")).toBeDefined();
    await waitFor(() => expect(reconcile).toHaveBeenCalled());
    expect(global.fetch).toHaveBeenCalledTimes(1);
    // The pause is unchanged, so the trait is still offered and still chosen.
    expect(screen.getByRole("button", { name: /orange sock/ })).toHaveAttribute("aria-pressed", "true");
  });

  it("keeps submissions locked when both dispatch and reconciliation fail", async () => {
    const reconcile = vi.fn().mockResolvedValue(false);
    mockUseJob.mockReturnValue({ ...jobState({ bucket: "paused", row: PAUSED_ROW }), refetch: reconcile });
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 503 }) as unknown as typeof fetch;
    await renderPausedPage();

    fireEvent.click(await screen.findByRole("button", { name: "orange sock" }));
    fireEvent.click(screen.getByRole("button", { name: "Redraw Kiko" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn't refresh your character choices. Try loading them again."
    );
    expect(screen.getByRole("button", { name: "Use these characters" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Load character choices again" })).toBeDefined();
    expect(screen.getByRole("link", { name: /bookshelf/i })).toBeDefined();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("blocks continue after signing failure and retries the read without posting", async () => {
    mockCreateSignedUrls
      .mockResolvedValueOnce({ data: null, error: new Error("net") })
      .mockResolvedValueOnce({ data: null, error: new Error("net") })
      .mockResolvedValueOnce({ data: [{ path: "j1/ref-c0.png", signedUrl: "http://example.com/c0.png" }], error: null });
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));

    expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't load Kiko's picture.");
    expect(screen.getByRole("button", { name: "Use these characters" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Try loading Kiko's picture again" }));

    const image = await screen.findByRole("img", { name: "Kiko" });
    fireEvent.load(image);
    await waitFor(() => expect(screen.getByRole("button", { name: "Use these characters" })).toBeEnabled());
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("turns an img load error into an inline read retry", async () => {
    mockCreateSignedUrls.mockResolvedValue({
      data: [{ path: "j1/ref-c0.png", signedUrl: "http://example.com/c0.png" }],
      error: null,
    });
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPage(makeParams("j1"));

    const image = await screen.findByRole("img", { name: "Kiko" });
    fireEvent.error(image);

    expect(screen.getByRole("alert")).toHaveTextContent("We couldn't load Kiko's picture.");
    expect(screen.getByRole("button", { name: "Use these characters" })).toBeDisabled();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("explains an empty chip list without inventing a redraw choice", async () => {
    const emptyChips = {
      ...PAUSED_ROW,
      reveal: {
        ...PAUSED_ROW.reveal!,
        characters: [{ ...PAUSED_ROW.reveal!.characters[0], chips: [] }],
      },
    };
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: emptyChips }));
    await renderPage(makeParams("j1"));

    expect(screen.getByText("No suggested changes are available for this character.")).toBeDefined();
    expect(screen.queryByRole("button", { name: /Redraw Kiko/ })).toBeNull();
    expect(screen.getByRole("link", { name: /bookshelf/i })).toBeDefined();
  });

  it("Escape clears an unsubmitted selection without sending a request", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPausedPage();
    const trait = await screen.findByRole("button", { name: "orange sock" });
    trait.focus();
    fireEvent.click(trait);

    fireEvent.keyDown(window, { key: "Escape" });

    expect(trait).toHaveAttribute("aria-pressed", "false");
    expect(document.activeElement).toBe(trait);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("focuses the updated character heading when the selected control disappears", async () => {
    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);
    const trait = await screen.findByRole("button", { name: "orange sock" });
    trait.focus();
    fireEvent.click(trait);

    mockUseJob.mockReturnValue(jobState({
      bucket: "paused",
      row: {
        ...PAUSED_ROW,
        reveal: {
          characters: [{ char_id: "c0", name: "Kiko", image_path: "j1/ref-c0-v2.png", chips: ["green scarf"] }],
          taps_left: 1,
        },
      },
    }));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Kiko" })).toHaveFocus());
  });

  it("leaves focus alone when the child has tabbed away from the character card", async () => {
    // Spec §5: focus the updated heading "when focus would otherwise be lost; do not steal focus
    // from a child actively navigating elsewhere." Selecting a trait and then tabbing to another
    // control is the second case, not the first.
    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);
    const trait = await screen.findByRole("button", { name: "orange sock" });
    trait.focus();
    fireEvent.click(trait);

    const continueButton = screen.getByRole("button", { name: /Use these characters/i });
    continueButton.focus();

    mockUseJob.mockReturnValue(jobState({
      bucket: "paused",
      row: {
        ...PAUSED_ROW,
        reveal: {
          characters: [{ char_id: "c0", name: "Kiko", image_path: "j1/ref-c0-v2.png", chips: ["green scarf"] }],
          taps_left: 1,
        },
      },
    }));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));

    await waitFor(() => expect(screen.getByText("green scarf")).toBeDefined());
    expect(screen.getByRole("heading", { name: "Kiko" })).not.toHaveFocus();
  });

  it("explains a changed reveal visibly, not only to a screen reader", async () => {
    // Spec §4: "explain that the character choices updated when needed" — an `sr-only` live
    // region announces it to one child and tells a sighted child nothing.
    const paramsPromise = makeParams("j1");
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    const view = await renderPausedPage(paramsPromise);
    fireEvent.click(await screen.findByRole("button", { name: "orange sock" }));

    mockUseJob.mockReturnValue(jobState({
      bucket: "paused",
      row: {
        ...PAUSED_ROW,
        reveal: {
          characters: [{ char_id: "c0", name: "Kiko", image_path: "j1/ref-c0-v2.png", chips: ["green scarf"] }],
          taps_left: 1,
        },
      },
    }));
    await act(async () => view.rerender(<ProcessingPage params={paramsPromise} />));

    await waitFor(() => {
      const notices = screen.getAllByText("The character choices were updated.");
      expect(notices.some((node) => !node.closest(".sr-only"))).toBe(true);
    });
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

describe("ProcessingPage — exit navigation", () => {
  it("in-flight shows top Bookshelf exit link", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "in-flight", row: RUNNING_ROW }));
    await renderPage(makeParams("j1"));
    const bookshelfLink = screen.getByRole("link", { name: /bookshelf/i });
    expect(bookshelfLink).toHaveAttribute("href", "/s/p1");
  });

  it("paused reveal shows top Bookshelf exit link", async () => {
    mockUseJob.mockReturnValue(jobState({ bucket: "paused", row: PAUSED_ROW }));
    await renderPausedPage();
    const bookshelfLink = screen.getByRole("link", { name: /bookshelf/i });
    expect(bookshelfLink).toHaveAttribute("href", "/s/p1");
  });

  it("stalled prompt shows actionable Return to Bookshelf button", async () => {
    vi.useFakeTimers();
    mockUseJob.mockReturnValue(jobState({ bucket: "in-flight", row: RUNNING_ROW }));
    await renderPage(makeParams("j1"));

    await act(async () => { vi.advanceTimersByTime(90_001); });
    const returnBtn = screen.getByRole("link", { name: /return to bookshelf/i });
    expect(returnBtn).toHaveAttribute("href", "/s/p1");

    vi.useRealTimers();
  });
});
