import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import SdlcPage from "./page";

describe("/research/sdlc", () => {
  it("shows Figure 3 with its PNG and the editable source", () => {
    render(<SdlcPage />);

    expect(screen.getByRole("heading", { level: 1, name: "Development loops (SDLC)" })).toBeInTheDocument();
    const figure = screen.getByRole("figure", { name: /six development loops drawn as a spiral/i });
    expect(within(figure).getByText(/Figure 3/)).toBeInTheDocument();
    expect(within(figure).getByRole("img")).toHaveAttribute("src", "/research/diagrams/sdlc_spiral.png");
  });

  it("gives Table 1 one row per loop, each with its gate result in words", () => {
    render(<SdlcPage />);

    const table = screen.getByRole("table", { name: /table 1/i });
    // A header row plus six loops.
    expect(within(table).getAllByRole("row")).toHaveLength(7);
    const loop3 = within(table).getByRole("row", { name: /Loop 3/ });
    expect(within(loop3).getByText("Not run")).toBeInTheDocument();
    expect(within(loop3).getByText(/probe 4/)).toBeInTheDocument();
    expect(within(loop3).getByText(/#12–#18/)).toBeInTheDocument();
    const loop1 = within(table).getByRole("row", { name: /Loop 1/ });
    expect(within(loop1).getByText("Split")).toBeInTheDocument();
    expect(within(loop1).getByText(/none: committed to main before PR #1/i)).toBeInTheDocument();
    const loop6 = within(table).getByRole("row", { name: /Loop 6/ });
    expect(within(loop6).getByText("Open")).toBeInTheDocument();
  });

  it("lists where the work left the plan", () => {
    render(<SdlcPage />);

    const section = screen.getByRole("region", { name: "Where the work left the plan" });
    expect(within(section).getAllByRole("listitem")).toHaveLength(7);
    expect(within(section).getByText(/Loop 3 started without its entry gate\./)).toBeInTheDocument();
  });

  it("keeps the Phase 0.5 result as recorded", () => {
    render(<SdlcPage />);

    expect(screen.getByText(/Run 3 passed absolute \(80%\), failed separation \(\+25 vs ≥30\); escalation declined/)).toBeInTheDocument();
  });

  it("names the record and the git command that checks a row", () => {
    render(<SdlcPage />);

    const check = screen.getByRole("region", { name: "How to check a loop" });
    expect(within(check).getByText(/git show/)).toBeInTheDocument();
    expect(within(check).getByRole("link", { name: /docs\/capstone\/sdlc-record\.md/ })).toBeInTheDocument();
  });
});
