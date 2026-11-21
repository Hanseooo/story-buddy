import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ReferenceLayout from "./layout";

let mockPath = "/research/dataset";
vi.mock("next/navigation", () => ({ usePathname: () => mockPath }));

function renderAt(path: string) {
  mockPath = path;
  return render(
    <ReferenceLayout>
      <p>page body</p>
    </ReferenceLayout>
  );
}

describe("static research pages layout", () => {
  beforeEach(() => {
    mockPath = "/research/dataset";
  });

  it("shows the three header items and a back link to the hub, with no account controls", () => {
    renderAt("/research/dataset");

    expect(screen.getByText("page body")).toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Research" });
    expect(within(nav).getAllByRole("link").map((l) => l.textContent)).toEqual(["Research home", "Docs", "Runs"]);
    expect(screen.getByRole("link", { name: "Back to research home" })).toHaveAttribute("href", "/research");
    expect(screen.queryByRole("link", { name: /Back to (Methodology|Landing)/ })).toBeNull();
    expect(screen.queryByRole("link", { name: "Researcher sign in" })).toBeNull();
  });

  // US-02 AC-07: the end of every page in the order names its neighbours.
  it("ends with Previous and Next links that name the target pages", () => {
    renderAt("/research/dataset");

    const pager = screen.getByRole("navigation", { name: "Previous and next page" });
    const previous = within(pager).getByRole("link", { name: /Previous.*Methodology at a glance/ });
    const next = within(pager).getByRole("link", { name: /Next.*Evaluation instruments/ });
    expect(previous).toHaveAttribute("href", "/research/methodology");
    expect(next).toHaveAttribute("href", "/research/instruments");
  });

  it("has no Previous on the first page and no Next on the last", () => {
    const { unmount } = renderAt("/research/pipeline");
    let pager = screen.getByRole("navigation", { name: "Previous and next page" });
    expect(within(pager).queryByRole("link", { name: /Previous/ })).toBeNull();
    expect(within(pager).getByRole("link", { name: /Next.*Methodology at a glance/ })).toBeInTheDocument();
    unmount();

    renderAt("/research/docs");
    pager = screen.getByRole("navigation", { name: "Previous and next page" });
    expect(within(pager).queryByRole("link", { name: /Next/ })).toBeNull();
    expect(within(pager).getByRole("link", { name: /Previous.*Limitations/ })).toBeInTheDocument();
  });

  // US-02 AC-08: Tab follows the DOM when no tabindex above 0 is used: header, back link, content, Previous, Next.
  it("puts focus in order: header, back link, content, Previous, Next, with no positive tabindex", () => {
    mockPath = "/research/dataset";
    const { container } = render(
      <ReferenceLayout>
        <a href="#x">content link</a>
      </ReferenceLayout>
    );
    const focusable = [...container.querySelectorAll<HTMLElement>("a[href], button, [tabindex]")];
    expect(focusable.every((el) => !(Number(el.getAttribute("tabindex")) > 0))).toBe(true);
    const names = focusable.map((el) => (el.textContent ?? "").replace(/\s+/g, " ").trim());
    const at = (text: RegExp) => names.findIndex((n) => text.test(n));
    const order = [/^Research home$/, /^Docs$/, /^Runs$/, /^Back to research home$/, /^content link$/, /^Previous/, /^Next/].map(at);
    expect(order.every((i) => i >= 0)).toBe(true);
    expect(order).toEqual([...order].sort((a, b) => a - b));
  });
});
