import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import AnnotatePage from "./page";
import * as actions from "./actions";

vi.mock("./actions", () => ({
  getNextPair: vi.fn(),
  submitAnnotation: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("AnnotatePage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("offers a demo, a way back and logout when the live queue is empty", async () => {
    vi.mocked(actions.getNextPair).mockResolvedValueOnce({ pair: null });
    render(await AnnotatePage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("heading", { name: "Queue Complete" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /try annotation demo/i })).toHaveAttribute(
      "href",
      "/annotate?demo=1",
    );
    expect(screen.getByRole("link", { name: /back to research lab/i })).toHaveAttribute("href", "/research");
    expect(actions.getNextPair).toHaveBeenCalledOnce();
    const logout = screen.getByRole("button", { name: /log out/i });
    expect(logout.closest("form")).toHaveAttribute("action", "/auth/signout");
    expect(logout.closest("form")).toHaveAttribute("method", "post");
  });

  it("renders the actual annotation form in demo mode without reading the live queue", async () => {
    const { unmount } = render(await AnnotatePage({ searchParams: Promise.resolve({ demo: "1" }) }));

    expect(screen.getByText(/demo · synthetic samples · nothing is saved/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /example 1 of 2/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /same character/i })).toBeInTheDocument();
    expect(actions.getNextPair).not.toHaveBeenCalled();
    expect(actions.submitAnnotation).not.toHaveBeenCalled();
    unmount();

    vi.mocked(actions.getNextPair).mockResolvedValueOnce({
      pair: {
        id: "live-pair",
        canonical_signed_url: "/reference.webp",
        scene_signed_url: "/scene.webp",
      },
      round: 2,
    });
    render(await AnnotatePage({ searchParams: Promise.resolve({ demo: "0" }) }));
    expect(screen.getByText(/blinded · round 2/i)).toBeInTheDocument();
    expect(screen.queryByText(/nothing is saved/i)).not.toBeInTheDocument();
  });

  it("does not treat repeated or other query values as demo mode", async () => {
    vi.mocked(actions.getNextPair).mockResolvedValue({ pair: null });

    render(await AnnotatePage({ searchParams: Promise.resolve({ demo: ["1", "1"] }) }));
    expect(screen.getByRole("heading", { name: "Queue Complete" })).toBeInTheDocument();
    expect(actions.getNextPair).toHaveBeenCalledOnce();
  });

  it("shows a queue error as an error and offers no demo in its place", async () => {
    vi.mocked(actions.getNextPair).mockResolvedValueOnce({ error: "Failed to load annotation queue" });

    render(await AnnotatePage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("heading", { name: "Error" })).toBeInTheDocument();
    expect(screen.getByText("Failed to load annotation queue")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /demo/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to research lab/i })).toHaveAttribute("href", "/research");
  });
});
