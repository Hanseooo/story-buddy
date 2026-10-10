import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RUNS_QUERY_KEY } from "@/utils/metrics";
import BackLink from "./BackLink";

afterEach(() => sessionStorage.clear());

describe("BackLink", () => {
  it("returns to the list with the filters it had", () => {
    sessionStorage.setItem(RUNS_QUERY_KEY, "status=failed&style=cel");
    render(<BackLink />);
    expect(screen.getByRole("link", { name: "All runs" })).toHaveAttribute(
      "href",
      "/research/metrics?status=failed&style=cel"
    );
  });

  it("falls back to the plain list", () => {
    render(<BackLink />);
    expect(screen.getByRole("link", { name: "All runs" })).toHaveAttribute("href", "/research/metrics");
  });
});
