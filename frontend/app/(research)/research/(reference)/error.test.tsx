import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import MetricsError from "../metrics/error";
import ResearchPageError from "./error";

afterEach(() => vi.restoreAllMocks());

// US-02 AC-07: the way out of a failed research page names the hub it goes to.
describe("research error pages", () => {
  it.each([
    ["reference page", () => <ResearchPageError error={new Error("boom")} unstable_retry={() => {}} />],
    ["runs list", () => <MetricsError error={new Error("boom")} reset={() => {}} />],
  ])("%s links back to research home", (_name, ui) => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(ui());
    expect(screen.getByRole("link", { name: "Back to research home" })).toHaveAttribute("href", "/research");
    expect(screen.getByRole("alert")).not.toHaveTextContent(/methodology/i);
  });
});
