import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

const mockCreateSignedUrls = vi.fn();
const mockSession = vi.fn();
vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: { getSession: () => mockSession() },
    storage: { from: () => ({ createSignedUrls: (...a: unknown[]) => mockCreateSignedUrls(...a) }) },
  },
}));

import { signPaths } from "./signedUrls";

beforeEach(() => {
  sessionStorage.clear();
  mockCreateSignedUrls.mockReset();
});

describe("signPaths", () => {
  // ADR-086: teacher-review pictures come as backend-signed links, one /image-links call per job.
  describe("teacher-review links (ADR-086)", () => {
    const link = (asset_id: string, path: string) => ({asset_id, path, url: `https://cdn/${path}?token=t`});
    const reply = (...links: unknown[]) => new Response(JSON.stringify({links}), {status: 200});
    const twoJobs = [
      {id: "j", moderation_mode: "teacher_review_v1", pages: [{scene_id: "s0", image_path: "j/s0.png"}, {scene_id: "s1", image_path: "j/s1.png"}]},
      {id: "k", moderation_mode: "teacher_review_v1", pages: [{scene_id: "s0", image_path: "k/s0.png"}]},
    ];
    const flush = async () => { for (let i = 0; i < 10; i++) await Promise.resolve(); };
    beforeEach(() => { mockSession.mockReset(); mockSession.mockResolvedValue({data: {session: {access_token: "test-token"}}}); });
    afterEach(() => { vi.restoreAllMocks(); });

    it("asks once per job for the requested assets and returns the signed links, then reuses them", async () => {
      sessionStorage.setItem("sb:signed", JSON.stringify({"k/s0.png": {url: "https://cdn/cached-k", exp: Date.now() + 100000}}));
      const fetchMock = vi.spyOn(global, "fetch").mockImplementation(async () => reply(link("scene-s0", "j/s0.png"), link("scene-s1", "j/s1.png")));
      const urls = await signPaths(["j/s0.png", "j/s1.png", "k/s0.png"], twoJobs, new AbortController().signal);
      expect(urls).toEqual({"j/s0.png": "https://cdn/j/s0.png?token=t", "j/s1.png": "https://cdn/j/s1.png?token=t", "k/s0.png": "https://cdn/cached-k"});
      expect(mockCreateSignedUrls).not.toHaveBeenCalled();
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/jobs\/j\/image-links\?asset=scene-s0&asset=scene-s1$/),
        expect.objectContaining({headers: {Authorization: "Bearer test-token"}}));

      fetchMock.mockClear();
      expect(await signPaths(["j/s0.png", "j/s1.png"], twoJobs, new AbortController().signal)).toEqual({
        "j/s0.png": "https://cdn/j/s0.png?token=t", "j/s1.png": "https://cdn/j/s1.png?token=t"});
      expect(fetchMock).not.toHaveBeenCalled();
    });

    it("a kept version is asked for by its own asset id, never as the current reference", async () => {
      const fetchMock = vi.spyOn(global, "fetch").mockImplementation(async () => reply());
      await signPaths(["j/ref-c0-1.png"], [{id: "j", moderation_mode: "teacher_review_v1", reveal: {characters: [
        {char_id: "c0", image_path: "j/ref-c0-2.png", versions: [{version_id: "ref-c0-1", image_path: "j/ref-c0-1.png"}]},
      ]}}], new AbortController().signal);
      expect(fetchMock).toHaveBeenCalledWith(expect.stringMatching(/\/jobs\/j\/image-links\?asset=version-ref-c0-1$/), expect.anything());
      expect(mockCreateSignedUrls).not.toHaveBeenCalled();
    });

    it("leaves out a failed job and any link for a path it did not ask for", async () => {
      vi.spyOn(global, "fetch").mockImplementation(async (url) => String(url).includes("/jobs/k/")
        ? new Response("server error", {status: 500})
        : reply(link("scene-s0", "j/s0.png"), link("scene-s1", "j/other.png")));
      const urls = await signPaths(["j/s0.png", "j/s1.png", "k/s0.png"], twoJobs, new AbortController().signal);
      expect(urls).toEqual({"j/s0.png": "https://cdn/j/s0.png?token=t"});
      expect(sessionStorage.getItem("sb:signed") ?? "").not.toContain("j/other.png");
    });

    it("reads the session once per call, and leaves every picture out without one", async () => {
      const fetchMock = vi.spyOn(global, "fetch").mockImplementation(async () => reply());
      await signPaths(["j/s0.png", "k/s0.png"], twoJobs, new AbortController().signal);
      expect(mockSession).toHaveBeenCalledTimes(1);
      expect(fetchMock).toHaveBeenCalledTimes(2);

      fetchMock.mockClear();
      mockSession.mockResolvedValue({data: {session: null}});
      expect(await signPaths(["j/s0.png"], twoJobs, new AbortController().signal)).toEqual({});
      expect(fetchMock).not.toHaveBeenCalled();
    });

    it("hands nothing out and caches nothing for links that arrive after the abort", async () => {
      let release!: (r: Response) => void;
      vi.spyOn(global, "fetch").mockImplementation(() => new Promise<Response>(resolve => { release = resolve; }));
      const onUrl = vi.fn();
      const controller = new AbortController();
      const pending = signPaths(["j/s0.png"], twoJobs, controller.signal, onUrl);
      await flush();
      controller.abort();
      release(reply(link("scene-s0", "j/s0.png")));
      expect(await pending).toEqual({});
      expect(onUrl).not.toHaveBeenCalled();
      expect(sessionStorage.getItem("sb:signed") ?? "").not.toContain("j/s0.png");
    });

    it("hands each URL to onUrl as it arrives, before the call resolves", async () => {
      sessionStorage.setItem("sb:signed", JSON.stringify({"cached.png": {url: "https://cdn/cached", exp: Date.now() + 100000}}));
      mockCreateSignedUrls.mockResolvedValue({data: [{path: "fresh.png", signedUrl: "https://cdn/fresh", error: null}], error: null});
      let release!: (r: Response) => void;
      vi.spyOn(global, "fetch").mockImplementation(async (url) => String(url).includes("/jobs/k/")
        ? new Promise<Response>(resolve => { release = resolve; })
        : reply(link("scene-s0", "j/s0.png")));
      const onUrl = vi.fn();
      let settled = false;
      const pending = signPaths(["cached.png", "j/s0.png", "k/s0.png", "fresh.png"], twoJobs, new AbortController().signal, onUrl)
        .then(urls => { settled = true; return urls; });
      await flush();
      expect(settled).toBe(false);
      // The baseline link and one book's links do not wait for another book (mixed shelf, journey 1).
      expect(new Map(onUrl.mock.calls)).toEqual(new Map([
        ["cached.png", "https://cdn/cached"], ["j/s0.png", "https://cdn/j/s0.png?token=t"], ["fresh.png", "https://cdn/fresh"],
      ]));
      release(reply(link("scene-s0", "k/s0.png")));
      await pending;
      expect(onUrl).toHaveBeenLastCalledWith("k/s0.png", "https://cdn/k/s0.png?token=t");
    });
  });


  it("returns a path -> url map", async () => {
    mockCreateSignedUrls.mockResolvedValue({
      data: [{ path: "a.png", signedUrl: "https://cdn/a?token=1", error: null }],
      error: null,
    });
    expect(await signPaths(["a.png"])).toEqual({ "a.png": "https://cdn/a?token=1" });
  });

  it("reuses a cached URL instead of re-signing — the whole point of the cache", async () => {
    mockCreateSignedUrls.mockResolvedValue({
      data: [{ path: "a.png", signedUrl: "https://cdn/a?token=1", error: null }],
      error: null,
    });
    await signPaths(["a.png"]);
    const second = await signPaths(["a.png"]);

    expect(mockCreateSignedUrls).toHaveBeenCalledTimes(1);
    // Same URL, so the browser can serve the image from its own cache.
    expect(second["a.png"]).toBe("https://cdn/a?token=1");
  });

  it("signs only the uncached paths", async () => {
    mockCreateSignedUrls.mockResolvedValueOnce({
      data: [{ path: "a.png", signedUrl: "https://cdn/a", error: null }],
      error: null,
    });
    await signPaths(["a.png"]);

    mockCreateSignedUrls.mockResolvedValueOnce({
      data: [{ path: "b.png", signedUrl: "https://cdn/b", error: null }],
      error: null,
    });
    const out = await signPaths(["a.png", "b.png"]);

    expect(mockCreateSignedUrls).toHaveBeenLastCalledWith(["b.png"], 3600);
    expect(out).toEqual({ "a.png": "https://cdn/a", "b.png": "https://cdn/b" });
  });

  it("re-signs once the cached entry has expired", async () => {
    mockCreateSignedUrls.mockResolvedValue({
      data: [{ path: "a.png", signedUrl: "https://cdn/a", error: null }],
      error: null,
    });
    await signPaths(["a.png"]);

    vi.spyOn(Date, "now").mockReturnValue(Date.now() + 3600_000);
    await signPaths(["a.png"]);
    expect(mockCreateSignedUrls).toHaveBeenCalledTimes(2);
    vi.mocked(Date.now).mockRestore();
  });

  it("omits paths that failed to sign, and does not cache them", async () => {
    mockCreateSignedUrls.mockResolvedValue({
      data: [
        { path: "a.png", signedUrl: "https://cdn/a", error: null },
        { path: "b.png", signedUrl: null, error: "nope" },
      ],
      error: null,
    });
    const out = await signPaths(["a.png", "b.png"]);
    expect(out).toEqual({ "a.png": "https://cdn/a" });

    mockCreateSignedUrls.mockResolvedValue({
      data: [{ path: "b.png", signedUrl: "https://cdn/b", error: null }],
      error: null,
    });
    await signPaths(["a.png", "b.png"]);
    expect(mockCreateSignedUrls).toHaveBeenLastCalledWith(["b.png"], 3600);
  });

  it("survives a null data payload without throwing", async () => {
    mockCreateSignedUrls.mockResolvedValue({ data: null, error: new Error("network") });
    expect(await signPaths(["a.png"])).toEqual({});
  });

  it("deduplicates repeated paths in one request", async () => {
    mockCreateSignedUrls.mockResolvedValue({
      data: [{ path: "a.png", signedUrl: "https://cdn/a", error: null }],
      error: null,
    });
    await signPaths(["a.png", "a.png"]);
    expect(mockCreateSignedUrls).toHaveBeenCalledWith(["a.png"], 3600);
  });
});
