import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe, onTestFinished } from "vitest";
import BookshelfPage from "./page";

const mockSelect = vi.hoisted(() => vi.fn());
const mockChannel = vi.hoisted(() => vi.fn());
const mockRemoveChannel = vi.hoisted(() => vi.fn());
const mockCreateSignedUrls = vi.hoisted(() => vi.fn());
const mockGetSession = vi.hoisted(() => vi.fn());
const mockSelectColumns = vi.hoisted(() => vi.fn());
const realtime = vi.hoisted(() => ({ emit: (() => {}) as (payload: { new: unknown }) => void }));

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: { getSession: mockGetSession },
    from: () => ({
      select: (columns: string) => {
        mockSelectColumns(columns);
        return {
          eq: () => ({
            order: mockSelect,
          }),
        };
      },
    }),
    storage: {
      from: () => ({ createSignedUrls: mockCreateSignedUrls }),
    },
    channel: () => ({
      on: (_event: string, _filter: unknown, handler: (payload: { new: unknown }) => void) => {
        realtime.emit = handler;
        return { subscribe: mockChannel };
      },
    }),
    removeChannel: mockRemoveChannel,
  },
}));

const PROFILE_ID = "user-abc";

const makeJob = (overrides: Partial<{
  id: string;
  status: string;
  profile_id: string;
  moderation_mode: string;
  input_text: string;
  title: string | null;
  pages: { scene_id: string; caption: string; image_path: string }[];
}> = {}) => ({
  id: "job-1",
  status: "complete",
  current_stage: null,
  failure_reason: null,
  input_text: "My story",
  title: null,
  style_preset_id: null,
  pages: [{ scene_id: "s1", caption: "cap", image_path: "pages/img.jpg" }],
  reveal: null,
  profile_id: PROFILE_ID,
  ...overrides,
});

// Holds every picture request open until the test finishes it; blob URLs count up from 1.
function stubPictures() {
  mockGetSession.mockResolvedValue({ data: { session: { access_token: "synthetic" } } });
  const pictures: { url: string; signal: AbortSignal; finish: (r: Response) => void }[] = [];
  vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => {
    if (url.includes("/me/notes")) return Promise.resolve(new Response("[]"));
    return new Promise<Response>(resolve => pictures.push({ url, signal: init!.signal!, finish: resolve }));
  }));
  const { createObjectURL, revokeObjectURL } = URL;
  onTestFinished(() => { Object.assign(URL, { createObjectURL, revokeObjectURL }); });
  let n = 0;
  URL.createObjectURL = vi.fn(() => `blob:synthetic-${++n}`);
  URL.revokeObjectURL = vi.fn();
  return pictures;
}

const teacherReviewBook = (id: string, title: string) => makeJob({
  id, title, moderation_mode: "teacher_review_v1",
  pages: [{ scene_id: "s1", caption: "c", image_path: `${id}/s1.png` }],
});

