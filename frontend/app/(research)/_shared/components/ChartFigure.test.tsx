import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ChartFigure from "./ChartFigure";

const props = {
  id: "demo",
  alt: "A demo figure",
  asOf: "2026-11-21",
  png: "/research/diagrams/demo.png",
  source: "docs/diagrams/drawio/demo.drawio.svg",
  caption: "Demo",
};

describe("ChartFigure", () => {
  // Charts stay narrow so their text reads at its drawn size; a wide diagram takes the full content width.
  it("caps a chart at a readable width by default", () => {
    render(<ChartFigure {...props}>x</ChartFigure>);
    expect(screen.getByRole("figure", { name: "A demo figure" }).className).toContain("max-w-3xl");
  });

  // At 390px a long file name must wrap, or the page scrolls sideways (SH-10). Measured on /research/dataset.
  it("lets the download and source file names wrap", () => {
    render(
      <ChartFigure {...props} png="/research/diagrams/dataset_build_and_annotation_flow.png" source="docs/diagrams/drawio/dataset_build_and_annotation_flow.drawio.svg">
        x
      </ChartFigure>
    );
    const download = screen.getByRole("link", { name: /Download dataset_build_and_annotation_flow\.png/ });
    const source = screen.getByRole("link", { name: /dataset_build_and_annotation_flow\.drawio\.svg/ });
    expect(download.querySelector(".break-all")).not.toBeNull();
    expect(source.querySelector(".break-all")).not.toBeNull();
  });

  it("lets a wide diagram use the full content width", () => {
    render(
      <ChartFigure {...props} wide>
        x
      </ChartFigure>
    );
    const figure = screen.getByRole("figure", { name: "A demo figure" });
    expect(figure.className).not.toContain("max-w-3xl");
    expect(figure.getAttribute("data-chart-id")).toBe("demo");
  });
});
