import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import GlobalError from "./global-error";

describe("Root Layout Global Error Boundary (global-error.tsx)", () => {
  it("renders standalone fallback error view", () => {
    const resetFn = vi.fn();
    render(<GlobalError error={new Error("Root layout crash")} reset={resetFn} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /storybuddy needs a quick refresh/i,
      })
    ).toBeDefined();

    expect(
      screen.getByText(/something interrupted the storybook connection/i)
    ).toBeDefined();
  });

  it("triggers reset callback on button click", () => {
    const resetFn = vi.fn();
    render(<GlobalError error={new Error("Root layout crash")} reset={resetFn} />);

    const retryButton = screen.getByRole("button", { name: /refresh page/i });
    fireEvent.click(retryButton);

    expect(resetFn).toHaveBeenCalledTimes(1);
  });
});
