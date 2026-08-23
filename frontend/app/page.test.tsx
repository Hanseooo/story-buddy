import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import Home from "./page";

describe("Home", () => {
  it("introduces StoryBuddy and links CTAs to signup and join", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /big ideas\. bright pages\./i,
      })
    ).toBeDefined();

    const signupLinks = screen.getAllByRole("link", { name: /sign up/i });
    signupLinks.forEach((link) => expect(link).toHaveAttribute("href", "/welcome?action=signup"));

    const joinLinks = screen.getAllByRole("link", { name: /enter class code/i });
    joinLinks.forEach((link) => expect(link).toHaveAttribute("href", "/join"));

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
