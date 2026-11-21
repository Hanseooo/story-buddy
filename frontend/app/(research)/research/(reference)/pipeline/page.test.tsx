import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PipelinePage from "./page";

describe("/research/pipeline", () => {
  it("shows both figures with alt text, an As-of caption, a PNG download and a GitHub source", () => {
    render(<PipelinePage />);

    for (const [id, file, source] of [
      ["ipo-model", "ipo_model.png", "ipo_model.drawio.svg"],
      ["langgraph-pipeline", "langgraph_pipeline_after_2026-10.png", "langgraph_pipeline_after_2026-10.drawio.svg"],
    ]) {
      const figure = document.getElementById(id) as HTMLElement;
      expect(figure, id).not.toBeNull();
      expect(within(figure).getByRole("img").getAttribute("alt")).toMatch(/^\S+(\s+\S+){7,}/);
      expect(within(figure).getByText("As of 2026-11-21")).toBeInTheDocument();
      expect(within(figure).getByRole("link", { name: `Download ${file}` })).toHaveAttribute("href", `/research/diagrams/${file}`);
      expect(within(figure).getByRole("link", { name: new RegExp(source) }).getAttribute("href")).toContain(`docs/diagrams/drawio/${source}`);
    }
  });

  it("lists all 14 nodes on first render with their modes", () => {
    const { container } = render(<PipelinePage />);

    expect(container.querySelectorAll("[data-node]")).toHaveLength(14);
    expect(container.querySelectorAll('[data-node][data-mode="both"]')).toHaveLength(11);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(/pipeline/i);
  });

  it("says the prompt optimizer is not a graph node", () => {
    render(<PipelinePage />);

    const table = screen.getByRole("table", { name: /paper.s modules/i });
    const row = within(table).getByRole("row", { name: /Prompt Optimizer/ });
    expect(within(row).getByText(/not a graph node/i)).toBeInTheDocument();
    expect(within(table).getAllByRole("row")).toHaveLength(11);
  });

  it("gives the caps with their source lines", () => {
    render(<PipelinePage />);

    const table = screen.getByRole("table", { name: /limits the pipeline enforces/i });
    expect(within(table).getByRole("row", { name: /Most pages.*10/ })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /Fewest pages.*3/ })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /Drawing attempts per page.*3/ })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /Try again.*3/ })).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /Words in a story.*500.*300/ })).toBeInTheDocument();
  });

  it("says what a failed check does in each mode, and the reveal features", () => {
    render(<PipelinePage />);

    expect(screen.getByText(/no partial book is made/i)).toBeInTheDocument();
    expect(screen.getByText(/held for the teacher/i)).toBeInTheDocument();
    expect(screen.getAllByText(/magic pencil/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/other versions/i).length).toBeGreaterThan(0);
  });
});
