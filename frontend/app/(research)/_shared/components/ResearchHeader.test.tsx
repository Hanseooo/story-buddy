import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ResearchHeader from "./ResearchHeader";
import type { ResearchViewer } from "../viewer";

let mockPath = "/research/metrics";
vi.mock("next/navigation", () => ({ usePathname: () => mockPath }));

const annotator: ResearchViewer = { id: "r-1", role: "researcher", isAdjudicator: false, displayName: "Ana" };
const adjudicator: ResearchViewer = { id: "r-2", role: "researcher", isAdjudicator: true, displayName: "Owner" };

function tabNames() {
  const nav = screen.getByRole("navigation", { name: "Research" });
  return within(nav).getAllByRole("link").map((link) => link.textContent);
}

describe("ResearchHeader", () => {
  it("the logo leaves the research site for StoryBuddy's home", () => {
    render(<ResearchHeader viewer={null} />);
    expect(screen.getByRole("link", { name: "StoryBuddy home" })).toHaveAttribute("href", "/");
  });

  it("signed out: three tabs, Runs marked current, with a sign-in link back here", () => {
    render(<ResearchHeader viewer={null} />);

    expect(tabNames()).toEqual(["Research home", "Docs", "Runs"]);
    expect(screen.getByRole("link", { name: "Runs" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Researcher sign in" })).toHaveAttribute(
      "href",
      "/login?next=/research/metrics"
    );
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
  });

  it("marks Research home current only on the hub, not on every page under /research", () => {
    const { rerender } = render(<ResearchHeader viewer={null} showAccount={false} />);
    expect(screen.getByRole("link", { name: "Research home" })).not.toHaveAttribute("aria-current");
    mockPath = "/research";
    rerender(<ResearchHeader viewer={null} showAccount={false} />);
    expect(screen.getByRole("link", { name: "Research home" })).toHaveAttribute("aria-current", "page");
    mockPath = "/research/docs";
    rerender(<ResearchHeader viewer={null} showAccount={false} />);
    expect(screen.getByRole("link", { name: "Docs" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Research home" })).not.toHaveAttribute("aria-current");
    mockPath = "/research/metrics";
  });

  it("annotator: three tabs and Annotate, Annotator chip, Log out", () => {
    render(<ResearchHeader viewer={annotator} />);

    expect(tabNames()).toEqual(["Research home", "Docs", "Runs", "Annotate"]);
    expect(screen.getByText("Annotator")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log out" })).toBeInTheDocument();
  });

  it("adjudicator: three tabs and Adjudicate, Adjudicator chip", () => {
    render(<ResearchHeader viewer={adjudicator} />);

    expect(tabNames()).toEqual(["Research home", "Docs", "Runs", "Adjudicate"]);
    expect(screen.getByText("Adjudicator")).toBeInTheDocument();
  });

  // The static pages (ADR-065, ADR-066, ADR-067) read no session, so they cannot say who is signed in.
  it("showAccount off: tabs only, no sign-in link and no Log out", () => {
    render(<ResearchHeader viewer={null} showAccount={false} />);

    expect(tabNames()).toEqual(["Research home", "Docs", "Runs"]);
    expect(screen.queryByRole("link", { name: "Researcher sign in" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
  });
});
