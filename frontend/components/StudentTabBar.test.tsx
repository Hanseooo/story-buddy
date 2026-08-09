import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import * as Nav from "next/navigation";
import { StudentTabBar } from "./StudentTabBar";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const usePathname = vi.mocked(Nav.usePathname);
const PROFILE_ID = "student-1";

describe("StudentTabBar", () => {
  // Test 9 — three tabs each with a text label beside its icon
  it("renders three tabs each with a visible text label", () => {
    usePathname.mockReturnValue(`/s/${PROFILE_ID}`);

    render(<StudentTabBar profileId={PROFILE_ID} />);

    expect(screen.getByText("Bookshelf")).toBeInTheDocument();
    expect(screen.getByText("Gallery")).toBeInTheDocument();
    expect(screen.getByText("Profile")).toBeInTheDocument();

    expect(screen.getByText("📚")).toBeInTheDocument();
    expect(screen.getByText("🖼️")).toBeInTheDocument();
    expect(screen.getByText("👤")).toBeInTheDocument();
  });

  // Test 10 — active tab marked aria-current="page"
  it("marks the tab matching the current pathname as aria-current=page", () => {
    // Bookshelf active
    usePathname.mockReturnValue(`/s/${PROFILE_ID}`);
    const { rerender } = render(<StudentTabBar profileId={PROFILE_ID} />);
    expect(screen.getByText("Bookshelf").closest("a")).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Gallery").closest("a")).not.toHaveAttribute(
      "aria-current",
    );

    // Gallery active
    usePathname.mockReturnValue(`/s/${PROFILE_ID}/gallery`);
    rerender(<StudentTabBar profileId={PROFILE_ID} />);
    expect(screen.getByText("Gallery").closest("a")).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByText("Bookshelf").closest("a")).not.toHaveAttribute(
      "aria-current",
    );
  });
});
