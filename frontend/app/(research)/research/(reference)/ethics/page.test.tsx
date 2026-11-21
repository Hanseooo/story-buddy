import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import EthicsPage from "./page";

describe("/research/ethics", () => {
  it("states the basis: no ethics committee review, and why", () => {
    render(<EthicsPage />);

    const basis = screen.getByRole("region", { name: /ethics basis/i });
    expect(within(basis).getByText(/no ethics committee review/i)).toBeInTheDocument();
    expect(within(basis).getByText(/did not interact with the children/i)).toBeInTheDocument();
    expect(within(basis).getByText(/did not use the system during the study/i)).toBeInTheDocument();
  });

  it("states consent as the teacher's signed hard-copy consent and nothing wider", () => {
    render(<EthicsPage />);

    const consent = screen.getByRole("region", { name: /^consent/i });
    expect(within(consent).getByText(/teacher's signed hard-copy consent/i)).toBeInTheDocument();
    expect(within(consent).getByText(/no separate parental consent was collected/i)).toBeInTheDocument();
    expect(within(consent).getByText(/expert evaluators sign their own/i)).toBeInTheDocument();
  });

  it("discloses what is public and what is redacted", () => {
    render(<EthicsPage />);

    const privacy = screen.getByRole("region", { name: /privacy/i });
    expect(within(privacy).getByText(/story IDs, plot summaries and character names/i)).toBeInTheDocument();
    expect(within(privacy).getByText(/no donated images/i)).toBeInTheDocument();
    expect(within(privacy).getByText(/North America/)).toBeInTheDocument();
  });

  it("lists the moderation layers and where each runs", () => {
    render(<EthicsPage />);

    const table = screen.getByRole("table", { name: /moderation layers/i });
    expect(within(table).getByRole("row", { name: /Story text/ })).toHaveTextContent("meta-llama/llama-guard-4-12b");
    expect(within(table).getByRole("row", { name: /Story text/ })).toHaveTextContent("input_gate.py");
    expect(within(table).getByRole("row", { name: /Title/ })).toHaveTextContent("main.py");
  });

  it("states the magic pencil limits and the release gate", () => {
    render(<EthicsPage />);

    const safety = screen.getByRole("region", { name: /safety measures/i });
    expect(within(safety).getByText(/200 characters/)).toBeInTheDocument();
    expect(within(safety).getByText(/ethics re-review/i)).toBeInTheDocument();
  });
});
