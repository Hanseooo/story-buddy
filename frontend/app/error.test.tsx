import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ErrorBoundary from "./error";
import StudentErrorBoundary from "./s/[profileId]/error";
import ClassroomErrorBoundary from "./classroom/error";

const mockParams = vi.fn().mockReturnValue({ profileId: "child-42" });
vi.mock("next/navigation", () => ({
  useParams: () => mockParams(),
}));

beforeEach(() => {
  mockParams.mockReturnValue({ profileId: "child-42" });
});

describe("Global Error Boundary (error.tsx)", () => {
  it("renders friendly error message and headline", () => {
    const resetFn = vi.fn();
    render(<ErrorBoundary error={new Error("Test crash")} reset={resetFn} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /something took an unexpected turn/i,
      })
    ).toBeDefined();

    expect(
      screen.getByText(/your work is saved\. you can try refreshing this page or return home/i)
    ).toBeDefined();
  });

  it("calls reset when Try Again button is clicked", () => {
    const resetFn = vi.fn();
    render(<ErrorBoundary error={new Error("Test crash")} reset={resetFn} />);

    const retryButton = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryButton);

    expect(resetFn).toHaveBeenCalledTimes(1);
  });

  it("provides a return home link", () => {
    const resetFn = vi.fn();
    render(<ErrorBoundary error={new Error("Test crash")} reset={resetFn} />);

    const homeLink = screen.getByRole("link", { name: /back to my storybook/i });
    expect(homeLink).toHaveAttribute("href", "/");
  });
});

describe("Student Error Boundary (app/s/[profileId]/error.tsx)", () => {
  it("renders friendly child headline and supportive copy", () => {
    const resetFn = vi.fn();
    render(<StudentErrorBoundary error={new Error("Student crash")} reset={resetFn} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /the magic pencil took a break/i,
      })
    ).toBeDefined();

    expect(
      screen.getByText(/your stories are safe! you can try this again or head back to your bookshelf/i)
    ).toBeDefined();
  });

  it("calls reset when Try again button is clicked", () => {
    const resetFn = vi.fn();
    render(<StudentErrorBoundary error={new Error("Student crash")} reset={resetFn} />);

    const retryButton = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryButton);

    expect(resetFn).toHaveBeenCalledTimes(1);
  });

  it("provides Back to Bookshelf link with student profile path", () => {
    const resetFn = vi.fn();
    render(<StudentErrorBoundary error={new Error("Student crash")} reset={resetFn} />);

    const bookshelfLink = screen.getByRole("link", { name: /back to bookshelf/i });
    expect(bookshelfLink).toHaveAttribute("href", "/s/child-42");
  });
});

describe("Classroom Error Boundary (app/classroom/error.tsx)", () => {
  it("renders educator copy and headline", () => {
    const resetFn = vi.fn();
    render(<ClassroomErrorBoundary error={new Error("Classroom crash")} reset={resetFn} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /unable to load classroom/i,
      })
    ).toBeDefined();

    expect(
      screen.getByText(/we encountered an issue loading your classroom details/i)
    ).toBeDefined();
  });

  it("calls reset when Try again button is clicked", () => {
    const resetFn = vi.fn();
    render(<ClassroomErrorBoundary error={new Error("Classroom crash")} reset={resetFn} />);

    const retryButton = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryButton);

    expect(resetFn).toHaveBeenCalledTimes(1);
  });

  it("provides Back to Classroom link to dashboard", () => {
    const resetFn = vi.fn();
    render(<ClassroomErrorBoundary error={new Error("Classroom crash")} reset={resetFn} />);

    const classroomLink = screen.getByRole("link", { name: /back to classroom/i });
    expect(classroomLink).toHaveAttribute("href", "/classroom");
  });
});