describe("Bookshelf — §9.11–12", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    sessionStorage.clear();
    mockGetSession.mockResolvedValue({ data: { session: null } });
    mockChannel.mockReturnValue({ unsubscribe: vi.fn() });
    mockCreateSignedUrls.mockResolvedValue({ data: [] });
  });

  it("shows only unread teacher notes and removes the badge on the next shelf load", async () => {
    mockSelect.mockResolvedValue({ data: [makeJob()] });
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "synthetic" } } });
    const fetchNotes = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify([
      { job_id: "job-1", body: "Lovely story!", seen: false },
    ]))).mockResolvedValueOnce(new Response(JSON.stringify([
      { job_id: "job-1", body: "Lovely story!", seen: true },
    ])));
    vi.stubGlobal("fetch", fetchNotes);
    const view = render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText("A note from your teacher")).toBeVisible());
    expect(fetchNotes).toHaveBeenCalledWith(expect.stringContaining("/me/notes"), expect.objectContaining({
      headers: { Authorization: "Bearer synthetic" }, cache: "no-store",
    }));
    mockGetSession.mockResolvedValue({ data: { session: null } });
    fireEvent.focus(window);
    await waitFor(() => expect(screen.queryByText("A note from your teacher")).toBeNull());
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "synthetic" } } });
    view.unmount();
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(fetchNotes).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByText("My story")).toBeVisible());
    expect(screen.queryByText("A note from your teacher")).toBeNull();
  });

  it("still renders books without a badge when notes cannot be fetched", async () => {
    mockSelect.mockResolvedValue({ data: [makeJob()] });
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "synthetic" } } });
    let finish!: (response: Response) => void;
    const network = vi.fn().mockImplementationOnce(() => new Promise<Response>(resolve => { finish = resolve; }))
      .mockResolvedValueOnce(new Response("[]"))
      .mockRejectedValue(new Error("offline"));
    vi.stubGlobal("fetch", network);
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText("My story")).toBeVisible());
    await waitFor(() => expect(network).toHaveBeenCalledTimes(1));
    fireEvent.focus(window);
    await waitFor(() => expect(network).toHaveBeenCalledTimes(2));
    await act(async () => { finish(new Response(JSON.stringify([{ job_id: "job-1", seen: false }]))); });
    expect(screen.queryByText("A note from your teacher")).toBeNull();
    fireEvent.focus(window);
    await waitFor(() => expect(network).toHaveBeenCalledTimes(3));
    expect(screen.queryByText("A note from your teacher")).toBeNull();
  });

  it("§9.11 — shows own jobs (explicit .eq filter prevents classmate leak)", async () => {
    mockSelect.mockResolvedValueOnce({ data: [makeJob({ id: "own-job" })] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText("My story")).toBeDefined());
    // Three links: desktop write CTA, the book card, and mobile write CTA
    expect(screen.getAllByRole("link")).toHaveLength(3);
    // §5.8 — the shelf reads only what classify, displayTitle and signPaths use
    expect(mockSelectColumns).toHaveBeenCalledWith("id, status, moderation_mode, input_text, title, pages");
  });

  it("shows the stored title on a bookshelf card", async () => {
    mockSelect.mockResolvedValueOnce({ data: [makeJob({ title: "My Dragon Book" })] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText("My Dragon Book")).toBeDefined());
  });

  it("falls back to the first-line excerpt when the stored title is null", async () => {
    mockSelect.mockResolvedValueOnce({
      data: [makeJob({ title: null, input_text: "A brave knight\nthe rest of the story" })],
    });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText("A brave knight")).toBeDefined());
  });

  it("§9.12 — terminal-success card links to /book/[jobId]", async () => {
    mockSelect.mockResolvedValueOnce({ data: [makeJob({ id: "j1", status: "complete" })] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      // The book card link (not the write CTAs)
      const cardLink = screen.getAllByRole("link").find(
        (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/book/j1`
      );
      expect(cardLink).toBeDefined();
      expect(cardLink).toHaveAttribute("href", `/s/${PROFILE_ID}/book/j1`);
    });
  });

  it("§9.12 — in-flight card links to /process/[jobId]", async () => {
    mockSelect.mockResolvedValueOnce({
      data: [makeJob({ id: "j2", status: "running", pages: [] })],
    });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      const cardLink = screen.getAllByRole("link").find(
        (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/process/j2`
      );
      expect(cardLink).toBeDefined();
      expect(screen.getByText("Writing...")).toBeDefined();
    });
  });

  it("§9.12 — paused card links to /process/[jobId]", async () => {
    mockSelect.mockResolvedValueOnce({
      data: [makeJob({ id: "j3", status: "awaiting_confirm", pages: [] })],
    });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      const cardLink = screen.getAllByRole("link").find(
        (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/process/j3`
      );
      expect(cardLink).toBeDefined();
      expect(screen.getByText("Needs characters")).toBeDefined();
    });
  });

  it("§9.12 — terminal-failure card links to /process/[jobId] (amended)", async () => {
    mockSelect.mockResolvedValueOnce({
      data: [makeJob({ id: "j4", status: "failed", pages: [] })],
    });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      const cardLink = screen.getAllByRole("link").find(
        (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/process/j4`
      );
      expect(cardLink).toBeDefined();
    });
  });

  it("failed cards live in a collapsed 'Didn't finish' section, not the shelf grid", async () => {
    mockSelect.mockResolvedValueOnce({
      data: [
        makeJob({ id: "ok1", status: "complete" }),
        makeJob({ id: "bad1", status: "failed", pages: [] }),
      ],
    });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => {
      expect(screen.getByText(/didn't finish \(1\)/i)).toBeDefined();
    });
    const failedLink = screen.getAllByRole("link").find(
      (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/process/bad1`
    );
    expect(failedLink?.closest("details")).not.toBeNull();
    const okLink = screen.getAllByRole("link").find(
      (el) => el.getAttribute("href") === `/s/${PROFILE_ID}/book/ok1`
    );
    expect(okLink?.closest("details")).toBeNull();
  });

  it("AC-01 — shows the route skeleton, not the heading, while the book list loads", async () => {
    mockSelect.mockReturnValueOnce(new Promise(() => {}));
    const { container } = render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Loading your bookshelf"));
    expect(screen.queryByRole("heading", { name: "Your Bookshelf" })).toBeNull();
    expect(container.querySelector('[aria-hidden="true"] .animate-pulse.bg-muted\\/50')).not.toBeNull();
  });

  it("AC-03 — a teacher-review cover appears in its card while another is still downloading", async () => {
    const pictures = stubPictures();
    mockSelect.mockResolvedValueOnce({ data: [teacherReviewBook("tr1", "First Book"), teacherReviewBook("tr2", "Second Book")] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(pictures).toHaveLength(2));
    await act(async () => { pictures.find(p => p.url.includes("/jobs/tr1/"))!.finish(new Response("png")); });
    const first = screen.getByRole("link", { name: "First Book" });
    await waitFor(() => expect(first.querySelector("img")).toHaveAttribute("src", "blob:synthetic-1"));
    const second = screen.getByRole("link", { name: "Second Book" });
    expect(second.querySelector("img")).toBeNull();
    expect(second.querySelector(".animate-pulse")).not.toBeNull();
  });

  it("AC-02/AC-03 — cards render while covers sign, then each cover appears in its card", async () => {
    let finishSigning!: (value: { data: { path: string; signedUrl: string }[] }) => void;
    mockCreateSignedUrls.mockReturnValueOnce(new Promise(resolve => { finishSigning = resolve; }));
    mockSelect.mockResolvedValueOnce({ data: [
      makeJob({ id: "j1", title: "Dragon Book", pages: [{ scene_id: "s1", caption: "c", image_path: "j1/p1.png" }] }),
      makeJob({ id: "j2", title: "Robot Book", pages: [{ scene_id: "s1", caption: "c", image_path: "j2/p1.png" }] }),
    ] });
    const { container } = render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText("Dragon Book")).toBeVisible());
    await waitFor(() => expect(screen.getByText("Robot Book")).toBeVisible());
    expect(container.querySelectorAll("img")).toHaveLength(0);
    const dragonLink = screen.getByRole("link", { name: "Dragon Book" });
    expect(dragonLink).toHaveAttribute("href", `/s/${PROFILE_ID}/book/j1`);
    expect(dragonLink.querySelector(".animate-pulse.bg-muted\\/50")).not.toBeNull();

    await act(async () => {
      finishSigning({ data: [
        { path: "j1/p1.png", signedUrl: "https://cdn.test/j1.png" },
        { path: "j2/p1.png", signedUrl: "https://cdn.test/j2.png" },
      ] });
    });
    await waitFor(() => expect(dragonLink.querySelector("img")).toHaveAttribute("src", "https://cdn.test/j1.png"));
    expect(dragonLink.querySelector("img")).toHaveAttribute("alt", "");
    expect(screen.getByRole("link", { name: "Robot Book" }).querySelector("img"))
      .toHaveAttribute("src", "https://cdn.test/j2.png");
  });

  it("AC-09 — a finished book with no first-page image or no signed cover shows the book icon, not '?'", async () => {
    mockSelect.mockResolvedValueOnce({ data: [
      makeJob({ id: "j1", title: "No Picture", pages: [{ scene_id: "s1", caption: "c", image_path: "" }] }),
      makeJob({ id: "j2", title: "Unsigned", pages: [{ scene_id: "s1", caption: "c", image_path: "j2/p1.png" }] }),
    ] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(mockCreateSignedUrls).toHaveBeenCalled());
    for (const name of ["No Picture", "Unsigned"]) {
      const link = await screen.findByRole("link", { name });
      await waitFor(() => expect(link.querySelector(".animate-pulse")).toBeNull());
      expect(link.querySelector("img")).toBeNull();
      expect(link.querySelector("svg[aria-hidden='true']")).not.toBeNull();
      expect(link).not.toHaveTextContent("?");
      expect(link.querySelectorAll("a, button")).toHaveLength(0);
    }
  });

  it("aborts the cover download on unmount", async () => {
    mockGetSession.mockResolvedValue({ data: { session: { access_token: "synthetic" } } });
    let coverSignal: AbortSignal | undefined;
    const network = vi.fn((url: string, init?: RequestInit) => {
      if (url.includes("/me/notes")) return Promise.resolve(new Response("[]"));
      coverSignal = init?.signal ?? undefined;
      return new Promise<Response>(() => {});
    });
    vi.stubGlobal("fetch", network);
    mockSelect.mockResolvedValueOnce({ data: [makeJob({
      id: "tr1", title: "Held Book", moderation_mode: "teacher_review_v1",
      pages: [{ scene_id: "s1", caption: "c", image_path: "tr1/p1.png" }],
    })] });
    const view = render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(coverSignal).toBeDefined());
    expect(coverSignal?.aborted).toBe(false);
    view.unmount();
    expect(coverSignal?.aborted).toBe(true);
  });

  it("AC-07/AC-08 — retries only the failed cover in one call, then shows the book icon in a working link", async () => {
    mockCreateSignedUrls
      .mockResolvedValueOnce({ data: [{ path: "j1/p1.png", signedUrl: "https://cdn.test/j1.png" }] })
      .mockResolvedValueOnce({ data: [{ path: "j2/p1.png", signedUrl: null, error: "Object not found" }] });
    mockSelect.mockResolvedValueOnce({ data: [
      makeJob({ id: "j1", title: "Dragon Book", pages: [{ scene_id: "s1", caption: "c", image_path: "j1/p1.png" }] }),
      makeJob({ id: "j2", title: "Robot Book", pages: [{ scene_id: "s1", caption: "c", image_path: "j2/p1.png" }] }),
    ] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    const robot = await screen.findByRole("link", { name: "Robot Book" });
    await waitFor(() => expect(mockCreateSignedUrls).toHaveBeenCalledTimes(2));
    expect(mockCreateSignedUrls.mock.calls[0][0]).toEqual(["j1/p1.png", "j2/p1.png"]);
    expect(mockCreateSignedUrls.mock.calls[1][0]).toEqual(["j2/p1.png"]);
    await waitFor(() => expect(robot.querySelector(".animate-pulse")).toBeNull());
    expect(robot.querySelector("img")).toBeNull();
    expect(robot.querySelector("svg[aria-hidden='true']")).not.toBeNull();
    expect(robot).toHaveAttribute("href", `/s/${PROFILE_ID}/book/j2`);
    expect(robot.querySelectorAll("a, button")).toHaveLength(0);
    expect(screen.getByRole("link", { name: "Dragon Book" }).querySelector("img")).toHaveAttribute("src", "https://cdn.test/j1.png");
  });

  it("AC-10 — an issued cover whose image fails goes straight to the book icon, with no retry", async () => {
    mockCreateSignedUrls.mockResolvedValueOnce({ data: [{ path: "j1/p1.png", signedUrl: "https://cdn.test/j1.png" }] });
    mockSelect.mockResolvedValueOnce({ data: [makeJob({ id: "j1", title: "Dragon Book", pages: [{ scene_id: "s1", caption: "c", image_path: "j1/p1.png" }] })] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    const link = await screen.findByRole("link", { name: "Dragon Book" });
    await waitFor(() => expect(link.querySelector("img")).not.toBeNull());
    fireEvent.error(link.querySelector("img")!);
    await waitFor(() => expect(link.querySelector("img")).toBeNull());
    expect(link.querySelector(".animate-pulse")).toBeNull();
    expect(link.querySelector("svg[aria-hidden='true']")).not.toBeNull();
    expect(mockCreateSignedUrls).toHaveBeenCalledTimes(1);
  });

  describe("AC-05 — a book that finishes while the shelf is open", () => {
    const finished = (pageId: string) => ({ ...makeJob({
      id: "tr1", title: "Held Book", status: "complete", moderation_mode: "teacher_review_v1",
      pages: [{ scene_id: pageId, caption: "c", image_path: `tr1/${pageId}.png` }],
    }) });

    async function renderInFlight() {
      mockSelect.mockResolvedValueOnce({ data: [makeJob({
        id: "tr1", title: "Held Book", status: "running", moderation_mode: "teacher_review_v1", pages: [],
      })] });
      const view = render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
      await screen.findByText("Writing...");
      return view;
    }

    it("loads its cover from the updated row through the picture endpoint, pulsing first", async () => {
      const pictures = stubPictures();
      await renderInFlight();
      act(() => realtime.emit({ new: finished("s1") }));
      const link = await screen.findByRole("link", { name: "Held Book" });
      expect(link).toHaveAttribute("href", `/s/${PROFILE_ID}/book/tr1`);
      expect(link.querySelector(".animate-pulse.bg-muted\\/50")).not.toBeNull();
      await waitFor(() => expect(pictures).toHaveLength(1));
      expect(pictures[0].url).toContain("/jobs/tr1/images/scene-s1");
      expect(mockCreateSignedUrls).not.toHaveBeenCalled();
      await act(async () => { pictures[0].finish(new Response("png")); });
      await waitFor(() => expect(link.querySelector("img")).toHaveAttribute("src", "blob:synthetic-1"));
    });

    it("aborts a superseded cover request and the latest one on unmount", async () => {
      const pictures = stubPictures();
      const view = await renderInFlight();
      act(() => realtime.emit({ new: finished("s1") }));
      await waitFor(() => expect(pictures).toHaveLength(1));
      act(() => realtime.emit({ new: finished("s2") }));
      await waitFor(() => expect(pictures).toHaveLength(2));
      expect(pictures[0].signal.aborted).toBe(true);
      expect(pictures[1].signal.aborted).toBe(false);
      view.unmount();
      expect(pictures[1].signal.aborted).toBe(true);
    });

    it("keeps the shown cover when a finished book gets another UPDATE with the same cover", async () => {
      const pictures = stubPictures();
      mockSelect.mockResolvedValueOnce({ data: [finished("s1")] });
      render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
      await waitFor(() => expect(pictures).toHaveLength(1));
      await act(async () => { pictures[0].finish(new Response("png")); });
      const link = screen.getByRole("link", { name: "Held Book" });
      await waitFor(() => expect(link.querySelector("img")).toHaveAttribute("src", "blob:synthetic-1"));
      fireEvent.load(link.querySelector("img")!);
      expect(link.querySelector(".animate-pulse")).toBeNull();

      await act(async () => realtime.emit({ new: finished("s1") }));

      expect(link.querySelector("img")).toHaveAttribute("src", "blob:synthetic-1");
      expect(link.querySelector(".animate-pulse")).toBeNull();
      expect(pictures).toHaveLength(1);
    });

    it("a first-load cover finishing after a Realtime cover does not replace it", async () => {
      const pictures = stubPictures();
      mockSelect.mockResolvedValueOnce({ data: [finished("s1")] });
      render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
      await waitFor(() => expect(pictures).toHaveLength(1));
      act(() => realtime.emit({ new: finished("s2") }));
      await waitFor(() => expect(pictures).toHaveLength(2));
      await act(async () => { pictures[1].finish(new Response("png")); });
      const link = screen.getByRole("link", { name: "Held Book" });
      await waitFor(() => expect(link.querySelector("img")).toHaveAttribute("src", "blob:synthetic-1"));

      await act(async () => { pictures[0].finish(new Response("png")); });
      await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalledTimes(2));

      expect(link.querySelector("img")).toHaveAttribute("src", "blob:synthetic-1");
    });
  });

  it("shows empty state when no jobs", async () => {
    mockSelect.mockResolvedValueOnce({ data: [] });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    await waitFor(() => expect(screen.getByText(/your shelf is empty/i)).toBeDefined());
  });

  it("AC-06 — a failed book list read says so and Try again reads the list again", async () => {
    mockSelect.mockResolvedValueOnce({ data: null, error: { message: "network" } });
    render(<BookshelfPage params={Promise.resolve({ profileId: PROFILE_ID })} />);
    const retry = await screen.findByRole("button", { name: "Try again" });
    expect(screen.getByRole("alert")).toHaveTextContent("We couldn't open your bookshelf");
    expect(screen.queryByText(/your shelf is empty/i)).toBeNull();

    let finishList!: (r: unknown) => void;
    mockSelect.mockReturnValueOnce(new Promise(resolve => { finishList = resolve; }));
    fireEvent.click(retry);
    expect(await screen.findByText("Loading your bookshelf")).toBeInTheDocument();
    await act(async () => finishList({ data: [makeJob({ title: "Space Cats" })] }));
    expect(await screen.findByText("Space Cats")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).toBeNull();
    expect(mockSelect).toHaveBeenCalledTimes(2);
  });
});
