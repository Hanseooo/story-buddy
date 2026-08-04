import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Home from "./page";

describe("Home", () => {
  it("introduces StoryBuddy and links the primary action to the writing flow", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /big ideas\. bright pages\./i,
      })
    ).toBeDefined();
    expect(screen.getByRole("link", { name: /make a book/i })).toHaveAttribute(
      "href",
      "/write"
    );
    expect(
      screen.getByRole("navigation", { name: /main navigation/i })
    ).toBeDefined();
  });

  it("explains the creation flow and child-friendly safeguards", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { name: /from first line to final page/i })
    ).toBeDefined();
    expect(screen.getByText(/write your story/i)).toBeDefined();
    expect(
      screen.getByRole("heading", { name: /made for young imaginations/i })
    ).toBeDefined();
  });
});
