import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: { getSession: async () => ({ data: { session: { access_token: "test-token" } } }) },
    storage: { from: () => ({ createSignedUrls: vi.fn() }) },
  },
}));

import GuardedCover from "./GuardedCover";

// Ticket 03: the shared picture box, driven through the gallery's guarded cover.
const job = { id: "j", moderation_mode: "teacher_review_v1", pages: [{ scene_id: "s1", image_path: "j/s1.png" }] };
const links = (...urls: string[]) => Response.json({ links: urls.map((url) => ({ asset_id: "scene-s1", path: "j/s1.png", url })) });

beforeEach(() => sessionStorage.clear());
afterEach(() => vi.unstubAllGlobals());

describe("GuardedCover picture box", () => {
  it("shows no picture while the link is coming, then the picture", async () => {
    let answer: (r: Response) => void = () => {};
    const network = vi.fn(() => new Promise<Response>((resolve) => { answer = resolve; }));
    vi.stubGlobal("fetch", network);
    render(<GuardedCover job={job} alt="Cover of book by Kai" />);
    await waitFor(() => expect(network).toHaveBeenCalled());
    expect(screen.queryByRole("img")).toBeNull();
    // A6: a pulse like every other surface, named for assistive tech, not a visible text line.
    expect(screen.getByRole("status", { name: "Loading picture" })).toBeDefined();
    expect(screen.queryByText("Loading picture…")).toBeNull();
    expect(screen.queryByText("Picture didn't load")).toBeNull();
    answer(links("https://cdn.test/j/s1.png?token=first"));
    const img = await screen.findByRole("img", { name: "Cover of book by Kai" });
    fireEvent.load(img);
    expect(img).toHaveAttribute("src", "https://cdn.test/j/s1.png?token=first");
    expect(screen.queryByRole("status", { name: "Loading picture" })).toBeNull();
  });

  it("a broken picture offers Try again, which drops the cached link and shows a new one", async () => {
    const network = vi.fn()
      .mockResolvedValueOnce(links("https://cdn.test/j/s1.png?token=first"))
      .mockResolvedValueOnce(links("https://cdn.test/j/s1.png?token=second"));
    vi.stubGlobal("fetch", network);
    render(<GuardedCover job={job} alt="Cover of book by Kai" />);
    fireEvent.error(await screen.findByRole("img", { name: "Cover of book by Kai" }));
    expect(screen.getByText("Picture didn't load")).toBeDefined();
    expect(screen.queryByRole("img")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByRole("img", { name: "Cover of book by Kai" }))
      .toHaveAttribute("src", "https://cdn.test/j/s1.png?token=second"));
    // The first link was still cached; only an evicted cache asks the backend again.
    expect(network).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Picture didn't load")).toBeNull();
  });

  it("no link shows the failed state instead of loading forever", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ links: [] })));
    render(<GuardedCover job={job} alt="Cover of book by Kai" />);
    expect(await screen.findByText("Picture didn't load")).toBeDefined();
    expect(screen.getByRole("button", { name: "Try again" })).toBeDefined();
    expect(screen.queryByRole("img")).toBeNull();
  });

  it("shows a new server-signed link when the page passes one", () => {
    const baseline = { id: "b", pages: [{ scene_id: "s1", image_path: "b/s1.png" }] };
    const { rerender } = render(<GuardedCover job={baseline} alt="Cover of book by Kai" src="https://cdn.test/b/s1.png?token=first" />);
    rerender(<GuardedCover job={baseline} alt="Cover of book by Kai" src="https://cdn.test/b/s1.png?token=second" />);
    expect(screen.getByRole("img", { name: "Cover of book by Kai" })).toHaveAttribute("src", "https://cdn.test/b/s1.png?token=second");
  });

  it("a book with no cover path says No picture, not an error, and offers no Try again", () => {
    render(<GuardedCover job={{ id: "n", pages: [] }} alt="Cover of book by Kai" />);
    expect(screen.getByText("No picture")).toBeDefined();
    expect(screen.queryByText("Picture didn't load")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
  });
});
