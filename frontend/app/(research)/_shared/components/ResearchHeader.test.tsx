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
  it("signed out: the public tabs, Runs marked current, with a sign-in link back here", () => {
    render(<ResearchHeader viewer={null} />);

    expect(tabNames()).toEqual(["Runs", "Dataset", "Results", "Docs"]);
    expect(screen.getByRole("link", { name: "Runs" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Researcher sign in" })).toHaveAttribute(
      "href",
      "/login?next=/research/metrics"
    );
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
  });

  it("annotator: the public tabs and Annotate, Annotator chip, Log out", () => {
    render(<ResearchHeader viewer={annotator} />);

    expect(tabNames()).toEqual(["Runs", "Dataset", "Results", "Docs", "Annotate"]);
    expect(screen.getByText("Annotator")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log out" })).toBeInTheDocument();
  });

  it("adjudicator: the public tabs and Adjudicate, Adjudicator chip", () => {
    render(<ResearchHeader viewer={adjudicator} />);

    expect(tabNames()).toEqual(["Runs", "Dataset", "Results", "Docs", "Adjudicate"]);
    expect(screen.getByText("Adjudicator")).toBeInTheDocument();
  });

  // The static pages (ADR-065, ADR-066) read no session, so they cannot say who is signed in.
  it("showAccount off: tabs only, no sign-in link and no Log out", () => {
    render(<ResearchHeader viewer={null} showAccount={false} />);

    expect(tabNames()).toEqual(["Runs", "Dataset", "Results", "Docs"]);
    expect(screen.queryByRole("link", { name: "Researcher sign in" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
  });
});
