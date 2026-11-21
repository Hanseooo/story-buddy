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

  it("opens with a how-to-read box that defines the terms in this project's sense", () => {
    render(<ResultsPage />);

    const box = screen.getByRole("region", { name: /how to read this page/i });
    for (const term of ["Catch", "Miss", "False alarm", "Precision", "Recall", "F1"]) {
      expect(within(box).getByText(new RegExp(`^${term}`)), term).toBeInTheDocument();
    }
    expect(within(box).getByText(/reaches the child/)).toBeInTheDocument();
    expect(within(box).getByText(/unneeded redraw/)).toBeInTheDocument();
  });

  it("states the false-alarm tradeoff verbatim", () => {
    render(<ResultsPage />);

    const scores = screen.getByRole("region", { name: /what the scores show/i });
    expect(
      within(scores).getByText(
        "The fine-tuned judge raises far fewer false alarms (2 vs 47) because it rarely says 'different' at all. As a result it misses most real character changes (38 of 47 vs 18 of 47), and 12% of its answers could not be read. On the main score, F1, it is worse (0.31 vs 0.47)."
      )
    ).toBeInTheDocument();
    expect(screen.queryByText(/more careful/i)).not.toBeInTheDocument();
  });

  it("gives accuracy beside the answer-Same baseline and says why it is not the headline", () => {
    render(<ResultsPage />);

    const table = screen.getByRole("table", { name: /accuracy of the judges and of always answering same/i });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(6);
    expect(within(rows[1]).getByRole("rowheader")).toHaveTextContent("Always answering Same");
    expect(within(rows[1]).getByText("282 / 329 = 85.7%")).toBeInTheDocument();
    expect(screen.getByText(/accuracy is not the main measure/i)).toBeInTheDocument();
  });

  it("explains McNemar in words without calling seed 1 the better detector", () => {
    render(<ResultsPage />);

    const comparison = screen.getByRole("region", { name: /seed 1 against the untrained model/i });
    expect(within(comparison).getByText(/which judge was right on more pairs/)).toBeInTheDocument();
    expect(within(comparison).getByText(/wrong on fewer pairs \(40 vs 65\)/)).toBeInTheDocument();
    expect(within(comparison).getByText(/just reaches zero/)).toBeInTheDocument();
  });

  it("says the comparison is partial and that Gemma was not scored", () => {
    render(<ResultsPage />);

    const limits = screen.getByRole("region", { name: /what this does and does not show/i });
    expect(within(limits).getByText(/The comparison is partial/)).toBeInTheDocument();
    expect(within(limits).getByText(/failed authentication/)).toBeInTheDocument();
    expect(within(limits).getByText(/No claim-ladder or product-gate decision was made/)).toBeInTheDocument();
  });

  it("says unreadable answers may lower recall and were not counted by class", () => {
    render(<ResultsPage />);

    const unreadable = screen.getByRole("region", { name: /unreadable answers/i });
    expect(within(unreadable).getByText(/may lower their recall/)).toBeInTheDocument();
    expect(within(unreadable).getByText(/was not counted/)).toBeInTheDocument();
    expect(screen.queryByText(/part of why their recall is low/)).not.toBeInTheDocument();
  });

  it("gives the checkpoint tie as a lead, not a tested cause", () => {
    render(<ResultsPage />);

    const reading = screen.getByRole("region", { name: /what we take from this/i });
    expect(within(reading).getByRole("heading", { name: /a measured lead: the checkpoint tie/i })).toBeInTheDocument();
    expect(within(reading).getByText(/a lead, not a tested cause/i)).toBeInTheDocument();
    const tie = within(reading).getByRole("table", { name: /checkpoint tie on the validation pairs/i });
    expect(within(tie).getAllByRole("row")).toHaveLength(4);
    expect(within(tie).getByRole("row", { name: /checkpoint 110/ })).toBeInTheDocument();
    expect(within(reading).queryByText(/too few to call this a pattern/)).not.toBeInTheDocument();
  });

  it("gives three explanations and says none was tested", () => {
    render(<ResultsPage />);

    const reading = screen.getByRole("region", { name: /what we take from this/i });
    expect(within(reading).getByRole("heading", { name: /why it happened is not known/i })).toBeInTheDocument();
    const untested = within(reading).getByRole("list", { name: /explanations that were not tested/i });
    expect(within(untested).getAllByRole("listitem")).toHaveLength(3);
    expect(within(untested).getByText(/264 of 484 training pairs \(54\.5%\) are non-human/)).toBeInTheDocument();
    expect(within(untested).queryByText(/83%/)).not.toBeInTheDocument();
    expect(within(reading).getByText(/keeps its prompted Gemma judge/)).toBeInTheDocument();
  });

  it("recommends five things and marks items 2 to 4 untested", () => {
    render(<ResultsPage />);

    const section = screen.getByRole("region", { name: /what we recommend/i });
    const items = within(section).getAllByRole("listitem");
    expect(items).toHaveLength(5);
    expect(items[0]).toHaveTextContent(/Keep prompted Gemma/);
    for (const i of [1, 2, 3]) expect(items[i]).toHaveTextContent(/Untested as a fix/);
    expect(items[0]).not.toHaveTextContent(/Untested as a fix/);
    expect(items[4]).toHaveTextContent(/did not demonstrate a reliable improvement/);
  });

  it("promises no ROC, precision-recall or threshold curve", () => {
    render(<ResultsPage />);

    expect(screen.getByText(/no ROC, precision-recall or threshold curve can be drawn/)).toBeInTheDocument();
    expect(screen.queryByText(/will (add|show|plot)/i)).not.toBeInTheDocument();
  });

  it("gives each chart a stable id, alt text, an as-of caption, a PNG link and a source link", () => {
    const { container } = render(<ResultsPage />);

    for (const id of [
      "judge-confusion-matrices",
      "judge-f1-precision-recall",
      "judge-catches-false-alarms",
      "judge-validation-checkpoints",
    ]) {
      const figure = container.querySelector(`[data-chart-id="${id}"]`) as HTMLElement;
      expect(figure, id).not.toBeNull();
      expect(figure.getAttribute("aria-label") ?? "").not.toBe("");
      expect(within(figure).getByText(/As of 2026-11-21/)).toBeInTheDocument();
      const png = within(figure).getByRole("link", { name: new RegExp(`Download ${id}\\.png`) });
      expect(png).toHaveAttribute("href", `/research/diagrams/${id}.png`);
      expect(png).toHaveAttribute("download", `${id}.png`);
      expect(within(figure).getByRole("link", { name: /data\.ts/ })).toHaveAttribute("target", "_blank");
    }
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
