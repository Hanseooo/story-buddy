import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import ScrollTable from "./ScrollTable";

// jsdom has no layout, so the box sizes are set by hand.
function setWidths(scrollWidth: number, clientWidth: number) {
  Object.defineProperty(HTMLElement.prototype, "scrollWidth", { configurable: true, get: () => scrollWidth });
  Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => clientWidth });
}

afterEach(() => {
  Reflect.deleteProperty(HTMLElement.prototype, "scrollWidth");
  Reflect.deleteProperty(HTMLElement.prototype, "clientWidth");
});

const table = (
  <ScrollTable label="Demo table">
    <tbody>
      <tr>
        <th scope="row">Row</th>
        <td>1</td>
      </tr>
    </tbody>
  </ScrollTable>
);

describe("ScrollTable", () => {
  it("shows a scroll cue when the table is wider than its box", () => {
    setWidths(900, 350);
    render(table);

    expect(screen.getByText("Scrolls sideways")).toBeInTheDocument();
    const region = screen.getByRole("region", { name: "Demo table" });
    expect(region).toHaveAttribute("tabindex", "0");
  });

  it("shows no cue when the table fits", () => {
    setWidths(350, 350);
    render(table);

    expect(screen.queryByText("Scrolls sideways")).toBeNull();
    expect(screen.getByRole("region", { name: "Demo table" })).toBeInTheDocument();
  });
});
