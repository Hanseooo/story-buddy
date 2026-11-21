import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DatasetPage from "./dataset/page";
import DocsPage from "./docs/page";
import MethodologyPage from "./methodology/page";
import ResultsPage from "./results/page";

// The long pages open with jump links (a phone reader otherwise scrolls up to 19,000px). Every link must land
// on a section heading, and every section heading must be linked.
describe.each([
  ["results", ResultsPage, 14],
  ["dataset", DatasetPage, 10],
  ["methodology", MethodologyPage, 7],
  ["docs", DocsPage, 9],
] as const)("/research/%s contents", (_name, Page, count) => {
  it("links every section heading, and nothing else", () => {
    const { container } = render(<Page />);
    const contents = screen.getByRole("navigation", { name: "On this page" });
    const targets = within(contents).getAllByRole("link").map((l) => l.getAttribute("href")!.slice(1));
    expect(targets).toHaveLength(count);
    for (const id of targets) expect(document.getElementById(id)?.tagName, id).toBe("H2");
    const headings = [...container.querySelectorAll("h2[id]")].map((h) => h.id);
    expect(targets.sort()).toEqual(headings.sort());
  });
});
