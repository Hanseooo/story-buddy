import { describe, it, expect, vi, beforeEach } from "vitest";

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
