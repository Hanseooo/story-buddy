import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ArchitecturePage from "./page";

describe("/research/architecture", () => {
  it("shows the diagram with alt text, an As-of caption, a PNG download and a GitHub source", () => {
    render(<ArchitecturePage />);

    const figure = screen.getByRole("figure", { name: /system architecture/i });
    expect(within(figure).getByRole("img", { name: /system architecture/i })).toHaveAttribute("src", expect.stringContaining("system_architecture"));
    expect(within(figure).getByText("As of 2026-11-21")).toBeInTheDocument();
    const download = within(figure).getByRole("link", { name: /system_architecture\.png/ });
    expect(download).toHaveAttribute("download", "system_architecture.png");
    expect(within(figure).getByRole("link", { name: /system_architecture\.drawio\.svg/ })).toHaveAttribute(
      "href",
      expect.stringContaining("docs/diagrams/drawio/system_architecture.drawio.svg")
    );
  });

  it("lists each component with its role and source file", () => {
    render(<ArchitecturePage />);

    const table = screen.getByRole("table", { name: /components/i });
    const row = within(table).getByRole("row", { name: /Supabase Auth/ });
    expect(within(row).getByText(/backend\/app\/auth\.py/)).toBeInTheDocument();
    expect(within(table).getByRole("row", { name: /Magic pencil/ })).toBeInTheDocument();
  });

  it("gives every specification table a focusable, named scroll region", () => {
    render(<ArchitecturePage />);

    for (const name of [/^model ids/i, /^backend library versions/i, /^frontend library versions/i, /^training hardware values/i, /^hosting values/i, /^development hardware values/i]) {
      expect(screen.getByRole("region", { name })).toHaveAttribute("tabindex", "0");
    }
  });

  it("marks the development rows nobody has confirmed", () => {
    render(<ArchitecturePage />);

    const table = screen.getByRole("table", { name: /development hardware/i });
    expect(within(table).getByRole("row", { name: /Graphics card/ })).toHaveTextContent("NVIDIA RTX 3050 Ti, 4 GB VRAM");
    expect(within(table).getAllByText("Owner to supply")).toHaveLength(3);
  });

  it("shows exactly one image, the diagram", () => {
    render(<ArchitecturePage />);

    expect(screen.getAllByRole("img")).toHaveLength(1);
  });
});
