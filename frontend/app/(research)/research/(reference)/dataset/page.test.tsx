import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import DatasetPage from "./page";

describe("/research/dataset", () => {
  it("shows the split sizes with the file they come from", () => {
    render(<DatasetPage />);

    const splits = screen.getByRole("table", { name: /pairs in each split/i });
    const test = within(splits).getByRole("row", { name: /Held-out test/ });
    expect(within(test).getByText("329")).toBeInTheDocument();
    expect(within(test).getByText("47")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /research_runbook\.md/ })[0]).toHaveAttribute(
      "href",
      "https://github.com/Hanseooo/story-buddy/blob/main/docs/capstone/research_runbook.md"
    );
  });

  it("says the examples are hand-picked and that no test pair is shown", () => {
    render(<DatasetPage />);

    expect(screen.getByText(/hand-picked/i)).toBeInTheDocument();
    expect(screen.getByText(/no test pair is shown/i)).toBeInTheDocument();
  });

  it("shows each example as a reference and a page with its label", () => {
    render(<DatasetPage />);

    const examples = screen.getAllByRole("article");
    expect(examples).toHaveLength(6);
    expect(examples.filter((example) => within(example).queryByText("Same character"))).toHaveLength(3);
    expect(examples.filter((example) => within(example).queryByText("Different character"))).toHaveLength(3);
    for (const example of examples) expect(within(example).getAllByRole("img")).toHaveLength(2);
  });

  // ADR-066 decision 1.
  it("lets the reader open each example's frozen record", () => {
    render(<DatasetPage />);

    const examples = screen.getAllByRole("article");
    for (const example of examples) expect(within(example).getByText("Frozen record")).toBeInTheDocument();

    const constructed = examples[5];
    expect(constructed).toHaveTextContent('"pair_id": "848c636f47f8e342"');
    expect(constructed).toHaveTextContent('"pair_type": "constructed"');
    expect(constructed).toHaveTextContent("Not shown to the raters");
    expect(examples[0]).toHaveTextContent("Both raters first answered Same");
  });

  // ADR-066 decisions 2, 3 and 10.
  it("explains the record's fields, shows one training record, and states the two contradictory pairs", () => {
    render(<DatasetPage />);

    const fields = screen.getByRole("table", { name: /what each field of a record means/i });
    expect(within(fields).getByRole("row", { name: /ref_verdict_status/ })).toBeInTheDocument();
    expect(within(fields).getAllByRole("row")).toHaveLength(13); // header + 12 fields
    expect(screen.getByText(/The FIRST image is a canonical character reference/)).toBeInTheDocument();
    expect(screen.getByText(/"style_match": false/)).toBeInTheDocument();
    expect(screen.getByText(/the same fixed value in every training record/i)).toBeInTheDocument();
    expect(screen.getByText(/the training file holds those two image pairs with both answers/i)).toBeInTheDocument();
  });
});
