import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ErrorBoundary from "./error";
import StudentErrorBoundary from "./s/[profileId]/error";
import ClassroomErrorBoundary from "./classroom/error";
import AnnotateErrorBoundary from "./(research)/annotate/error";
import AdjudicateErrorBoundary from "./(research)/adjudicate/error";
import ResearchErrorBoundary from "./(research)/research/error";
import GalleryErrorBoundary from "./s/[profileId]/gallery/error";

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

  it("offers a logout escape hatch without exposing the raw error", () => {
    const resetFn = vi.fn();
    render(<ErrorBoundary error={new Error("secret backend token")} reset={resetFn} />);

    const logoutButton = screen.getByRole("button", { name: /log out/i });
    const logoutForm = logoutButton.closest("form");

    expect(logoutForm).toHaveAttribute("action", "/auth/signout");
    expect(logoutForm).toHaveAttribute("method", "post");
    expect(screen.queryByText("secret backend token")).toBeNull();
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

  it("offers a logout escape hatch", () => {
    render(<StudentErrorBoundary error={new Error("Student crash")} reset={vi.fn()} />);

    const logoutButton = screen.getByRole("button", { name: /log out/i });
    const logoutForm = logoutButton.closest("form");

    expect(logoutForm).toHaveAttribute("action", "/auth/signout");
    expect(logoutForm).toHaveAttribute("method", "post");
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

  it("offers a logout escape hatch", () => {
    render(<ClassroomErrorBoundary error={new Error("Classroom crash")} reset={vi.fn()} />);

    const logoutButton = screen.getByRole("button", { name: /log out/i });
    const logoutForm = logoutButton.closest("form");

    expect(logoutForm).toHaveAttribute("action", "/auth/signout");
    expect(logoutForm).toHaveAttribute("method", "post");
  });
});

describe("Annotate Error Boundary (app/(research)/annotate/error.tsx)", () => {
  it("renders annotation error copy and headline", () => {
    const resetFn = vi.fn();
    render(<AnnotateErrorBoundary error={new Error("Annotate crash")} reset={resetFn} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /unable to load annotation/i,
      })
    ).toBeDefined();

    expect(
      screen.getByText(/we encountered an issue loading the annotation queue/i)
    ).toBeDefined();
  });

  it("calls reset when Try again button is clicked", () => {
    const resetFn = vi.fn();
    render(<AnnotateErrorBoundary error={new Error("Annotate crash")} reset={resetFn} />);

    const retryButton = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryButton);

    expect(resetFn).toHaveBeenCalledTimes(1);
  });

  it("provides Back to Research Lab link", () => {
    const resetFn = vi.fn();
    render(<AnnotateErrorBoundary error={new Error("Annotate crash")} reset={resetFn} />);

    const backLink = screen.getByRole("link", { name: /back to research lab/i });
    expect(backLink).toHaveAttribute("href", "/research");
  });

  it("offers a logout escape hatch", () => {
    render(<AnnotateErrorBoundary error={new Error("Annotate crash")} reset={vi.fn()} />);

    const logoutButton = screen.getByRole("button", { name: /log out/i });
    const logoutForm = logoutButton.closest("form");

    expect(logoutForm).toHaveAttribute("action", "/auth/signout");
    expect(logoutForm).toHaveAttribute("method", "post");
  });
});

describe("Adjudicate Error Boundary (app/(research)/adjudicate/error.tsx)", () => {
  it("renders adjudication error copy and headline", () => {
    const resetFn = vi.fn();
    render(<AdjudicateErrorBoundary error={new Error("Adjudicate crash")} reset={resetFn} />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /unable to load adjudication/i,
      })
    ).toBeDefined();

    expect(
      screen.getByText(/we encountered an issue loading conflicted pairs/i)
    ).toBeDefined();
  });

  it("calls reset when Try again button is clicked", () => {
    const resetFn = vi.fn();
    render(<AdjudicateErrorBoundary error={new Error("Adjudicate crash")} reset={resetFn} />);

    const retryButton = screen.getByRole("button", { name: /try again/i });
    fireEvent.click(retryButton);

    expect(resetFn).toHaveBeenCalledTimes(1);
  });

  it("provides Back to Research Lab link", () => {
    const resetFn = vi.fn();
    render(<AdjudicateErrorBoundary error={new Error("Adjudicate crash")} reset={resetFn} />);

    const backLink = screen.getByRole("link", { name: /back to research lab/i });
    expect(backLink).toHaveAttribute("href", "/research");
  });

  it("offers a logout escape hatch", () => {
    render(<AdjudicateErrorBoundary error={new Error("Adjudicate crash")} reset={vi.fn()} />);

    const logoutButton = screen.getByRole("button", { name: /log out/i });
    const logoutForm = logoutButton.closest("form");

    expect(logoutForm).toHaveAttribute("action", "/auth/signout");
    expect(logoutForm).toHaveAttribute("method", "post");
  });
});

describe("Research Error Boundary (app/(research)/research/error.tsx)", () => {
  it("does not render the caught error message and offers logout recovery", () => {
    render(<ResearchErrorBoundary error={new Error("database secret")} />);

    const logoutButton = screen.getByRole("button", { name: /log out/i });
    const logoutForm = logoutButton.closest("form");

    expect(logoutForm).toHaveAttribute("action", "/auth/signout");
    expect(logoutForm).toHaveAttribute("method", "post");
    expect(screen.queryByText("database secret")).toBeNull();
  });
});

describe("Gallery Error Boundary (app/s/[profileId]/gallery/error.tsx)", () => {
  it("offers logout recovery", () => {
    render(<GalleryErrorBoundary error={new Error("Gallery crash")} reset={vi.fn()} />);

    const logoutButton = screen.getByRole("button", { name: /log out/i });
    const logoutForm = logoutButton.closest("form");

    expect(logoutForm).toHaveAttribute("action", "/auth/signout");
    expect(logoutForm).toHaveAttribute("method", "post");
  });
});
