import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import InstrumentsPage from "./page";

describe("/research/instruments", () => {
  it("lists the seven expert questions in order, each with its guide prompt", () => {
    render(<InstrumentsPage />);

    const expert = screen.getByRole("region", { name: "Expert questionnaire" });
    const list = within(expert).getByRole("list", { name: "The seven questions" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(7);
    expect(items[0]).toHaveTextContent("How appropriate and meaningful is the generated picture book for its intended readers?");
    expect(items[6]).toHaveTextContent(/what improvements would you recommend\?/);
    expect(items[3]).toHaveTextContent(/Consider the sequence and connection of events/);
  });

  it("shows the analysis method as undecided and never calls the expert results descriptive statistics", () => {
    render(<InstrumentsPage />);

    const expert = screen.getByRole("region", { name: "Expert questionnaire" });
    expect(within(expert).getByText("Content analysis or thematic analysis (to be decided)")).toBeInTheDocument();
    expect(within(expert).queryByText(/descriptive statistics/i)).not.toBeInTheDocument();
  });

  it("lists 23 ISO items under six headings, numbered across headings", () => {
    render(<InstrumentsPage />);

    const iso = screen.getByRole("region", { name: "ISO/IEC 25010 questionnaire" });
    expect(within(iso).getAllByRole("heading", { level: 3 })).toHaveLength(6);
    expect(within(iso).getByRole("heading", { level: 3, name: /Interaction Capability/ })).toBeInTheDocument();
    const lists = within(iso).getAllByRole("list", { name: /items$/ });
    expect(lists).toHaveLength(6);
    expect(within(iso).getAllByRole("listitem").filter((li) => li.getAttribute("value"))).toHaveLength(23);
    expect(within(lists[5]).getAllByRole("listitem").map((li) => li.getAttribute("value"))).toEqual(["22", "23"]);
    expect(within(iso).getByText(/higher mean is better/)).toBeInTheDocument();
    expect(within(iso).getByText(/Descriptive statistics only/)).toBeInTheDocument();
  });

  it("marks both instruments as pending", () => {
    render(<InstrumentsPage />);

    expect(screen.getAllByText("Survey pending")).toHaveLength(2);
  });

  it("shows no contact details and no evaluator names", () => {
    const { container } = render(<InstrumentsPage />);

    expect(container.textContent).not.toMatch(/@|e-?mail|phone/i);
  });
});
