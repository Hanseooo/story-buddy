import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AdjudicatePage from "./page";
import * as actions from "./actions";

vi.mock("./actions", () => ({
  getConflictedPair: vi.fn(),
}));

vi.mock("./AdjudicateClient", () => ({
  default: () => <div data-testid="adjudicate-client">AdjudicateClientMock</div>,
}));

describe("AdjudicatePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state message when no conflicted pairs exist", async () => {
    vi.mocked(actions.getConflictedPair).mockResolvedValueOnce({ pair: null });

    const ui = await AdjudicatePage();
    render(ui);

    expect(screen.getByText("Adjudicate Conflicts")).toBeInTheDocument();
    expect(
      screen.getByText("No conflicted pairs pending adjudication found.")
    ).toBeInTheDocument();
    expect(screen.queryByTestId("adjudicate-client")).not.toBeInTheDocument();
  });

  it("renders AdjudicateClient when conflicted pair and competing annotations are found", async () => {
    vi.mocked(actions.getConflictedPair).mockResolvedValueOnce({
      pair: {
        id: "pair-1",
        canonical_signed_url: "https://signed.url/c",
        scene_signed_url: "https://signed.url/s",
      },
      annotationA: {
        same_character: true,
        failure_reasons: [],
        anatomy_intact: true,
        text_free: true,
      },
      annotationB: {
        same_character: false,
        failure_reasons: ["wrong_colour"],
        anatomy_intact: true,
        text_free: true,
      },
    });

    const ui = await AdjudicatePage();
    render(ui);

    expect(screen.getByText("Adjudicate Conflicts")).toBeInTheDocument();
    expect(screen.getByTestId("adjudicate-client")).toBeInTheDocument();
  });
});
