import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import RunError from "./error";

afterEach(() => vi.restoreAllMocks());

describe("RunError", () => {
  it("asks Next to refetch the failed segment when the reader retries", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const retry = vi.fn();
    render(<RunError error={new TypeError("fetch failed")} unstable_retry={retry} />);

    fireEvent.click(screen.getByRole("button", { name: "Try again" }));

    expect(retry).toHaveBeenCalledOnce();
    expect(screen.getByRole("link", { name: "All runs" })).toBeInTheDocument();
  });
});
