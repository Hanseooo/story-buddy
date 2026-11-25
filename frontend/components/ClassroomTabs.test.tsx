import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import * as Nav from "next/navigation";
import ClassroomTabs from "./ClassroomTabs";

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

// PendingCount reads Supabase; nothing is waiting in these tests.
vi.mock("@supabase/ssr", () => {
  const query = {
    select: () => query,
    eq: () => query,
    is: () => query,
    then: (resolve: (v: { count: number }) => void) => resolve({ count: 0 }),
  };
  return { createBrowserClient: () => ({ from: () => query }) };
});

const usePathname = vi.mocked(Nav.usePathname);

describe("ClassroomTabs", () => {
  it("marks the tab matching the current pathname as aria-current=page", () => {
    usePathname.mockReturnValue("/classroom/cls-1");
    const { rerender } = render(<ClassroomTabs />);
    expect(screen.getByRole("link", { name: "Roster" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Books" })).not.toHaveAttribute("aria-current");

    usePathname.mockReturnValue("/classroom/cls-1/books");
    rerender(<ClassroomTabs />);
    expect(screen.getByRole("link", { name: "Books" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Roster" })).not.toHaveAttribute("aria-current");

    // Settings and Add students belong to neither tab.
    usePathname.mockReturnValue("/classroom/cls-1/settings");
    rerender(<ClassroomTabs />);
    expect(screen.getByRole("link", { name: "Roster" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Books" })).not.toHaveAttribute("aria-current");
  });
});
