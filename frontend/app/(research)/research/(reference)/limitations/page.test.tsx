import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LimitationsPage from "./page";

describe("/research/limitations", () => {
  it("says who scored the pages and that the numbers are provisional", () => {
    render(<LimitationsPage />);

    expect(screen.getByText(/AI-assisted visual assessment.*provisional/i)).toBeInTheDocument();
    expect(screen.queryByText(/AI reviewers|AI rater/i)).not.toBeInTheDocument();
  });

  it("splits the defect rate by character kind", () => {
    render(<LimitationsPage />);

    const kinds = screen.getByRole("region", { name: /human and non-human characters/i });
    const pages = within(kinds).getByRole("group", { name: "Pages with a major defect" });
    expect(within(pages).getByText("11 of 33")).toBeInTheDocument();
    expect(within(pages).getByText("66 of 117")).toBeInTheDocument();
    expect(within(kinds).getByText(/including mixed human and non-human casts/i)).toBeInTheDocument();
    expect(within(kinds).queryByText(/83%/)).not.toBeInTheDocument();
  });

  it("gives each defect its row", () => {
    render(<LimitationsPage />);

    const table = screen.getByRole("table", { name: /most common major defects/i });
    const inherited = within(table).getByRole("row", { name: /Reference inherited/ });
    expect(within(inherited).getByText("34")).toBeInTheDocument();
    expect(within(table).getAllByRole("row")).toHaveLength(6);
  });

  it("sets the scene editor against the two others that were tried", () => {
    render(<LimitationsPage />);

    const editors = screen.getByRole("region", { name: /the scene editor against two others/i });
    expect(within(editors).getByRole("heading", { name: /FLUX\.2 klein/ })).toBeInTheDocument();
    expect(within(editors).getByRole("heading", { name: /OmniGen2/ })).toBeInTheDocument();
    const identity = within(editors).getByRole("group", { name: "Pages where the character lost its identity" });
    expect(within(identity).getByText("3 of 30")).toBeInTheDocument();
    expect(within(identity).getByText("10 of 30")).toBeInTheDocument();
    expect(within(editors).getByText(/editor's name hidden.*the blinding is partial/i)).toBeInTheDocument();
    expect(within(editors).getByText(/three-eyed lizard-bird/i)).toBeInTheDocument();
    // ADR-067 decision 6: the three things the Phase 0.5 card must say.
    const buildCheck = within(editors).getByText(/not a finding of the study/i);
    expect(buildCheck).toHaveTextContent(/scored without blinding/i);
    expect(buildCheck).toHaveTextContent(/both runs failed the gate/i);
  });

  it("lists everything that was tried and all nine limitations", () => {
    render(<LimitationsPage />);

    expect(screen.getByText(/the October tests the group guide lists/i)).toBeInTheDocument();
    const tried = screen.getByRole("table", { name: /what was tried in october/i });
    expect(within(tried).getAllByRole("row")).toHaveLength(9);
    const limits = screen.getByRole("region", { name: /limitations to state/i });
    expect(within(limits).getAllByRole("heading", { level: 3 })).toHaveLength(9);
    expect(within(limits).getByRole("heading", { name: "Stated body counts" })).toBeInTheDocument();
  });

  it("links each section from the top of the page", () => {
    render(<LimitationsPage />);

    const contents = screen.getByRole("navigation", { name: "On this page" });
    for (const link of within(contents).getAllByRole("link")) {
      expect(document.getElementById(link.getAttribute("href")!.slice(1)), link.textContent ?? "").not.toBeNull();
    }
    expect(within(contents).getAllByRole("link")).toHaveLength(6);
  });

  it("opens the group guide on GitHub in a new tab", () => {
    render(<LimitationsPage />);

    const guide = screen.getAllByRole("link", { name: /group-guide\.md/ })[0];
    expect(guide).toHaveAttribute("href", "https://github.com/Hanseooo/story-buddy/blob/main/docs/capstone/group-guide.md");
    expect(guide).toHaveAttribute("target", "_blank");
    expect(guide).toHaveAttribute("rel", "noopener noreferrer");
    expect(guide).toHaveAccessibleName(/opens on GitHub in a new tab/);
  });

  // ADR-065 decision 5: no donated story or character id, in the text or in a link.
  it("names no donated story", () => {
    const { container } = render(<LimitationsPage />);

    expect(container.innerHTML).not.toMatch(/don-/i);
  });
});
