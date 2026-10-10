import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResultsPage from "./page";

describe("/research/results", () => {
  it("says the result is partial", () => {
    render(<ResultsPage />);

    expect(screen.getByText(/This is a partial result/)).toBeInTheDocument();
  });

  it("gives the preselected seed its row in the results table", () => {
    render(<ResultsPage />);

    const table = screen.getByRole("table", { name: /results of the four judges/i });
    const seed1 = within(table).getByRole("row", { name: /Trained, seed 1 \(picked in advance\)/ });
    expect(within(seed1).getByText("0.310")).toBeInTheDocument();
    expect(within(seed1).getByText("9")).toBeInTheDocument();
  });

  it("states among the limits that selection rested on four Different validation pairs", () => {
    render(<ResultsPage />);

    const limits = screen.getByRole("region", { name: /what this does and does not show/i });
    expect(within(limits).getByText(/4 Different pairs out of 86/)).toBeInTheDocument();
  });

  it("lists the training settings with their values", () => {
    render(<ResultsPage />);

    const table = screen.getByRole("table", { name: /training settings/i });
    const epochs = within(table).getByRole("row", { name: /num_train_epochs/ });
    expect(within(epochs).getByText("3.0")).toBeInTheDocument();
    expect(within(table).getAllByRole("row")).toHaveLength(14);
  });

  it("gives four explanations and says none was tested", () => {
    render(<ResultsPage />);

    const reading = screen.getByRole("region", { name: /what we take from this/i });
    expect(within(reading).getByRole("heading", { name: /why it happened is not known/i })).toBeInTheDocument();
    const untested = within(reading).getByRole("list", { name: /explanations that were not tested/i });
    expect(within(untested).getAllByRole("listitem")).toHaveLength(4);
    expect(within(reading).getByText(/keeps its prompted Gemma judge/)).toBeInTheDocument();
  });

  it("opens the runbook on GitHub in a new tab", () => {
    render(<ResultsPage />);

    const runbook = screen.getAllByRole("link", { name: /research_runbook\.md/ })[0];
    expect(runbook).toHaveAttribute(
      "href",
      "https://github.com/Hanseooo/story-buddy/blob/main/docs/capstone/research_runbook.md"
    );
    expect(runbook).toHaveAttribute("target", "_blank");
    expect(runbook).toHaveAttribute("rel", "noopener noreferrer");
    expect(runbook).toHaveAccessibleName(/opens on GitHub in a new tab/);
  });

  // ADR-066 decision 9: no donated story or character id, in the text or in a link.
  it("names no donated story", () => {
    const { container } = render(<ResultsPage />);

    expect(container.innerHTML).not.toMatch(/don-/i);
  });
});
