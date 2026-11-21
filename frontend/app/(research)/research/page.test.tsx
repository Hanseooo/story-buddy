import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RESEARCH_PAGES } from "../_shared/readingOrder";
import ResearchHubPage from "./page";

vi.mock("next/navigation", () => ({ usePathname: () => "/research" }));
// D-26: the hub reads no session and no profile. Any call to the server client fails the test.
const createClient = vi.fn(() => {
  throw new Error("the hub must not read a session");
});
vi.mock("@/utils/supabase/server", () => ({ createSupabaseServerClient: () => createClient() }));

describe("/research hub", () => {
  it("lists three groups in the order of index 4.1, each page once with its title, line and paper sections", () => {
    const { container } = render(<ResearchHubPage />);

    const groups = screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent);
    expect(groups).toEqual(["Methodology", "Results", "Reference"]);

    const entryTitles = [...container.querySelectorAll("ol a")].map((l) => l.textContent);
    expect(entryTitles).toEqual(RESEARCH_PAGES.map((p) => p.title));

    // Hand-worked from index 4.1 and US-01 AC-03's example, not computed from the list.
    const dataset = screen.getByRole("link", { name: "Dataset" }).closest("li") as HTMLElement;
    expect(dataset).toHaveTextContent("What a pair is, how pairs were labelled, and how they were split.");
    expect(dataset).toHaveTextContent("Paper: Dataset, Annotation, Dataset Division");
    expect(screen.getByRole("link", { name: "Dataset" })).toHaveAttribute("href", "/research/dataset");

    const results = screen.getByRole("heading", { level: 2, name: "Results" }).closest("section") as HTMLElement;
    expect(within(results).getAllByRole("link").map((l) => l.getAttribute("href"))).toEqual([
      "/research/objectives",
      "/research/results",
      "/research/limitations",
    ]);
    expect(within(screen.getByRole("main")).getByRole("link", { name: "Runs" })).toHaveAttribute("href", "/research/metrics");
  });

  it("reads no session and shows the same page logged out: no account controls, Research home current", () => {
    render(<ResearchHubPage />);

    expect(createClient).not.toHaveBeenCalled();
    expect(screen.queryByRole("link", { name: "Researcher sign in" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Log out" })).toBeNull();
    const nav = screen.getByRole("navigation", { name: "Research" });
    expect(within(nav).getByRole("link", { name: "Research home" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getAllByRole("link").map((l) => l.textContent)).toEqual(["Research home", "Docs", "Runs"]);
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  // US-01 AC-04: the stale and marketing claims are gone, and the pipeline map lives on /research/pipeline.
  it("has none of the old claims, headlines or the pipeline map", () => {
    const { container } = render(<ResearchHubPage />);
    const text = container.textContent ?? "";

    for (const gone of [
      "11 deterministic nodes",
      "self-host",
      "Self-hostable",
      "View Live Metrics",
      "science behind the magic",
      "Building a safe, consistent story pipeline",
      "Back to Landing",
    ]) {
      expect(text, gone).not.toContain(gone);
    }
    expect(container.querySelectorAll("[data-node]")).toHaveLength(0);
  });
});
