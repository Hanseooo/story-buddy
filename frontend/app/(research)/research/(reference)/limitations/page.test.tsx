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

  it("illustrates four visible limitations with requirements and historical output roles", () => {
    render(<LimitationsPage />);

    const examples = screen.getByRole("region", { name: "Examples of visible limitations" });
    expect(within(examples).getAllByRole("article")).toHaveLength(4);
    expect(within(examples).getAllByRole("img")).toHaveLength(5);
    expect(within(examples).getByText(/hand-picked synthetic examples.*do not establish/i)).toBeInTheDocument();
    expect(within(examples).getByText(/only four legs are depicted/i)).toBeInTheDocument();
    expect(within(examples).getByText(/what came out was air, because he was a sock/i)).toBeInTheDocument();
    expect(within(examples).getByText(/syn-021.*s6.*selected final.*attempt 1/i)).toBeInTheDocument();
    expect(within(examples).getByText(/syn-019.*s1.*selected final.*attempt 3/i)).toBeInTheDocument();
    expect(within(examples).getByRole("link", { name: /identity-drift examples/i })).toHaveAttribute("href", "/research/dataset#examples");
    for (const image of within(examples).getAllByRole("img")) {
      expect(image).toHaveAttribute("width", "768");
      expect(image).toHaveAttribute("height", "576");
      expect(image).toHaveAttribute("loading", "lazy");
    }
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

  it("lists everything that was tried and all eleven limitations", () => {
    render(<LimitationsPage />);

    expect(screen.getByText(/the October and November tests the group guide lists/i)).toBeInTheDocument();
    const tried = screen.getByRole("table", { name: /what was tried in october/i });
    expect(within(tried).getAllByRole("row")).toHaveLength(10);
    const limits = screen.getByRole("region", { name: /limitations to state/i });
    expect(within(limits).getAllByRole("heading", { level: 3 })).toHaveLength(11);
    expect(within(limits).getByRole("heading", { name: "Stated body counts" })).toBeInTheDocument();
  });

  it("replaces the old reference-check sentence with the counts, and explains 77 + 71 + 2 = 150", () => {
    render(<LimitationsPage />);

    const checks = screen.getByRole("region", { name: /what the automatic checks caught/i });
    expect(within(checks).queryByText(/finds most bad references/i)).not.toBeInTheDocument();
    expect(within(checks).getByText(/fails about 4 in 10 good ones \(15 of 38\)/)).toBeInTheDocument();
    expect(within(checks).getByText("77 of 150 have a major defect, 71 are acceptable and 2 are uncertain.")).toBeInTheDocument();
    expect(within(checks).getByText(/23 of the 71 redrawn first drafts were already acceptable/)).toBeInTheDocument();
  });

  it("gives both outcome charts a stable id, alt text, an as-of caption and a PNG link", () => {
    const { container } = render(<LimitationsPage />);

    for (const id of ["reference-check-outcomes", "page-check-outcomes"]) {
      const figure = container.querySelector(`[data-chart-id="${id}"]`) as HTMLElement;
      expect(figure, id).not.toBeNull();
      expect(figure.getAttribute("aria-label") ?? "").not.toBe("");
      expect(within(figure).getByText(/As of 2026-10-08/)).toBeInTheDocument();
      expect(within(figure).getByRole("link", { name: `Download ${id}.png` })).toHaveAttribute("href", `/research/diagrams/${id}.png`);
      expect(within(figure).getByRole("link", { name: /data\.ts/ })).toHaveAttribute("target", "_blank");
    }
  });

  it("brings the page up to November without a sentence about human review", () => {
    const { container } = render(<LimitationsPage />);

    expect(screen.getByText(/versions 6 and 7.*500-word.*magic pencil.*not measured here/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "The reference check cannot verify stated details" })).toBeInTheDocument();
    expect(screen.getByText(/stopped 4 of 30 synthetic stories/)).toBeInTheDocument();
    expect(screen.getByText(/2 of 9 fixed, against 5 of 9 with hand-written instructions/)).toBeInTheDocument();
    expect(screen.getByText(/klein also missed the action on 8 of 30 pages, against 2 for Qwen/)).toBeInTheDocument();
    const editors = screen.getByRole("region", { name: /the scene editor against two others/i });
    expect(within(editors).getByRole("group", { name: "Pages with a duplicate or extra character" })).toBeInTheDocument();
    expect(screen.getByText(/one rater, the AI assistant/)).toBeInTheDocument();
    expect(container.textContent).not.toMatch(/human review|reviewed the stored images/i);
  });

  it("links each section from the top of the page", () => {
    render(<LimitationsPage />);

    const contents = screen.getByRole("navigation", { name: "On this page" });
    for (const link of within(contents).getAllByRole("link")) {
      expect(document.getElementById(link.getAttribute("href")!.slice(1)), link.textContent ?? "").not.toBeNull();
    }
    expect(within(contents).getAllByRole("link")).toHaveLength(7);
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
