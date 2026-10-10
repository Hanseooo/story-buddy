import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ReferenceLayout from "./layout";

vi.mock("next/navigation", () => ({ usePathname: () => "/research/dataset" }));

describe("static research pages layout", () => {
  it("shows the research tabs and a way back, with no account controls", () => {
    render(
      <ReferenceLayout>
        <p>page body</p>
      </ReferenceLayout>
    );

    expect(screen.getByText("page body")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Dataset" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Back to Methodology" })).toHaveAttribute("href", "/research");
    expect(screen.queryByRole("link", { name: "Researcher sign in" })).toBeNull();
  });
});
