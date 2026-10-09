import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import RunFilters from "./RunFilters";
import { RUNS_QUERY_KEY } from "@/utils/metrics";

const navigation = vi.hoisted(() => ({ replace: vi.fn(), query: "style=cel" }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: navigation.replace }),
  usePathname: () => "/research/metrics",
  useSearchParams: () => new URLSearchParams(navigation.query),
}));

describe("RunFilters", () => {
  beforeEach(() => {
    navigation.replace.mockClear();
    navigation.query = "style=cel";
    sessionStorage.clear();
  });

  it("preserves the other filter, replaces history, and remembers the current query", () => {
    const { rerender } = render(<RunFilters styles={["cel", "gouache"]} hasNoStyle />);
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
    expect(sessionStorage.getItem(RUNS_QUERY_KEY)).toBe("style=cel");
    fireEvent.click(screen.getByRole("button", { name: "Failed" }));
    expect(navigation.replace).toHaveBeenLastCalledWith("/research/metrics?style=cel&status=failed", { scroll: false });

    navigation.query = "style=cel&status=failed";
    rerender(<RunFilters styles={["cel", "gouache"]} hasNoStyle />);
    fireEvent.change(screen.getByLabelText("Style"), { target: { value: "none" } });
    expect(navigation.replace).toHaveBeenLastCalledWith("/research/metrics?style=none&status=failed", { scroll: false });
    fireEvent.change(screen.getByLabelText("Style"), { target: { value: "all" } });
    expect(navigation.replace).toHaveBeenLastCalledWith("/research/metrics?status=failed", { scroll: false });
  });

  it("shows invalid URL filters honestly and clears both without requiring storage", () => {
    navigation.query = "status=bogus&style=unknown";
    const storage = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("Unavailable"); });
    try {
      render(<RunFilters styles={["cel"]} hasNoStyle />);
      expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
      expect(screen.getByLabelText("Style")).toHaveValue("unknown");
      fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
      expect(navigation.replace).toHaveBeenLastCalledWith("/research/metrics", { scroll: false });
    } finally {
      storage.mockRestore();
    }
  });
});
