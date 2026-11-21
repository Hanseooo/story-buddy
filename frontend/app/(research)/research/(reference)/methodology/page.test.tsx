import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import MethodologyPage from "./page";

describe("/research/methodology", () => {
  it("states the design and the Spiral phases with the Phase 0.5 result as recorded", () => {
    render(<MethodologyPage />);

    expect(screen.getByRole("heading", { level: 1, name: "Methodology at a glance" })).toBeInTheDocument();
    const table = screen.getByRole("table", { name: /spiral phases/i });
    expect(within(table).getAllByRole("row")).toHaveLength(5);
    expect(within(table).getByRole("row", { name: /Loop 4: Evaluation/ })).toBeInTheDocument();
    expect(screen.getByText(/Run 3 passed absolute \(80%\), failed separation \(\+25 vs ≥30\)/)).toBeInTheDocument();
  });

  it("names the source school", () => {
    render(<MethodologyPage />);

    const setting = screen.getByRole("region", { name: "Setting" });
    expect(within(setting).getByText(/Stories are collected at Vicente Hizon, Sr\. Elementary School/)).toBeInTheDocument();
  });

  it("shows both implementation sites as undecided", () => {
    render(<MethodologyPage />);

    const site = screen.getByRole("region", { name: "Implementation site" });
    expect(within(site).getByText("Undecided")).toBeInTheDocument();
    expect(within(site).getByText(/Option A: Vicente Hizon, Sr\. Elementary School/)).toBeInTheDocument();
    expect(within(site).getByText(/Option B: HCDC, with 40 School of Teacher Education \(STE\) students\./)).toBeInTheDocument();
  });

  it("gives the four corpus counts", () => {
    render(<MethodologyPage />);

    const corpus = screen.getByRole("region", { name: "Corpus" });
    const counts = within(corpus).getAllByRole("term").map((t) => t.textContent);
    expect(counts).toEqual(["15", "12", "30", "42"]);
  });

  it("describes both respondent groups and links to the instruments page", () => {
    render(<MethodologyPage />);

    const respondents = screen.getByRole("region", { name: "Respondents" });
    expect(within(respondents).getByText(/2 Bachelor of Elementary Education \(BEEd\) professors and 1 Arts professor/)).toBeInTheDocument();
    expect(within(respondents).getByText(/At least 30 respondents in total/)).toBeInTheDocument();
    expect(within(respondents).getByRole("link", { name: /evaluation instruments/i })).toHaveAttribute("href", "/research/instruments");
  });

  it("shows no contact details", () => {
    const { container } = render(<MethodologyPage />);

    expect(container.textContent).not.toMatch(/@|e-?mail|phone/i);
  });
});
