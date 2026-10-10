import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ResearchHeader from "./ResearchHeader";
import type { ResearchViewer } from "../viewer";

vi.mock("next/navigation", () => ({ usePathname: () => "/research/metrics" }));

const annotator: ResearchViewer = { id: "r-1", role: "researcher", isAdjudicator: false, displayName: "Ana" };
const adjudicator: ResearchViewer = { id: "r-2", role: "researcher", isAdjudicator: true, displayName: "Owner" };

function tabNames() {
  const nav = screen.getByRole("navigation", { name: "Research" });
  return within(nav).getAllByRole("link").map((link) => link.textContent);
}

describe("ResearchHeader", () => {
  it("signed out: Runs only, marked current, with a sign-in link back here", () => {
    render(<ResearchHeader viewer={null} />);

    expect(tabNames()).toEqual(["Runs"]);
    expect(screen.getByRole("link", { name: "Runs" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Researcher sign in" })).toHaveAttribute(
      "href",
      "/login?next=/research/metrics"
    );
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
  });

  it("annotator: Runs and Annotate, Annotator chip, Log out", () => {
    render(<ResearchHeader viewer={annotator} />);

    expect(tabNames()).toEqual(["Runs", "Annotate"]);
    expect(screen.getByText("Annotator")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log out" })).toBeInTheDocument();
  });

  it("adjudicator: Runs and Adjudicate, Adjudicator chip", () => {
    render(<ResearchHeader viewer={adjudicator} />);

    expect(tabNames()).toEqual(["Runs", "Adjudicate"]);
    expect(screen.getByText("Adjudicator")).toBeInTheDocument();
  });
});
