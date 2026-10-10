import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DocsPage from "./page";

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
    expect(screen.getAllByRole("link", { name: /opens on GitHub in a new tab/ })).toHaveLength(14);
  });

  it("marks the group guide as the place to start", () => {
    render(<DocsPage />);

    expect(screen.getByRole("link", { name: /group-guide\.md/ })).toHaveAccessibleName(/Start here/);
  });
});
