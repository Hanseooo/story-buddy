import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AdjudicatePage from "./page";
import * as actions from "./actions";

vi.mock("./actions", () => ({
  getConflictedPair: vi.fn(),
  submitAdjudication: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("AdjudicatePage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("offers a demo and a way back when the live queue is empty", async () => {
    vi.mocked(actions.getConflictedPair).mockResolvedValueOnce({ pair: null });

    render(await AdjudicatePage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByText("All Conflicts Adjudicated")).toBeInTheDocument();
    expect(screen.getByText("No conflicted pairs pending adjudication found.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /try adjudication demo/i })).toHaveAttribute(
      "href",
      "/adjudicate?demo=1",
    );
    expect(screen.getByRole("link", { name: /back to research lab/i })).toHaveAttribute(
      "href",
      "/research",
    );
    const logout = screen.getByRole("button", { name: /log out/i });
    expect(logout.closest("form")).toHaveAttribute("action", "/auth/signout");
    expect(logout.closest("form")).toHaveAttribute("method", "post");
  });

  it("renders the actual adjudicator in demo mode without reading the live queue", async () => {
    render(await AdjudicatePage({ searchParams: Promise.resolve({ demo: "1" }) }));

    expect(screen.getByText(/demo · synthetic samples · nothing is saved/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /example 1 of 2/i })).toBeInTheDocument();
    expect(screen.getByText(/illustrative disagreement/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit demo decision/i })).toBeInTheDocument();
    expect(actions.getConflictedPair).not.toHaveBeenCalled();
    expect(actions.submitAdjudication).not.toHaveBeenCalled();
  });

  it("does not treat another query value as demo mode", async () => {
    vi.mocked(actions.getConflictedPair).mockResolvedValueOnce({ pair: null });

    render(await AdjudicatePage({ searchParams: Promise.resolve({ demo: "true" }) }));

    expect(screen.getByText("All Conflicts Adjudicated")).toBeInTheDocument();
    expect(actions.getConflictedPair).toHaveBeenCalledOnce();
  });

  it("does not treat a repeated query value as demo mode", async () => {
    vi.mocked(actions.getConflictedPair).mockResolvedValueOnce({ pair: null });

    render(await AdjudicatePage({ searchParams: Promise.resolve({ demo: ["1", "1"] }) }));

    expect(screen.getByText("All Conflicts Adjudicated")).toBeInTheDocument();
    expect(actions.getConflictedPair).toHaveBeenCalledOnce();
  });

  it("shows a queue error as an error and offers no demo in its place", async () => {
    vi.mocked(actions.getConflictedPair).mockResolvedValueOnce({ error: "Failed to load adjudication queue" });

    render(await AdjudicatePage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("heading", { name: "Error" })).toBeInTheDocument();
    expect(screen.getByText("Failed to load adjudication queue")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /demo/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to research lab/i })).toHaveAttribute("href", "/research");
  });

  it("passes live conflicts to the real adjudicator", async () => {
    vi.mocked(actions.getConflictedPair).mockResolvedValueOnce({
      pair: {
        id: "live-conflict",
        canonical_signed_url: "/reference.webp",
        scene_signed_url: "/scene.webp",
      },
      annotationA: {
        same_character: true,
        failure_reasons: [],
        anatomy_intact: true,
        text_free: true,
      },
      annotationB: {
        same_character: false,
        failure_reasons: ["different_face"],
        anatomy_intact: true,
        text_free: true,
      },
    });

    render(await AdjudicatePage({ searchParams: Promise.resolve({}) }));

    expect(screen.getByRole("heading", { name: "Authoritative Label" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /submit final decision/i })).toBeInTheDocument();
    expect(screen.queryByText(/nothing is saved/i)).not.toBeInTheDocument();
  });
});
