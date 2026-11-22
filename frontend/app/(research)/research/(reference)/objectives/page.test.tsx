import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ObjectivesPage from "./page";

const GITHUB = "https://github.com/Hanseooo/story-buddy/blob/main/";

function objective(n: number) {
  return screen.getByRole("heading", { level: 2, name: `Objective ${n}` }).closest("article") as HTMLElement;
}

describe("/research/objectives", () => {
  it("lists the five objectives in the manuscript's order, each with Answer and Explained on", () => {
    render(<ObjectivesPage />);

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Objectives and answers");
    expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual([
      "Objective 1",
      "Objective 2",
      "Objective 3",
      "Objective 4",
      "Objective 5",
    ]);
    for (let n = 1; n <= 5; n++) {
      expect(within(objective(n)).getByText("Answer")).toBeInTheDocument();
      expect(within(objective(n)).getByText("Explained on")).toBeInTheDocument();
    }
    expect(objective(1)).toHaveTextContent("Implement an orchestrated AI pipeline as the core processing framework of StoryBuddy.");
  });

  it("Objective 1: Achieved, with the graph as evidence and the pipeline page, and no Tool A", () => {
    const { container } = render(<ObjectivesPage />);

    expect(objective(1)).toHaveTextContent("Achieved.");
    expect(objective(1)).toHaveTextContent("a LangGraph graph of 14 nodes (11 in baseline mode)");
    expect(within(objective(1)).getByRole("link", { name: /backend\/pipeline\/graph\.py/ })).toHaveAttribute("href", `${GITHUB}backend/pipeline/graph.py`);
    expect(within(objective(1)).getByRole("link", { name: "Conceptual framework and pipeline" })).toHaveAttribute("href", "/research/pipeline");
    expect(container.textContent).not.toMatch(/Tool A/);
  });

  it("Objective 2: 42 books, 30 synthetic and 12 donated, and the three that did not finish", () => {
    render(<ObjectivesPage />);

    const o = objective(2);
    expect(o).toHaveTextContent("42 digital picture books were produced through the pipeline: 30 from synthetic stories and 12 from donated stories.");
    expect(o).toHaveTextContent("Fifteen donated stories were collected and twelve were generated into books.");
    expect(o).toHaveTextContent("did not finish (two invalid_terminal, one budget_stopped)");
    expect(o).not.toHaveTextContent(/backup stories/i);
  });

  it("Objectives 3 and 5 say Survey pending and nothing else in their answer", () => {
    render(<ObjectivesPage />);

    for (const n of [3, 5]) {
      const answer = within(objective(n)).getByText("Answer").parentElement as HTMLElement;
      expect(answer).toHaveTextContent(/^AnswerSurvey pending$/);
      expect(within(objective(n)).queryByText("Evidence")).toBeNull();
      expect(within(objective(n)).getByRole("link", { name: "Evaluation instruments" })).toHaveAttribute("href", "/research/instruments");
    }
  });

  it("Objective 4: the F1 result, the tradeoff sentence, the partial note and a link to the results page", () => {
    render(<ObjectivesPage />);

    const o = objective(4);
    expect(o).toHaveTextContent("The fine-tuned judge did not beat its untrained base on F1 (0.31 vs 0.47).");
    expect(o).toHaveTextContent(
      "The fine-tuned judge raises far fewer false alarms (2 vs 47) because it rarely says 'different' at all. As a result it misses most real character changes (38 of 47 vs 18 of 47), and 12% of its answers could not be read. On the main score, F1, it is worse (0.31 vs 0.47)."
    );
    expect(o).toHaveTextContent("The comparison is partial.");
    expect(within(o).getByRole("link", { name: "Character-consistency results" })).toHaveAttribute("href", "/research/results");
    expect(within(o).getAllByRole("link", { name: /\.md/ }).length).toBeGreaterThanOrEqual(2);
  });
});
