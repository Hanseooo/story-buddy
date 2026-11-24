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
  it("feature pictures use authenticated bytes and revoke their blob on exit", async () => {
    sessionStorage.setItem("sb:signed", JSON.stringify({"j/s0-1.png": {url: "https://old-link", exp: Date.now() + 100000}}));
    mockSession.mockResolvedValue({data: {session: {access_token: "test-token"}}});
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue({ok: true, blob: async () => new Blob(["image"])} as Response);
    const create = vi.fn(() => "blob:feature-image");
    const revoke = vi.fn();
    vi.stubGlobal("URL", Object.assign(URL, {createObjectURL: create, revokeObjectURL: revoke}));
    const controller = new AbortController();
    const urls = await signPaths(["j/s0-1.png"], [{id: "j", moderation_mode: "teacher_review_v1", pages: [
      {scene_id: "s0", image_path: "j/s0-1.png"},
    ]}], controller.signal);
    expect(urls).toEqual({"j/s0-1.png": "blob:feature-image"});
    expect(mockCreateSignedUrls).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/jobs/j/images/scene-s0"), expect.objectContaining({
      cache: "no-store", headers: {Authorization: "Bearer test-token"},
    }));
    controller.abort();
    expect(revoke).toHaveBeenCalledWith("blob:feature-image");
    fetchMock.mockRestore();
  });
  it("a kept version is fetched by its own asset id, never as the current reference", async () => {
    mockSession.mockResolvedValue({data: {session: {access_token: "test-token"}}});
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue({ok: true, blob: async () => new Blob(["image"])} as Response);
    vi.stubGlobal("URL", Object.assign(URL, {createObjectURL: vi.fn(() => "blob:version"), revokeObjectURL: vi.fn()}));
    await signPaths(["j/ref-c0-1.png"], [{id: "j", moderation_mode: "teacher_review_v1", reveal: {characters: [
      {char_id: "c0", image_path: "j/ref-c0-2.png", versions: [{version_id: "ref-c0-1", image_path: "j/ref-c0-1.png"}]},
    ]}}], new AbortController().signal);
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/jobs/j/images/version-ref-c0-1"), expect.anything());
    expect(mockCreateSignedUrls).not.toHaveBeenCalled();
    fetchMock.mockRestore();
  });
  describe("parallel protected fetch (image-loading SH-01, SH-02)", () => {
    const sixPages = [{id: "j", moderation_mode: "teacher_review_v1", pages: ["s0", "s1", "s2", "s3", "s4", "s5"].map(s => (
      {scene_id: s, image_path: `j/${s}.png`}
    ))}];
    const sixPaths = sixPages[0].pages.map(p => p.image_path);
    const flush = async () => { for (let i = 0; i < 10; i++) await Promise.resolve(); };
    const { createObjectURL, revokeObjectURL } = URL;
    beforeEach(() => { mockSession.mockReset(); });
    afterEach(() => {
      vi.restoreAllMocks();
      Object.assign(URL, { createObjectURL, revokeObjectURL });
    });

    it("keeps more than 1 and at most 4 picture requests in flight", async () => {
      mockSession.mockResolvedValue({data: {session: {access_token: "test-token"}}});
      const held: Array<() => void> = [];
      let inFlight = 0;
      let peak = 0;
      vi.spyOn(global, "fetch").mockImplementation(() => {
        inFlight++;
        peak = Math.max(peak, inFlight);
        return new Promise<Response>(resolve => held.push(() => {
          inFlight--;
          resolve({ok: true, blob: async () => new Blob(["image"])} as Response);
        }));
      });
      vi.stubGlobal("URL", Object.assign(URL, {createObjectURL: vi.fn(() => `blob:${Math.random()}`), revokeObjectURL: vi.fn()}));
      const pending = signPaths(sixPaths, sixPages, new AbortController().signal);
      await flush();
      expect(peak).toBeGreaterThan(1);
      expect(peak).toBeLessThanOrEqual(4);
      while (held.length) { held.shift()!(); await flush(); }
      expect(Object.keys(await pending)).toHaveLength(6);
      expect(peak).toBeLessThanOrEqual(4);
    });

    it("reads the session once per call, and leaves every picture out without one", async () => {
      mockSession.mockResolvedValue({data: {session: {access_token: "test-token"}}});
      const fetchMock = vi.spyOn(global, "fetch").mockImplementation(async () => ({ok: true, blob: async () => new Blob(["image"])} as Response));
      vi.stubGlobal("URL", Object.assign(URL, {createObjectURL: vi.fn(() => `blob:${Math.random()}`), revokeObjectURL: vi.fn()}));
      await signPaths(sixPaths, sixPages, new AbortController().signal);
      expect(mockSession).toHaveBeenCalledTimes(1);

      fetchMock.mockClear();
      mockSession.mockResolvedValue({data: {session: null}});
      expect(await signPaths(sixPaths, sixPages, new AbortController().signal)).toEqual({});
      expect(fetchMock).not.toHaveBeenCalled();
    });

    it("leaves out a picture that fails and returns the others", async () => {
      mockSession.mockResolvedValue({data: {session: {access_token: "test-token"}}});
      vi.spyOn(global, "fetch").mockImplementation(async (url) => {
        if (String(url).endsWith("/scene-s1")) return new Response("server error", {status: 500});
        if (String(url).endsWith("/scene-s2")) throw new TypeError("network");
        return {ok: true, blob: async () => new Blob(["image"])} as Response;
      });
      vi.stubGlobal("URL", Object.assign(URL, {createObjectURL: vi.fn(() => `blob:${Math.random()}`), revokeObjectURL: vi.fn()}));
      const urls = await signPaths(sixPaths, sixPages, new AbortController().signal);
      expect(Object.keys(urls).sort()).toEqual(["j/s0.png", "j/s3.png", "j/s4.png", "j/s5.png"]);
      expect(sessionStorage.getItem("sb:signed") ?? "").not.toContain("j/s0.png");
    });

    it("never hands out a blob that arrives after the abort, and revokes the ones it handed out", async () => {
      mockSession.mockResolvedValue({data: {session: {access_token: "test-token"}}});
      let release!: () => void;
      const late = new Promise<void>(resolve => { release = resolve; });
      vi.spyOn(global, "fetch").mockImplementation(async (url) => ({ok: true, blob: async () => {
        if (String(url).endsWith("/scene-s1")) await late;
        return new Blob(["image"]);
      }} as Response));
      let n = 0;
      const create = vi.fn(() => `blob:${++n}`);
      const revoke = vi.fn();
      vi.stubGlobal("URL", Object.assign(URL, {createObjectURL: create, revokeObjectURL: revoke}));
      const controller = new AbortController();
      const pending = signPaths(["j/s0.png", "j/s1.png"], sixPages, controller.signal);
      await flush();
      controller.abort();
      release();
      const urls = await pending;
      expect(urls["j/s1.png"]).toBeUndefined();
      expect(create.mock.results.map(r => r.value).sort()).toEqual(revoke.mock.calls.map(([u]) => u).sort());
      expect(revoke).toHaveBeenCalledWith(urls["j/s0.png"]);
    });
    it("hands each URL to onUrl as it arrives, before the call resolves", async () => {
      sessionStorage.setItem("sb:signed", JSON.stringify({"cached.png": {url: "https://cdn/cached", exp: Date.now() + 100000}}));
      mockSession.mockResolvedValue({data: {session: {access_token: "test-token"}}});
      mockCreateSignedUrls.mockResolvedValue({data: [{path: "fresh.png", signedUrl: "https://cdn/fresh", error: null}], error: null});
      let release!: (r: Response) => void;
      vi.spyOn(global, "fetch").mockImplementation(async (url) => String(url).endsWith("/scene-s1")
        ? new Promise<Response>(resolve => { release = resolve; })
        : ({ok: true, blob: async () => new Blob(["image"])} as Response));
      let n = 0;
      vi.stubGlobal("URL", Object.assign(URL, {createObjectURL: vi.fn(() => `blob:${++n}`), revokeObjectURL: vi.fn()}));
      const onUrl = vi.fn();
      let settled = false;
      const pending = signPaths(["cached.png", "j/s0.png", "j/s1.png", "fresh.png"], sixPages, new AbortController().signal, onUrl)
        .then(urls => { settled = true; return urls; });
      await flush();
      expect(settled).toBe(false);
      expect(onUrl.mock.calls).toEqual([["cached.png", "https://cdn/cached"], ["j/s0.png", "blob:1"]]);
      release({ok: true, blob: async () => new Blob(["image"])} as Response);
      await pending;
      expect(onUrl.mock.calls).toEqual([
        ["cached.png", "https://cdn/cached"], ["j/s0.png", "blob:1"], ["j/s1.png", "blob:2"], ["fresh.png", "https://cdn/fresh"],
      ]);
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
