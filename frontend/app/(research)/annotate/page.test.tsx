import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AnnotatePage from "./page";
import * as actions from "./actions";

vi.mock("./actions", () => ({
  getNextPair: vi.fn(),
}));

vi.mock("./AnnotationClient", () => ({
  default: () => null,
}));

describe("AnnotatePage", () => {
  it("offers logout instead of the methodology page when the queue is complete", async () => {
    vi.mocked(actions.getNextPair).mockResolvedValueOnce({ pair: null });

    render(await AnnotatePage());

    const logoutButton = screen.getByRole("button", { name: /log out/i });
    expect(logoutButton.closest("form")).toHaveAttribute("action", "/auth/signout");
    expect(logoutButton.closest("form")).toHaveAttribute("method", "post");
    expect(screen.queryByRole("link", { name: /back to research lab/i })).not.toBeInTheDocument();
  });
});
