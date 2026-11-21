import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DocsPage from "./page";
import { DOC_CHAPTERS } from "./entries";

describe("/research/docs", () => {
  it("opens each document on GitHub in a new tab", () => {
    render(<DocsPage />);

    const guide = screen.getByRole("link", { name: /group-guide\.md/ });
    expect(guide).toHaveAttribute(
      "href",
      "https://github.com/Hanseooo/story-buddy/blob/main/docs/capstone/group-guide.md"
    );
    expect(guide).toHaveAttribute("target", "_blank");
    expect(guide).toHaveAttribute("rel", "noopener noreferrer");
    const total = DOC_CHAPTERS.reduce((n, c) => n + c.entries.length, 0);
    expect(total).toBe(38);
    expect(screen.getAllByRole("link", { name: /opens on GitHub in a new tab/ })).toHaveLength(total);
  });

  it("marks the group guide as the place to start", () => {
    render(<DocsPage />);

    expect(screen.getByRole("link", { name: /group-guide\.md/ })).toHaveAccessibleName(/Start here/);
  });

  it("groups the entries under one heading per paper chapter", () => {
    render(<DocsPage />);

    for (const chapter of DOC_CHAPTERS) {
      expect(screen.getByRole("heading", { level: 2, name: chapter.title })).toBeInTheDocument();
    }
  });

  it("shows each entry's last-changed date", () => {
    render(<DocsPage />);

    const guide = screen.getByRole("link", { name: /group-guide\.md/ }).closest("li")!;
    expect(within(guide).getByText(/2026-11-21/)).toBeInTheDocument();
  });

  it("shows the 'What the paper must say' panel with open items and typos", () => {
    render(<DocsPage />);

    expect(screen.getByRole("heading", { name: "What the paper must say" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /O-04.*issue 135/i })).toHaveAttribute(
      "href",
      "https://github.com/Hanseooo/story-buddy/issues/135"
    );
    expect(screen.getByRole("link", { name: /O-07.*issue 136/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /O-12.*issue 137/i })).toBeInTheDocument();
    expect(screen.getByText(/Visibile/)).toBeInTheDocument();
    expect(screen.getByText(/Cohen's Cappa/)).toBeInTheDocument();
  });

  it("shows the donated-story count as a correction, not an open item", () => {
    render(<DocsPage />);

    const row = screen.getByTestId("correction-P6");
    expect(within(row).getByText("Repo is right")).toBeInTheDocument();
    expect(within(row).queryByText("Open")).toBeNull();
  });

  it("shows P7 and P24 as unconfirmed for the owner", () => {
    render(<DocsPage />);

    for (const id of ["P7", "P24"]) {
      const row = screen.getByTestId(`correction-${id}`);
      expect(within(row).getByText("Unconfirmed, owner to confirm")).toBeInTheDocument();
      expect(within(row).queryByRole("link", { name: /issue/ })).toBeNull();
    }
  });
});
