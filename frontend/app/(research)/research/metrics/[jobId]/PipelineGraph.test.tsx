import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import fixture from "./__fixtures__/run.json";
import { summarizeNodes } from "./nodeSummary";
import PipelineGraph from "./PipelineGraphView";
import type { RunDetail } from "./types";

const RUN = fixture as unknown as RunDetail;

beforeAll(() => {
  // jsdom has <dialog> but not its modal methods. These do what the browser does, `close` event included.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

const renderGraph = (steps = RUN.steps) =>
  render(<PipelineGraph steps={steps} endedOn={RUN.ended_on} summaries={summarizeNodes(RUN)} />);

describe("PipelineGraph", () => {
  it("lists the nodes in flow order with what happened at each", () => {
    renderGraph();
    const names = within(screen.getByRole("list", { name: "Pipeline steps" }))
      .getAllByRole("button")
      .map((b) => b.getAttribute("aria-label"));

    expect(names[0]).toBe("Input safety, ran once");
    expect(names).toContain("Split into pages, did not run");
    expect(names).toContain("Consistency check, ran 2 times, 1 redraw");
    expect(names.at(-1)).toBe("Compose book, did not run");
  });

  it("opens a panel for a node and returns focus to it on close", () => {
    renderGraph();
    const check = screen.getByRole("button", { name: "Consistency check, ran 2 times, 1 redraw" });
    check.focus();
    fireEvent.click(check);

    const panel = screen.getByRole("dialog", { name: "Consistency check" });
    expect(panel).toHaveAttribute("open");
    expect(panel).toHaveTextContent("Page 1: 2 attempts, shipped attempt 2.");

    fireEvent.click(within(panel).getByRole("button", { name: "Close panel" }));
    expect(panel).not.toHaveAttribute("open");
    expect(check).toHaveFocus();
  });

  it("the section link closes the panel without pulling focus back", () => {
    renderGraph();
    const check = screen.getByRole("button", { name: "Consistency check, ran 2 times, 1 redraw" });
    fireEvent.click(check);
    const panel = screen.getByRole("dialog", { name: "Consistency check" });

    const jump = within(panel).getByRole("link", { name: "Go to Pages" });
    expect(jump).toHaveAttribute("href", "#pages");
    fireEvent.click(jump);

    expect(panel).not.toHaveAttribute("open");
    expect(check).not.toHaveFocus();
  });

  it("notes steps that are not on the map instead of failing", () => {
    renderGraph([...RUN.steps, { node: "proofread", started_at: "2026-10-01T10:00:20+00:00", duration_ms: null }]);
    expect(screen.getByText("1 step not on this map.")).toBeInTheDocument();
  });
});
