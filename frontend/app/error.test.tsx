import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ErrorBoundary from "./error";

describe("Global Error Boundary (error.tsx)", () => {
  it("renders friendly error message and headline", () => {
    const resetFn = vi.fn();
    render(<ErrorBoundary error={new Error("Test crash")} reset={resetFn} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /something took an unexpected turn/i,
      })
    ).toBeDefined();

    expect(
      screen.getByText(/your work is saved\. you can try refreshing this page or return home/i)
    ).toBeDefined();
  });

  it("calls reset when Try Again button is clicked", () => {
    const resetFn = vi.fn();
    render(<ErrorBoundary error={new Error("Test crash")} reset={resetFn} />);

    const retryButton = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryButton);

    expect(resetFn).toHaveBeenCalledTimes(1);
  });

  it("provides a return home link", () => {
    const resetFn = vi.fn();
    render(<ErrorBoundary error={new Error("Test crash")} reset={resetFn} />);

    const homeLink = screen.getByRole("link", { name: /back to my storybook/i });
    expect(homeLink).toHaveAttribute("href", "/");
  });
});
