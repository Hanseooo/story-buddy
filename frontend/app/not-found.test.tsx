import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import NotFound from "./not-found";

describe("NotFound Page (404)", () => {
  it("renders friendly storybook 404 heading and body text", () => {
    render(<NotFound />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /this page hasn't been written yet/i,
      })
    ).toBeDefined();

    expect(
      screen.getByText(/looks like this story took a secret shortcut off the map/i)
    ).toBeDefined();
  });

  it("provides primary and secondary return CTAs", () => {
    render(<NotFound />);

    const homeLink = screen.getByRole("link", { name: /back to my storybook/i });
    expect(homeLink).toHaveAttribute("href", "/");

    const createLink = screen.getByRole("link", { name: /start a new story/i });
    expect(createLink).toHaveAttribute("href", "/signup");
  });

  it("displays the 404 unwritten page visual badge and storybook frame", () => {
    render(<NotFound />);

    expect(screen.getByText("Page 404")).toBeDefined();
    expect(screen.getByTestId("storybook-404-visual")).toBeDefined();
  });
});
