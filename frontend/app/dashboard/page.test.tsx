import { render, screen, fireEvent } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import Dashboard from "./page";

const mockSignOut = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      signOut: mockSignOut,
    },
  },
}));

describe("Dashboard Page", () => {
  it("renders dashboard placeholder and supports sign out", () => {
    render(<Dashboard />);
    expect(screen.getByRole("heading", { name: /dashboard/i })).toBeDefined();
    expect(screen.getByText(/classroom tools are not built yet/i)).toBeDefined();
    const logoutBtn = screen.getByRole("button", { name: /log out/i });
    expect(logoutBtn).toBeDefined();

    fireEvent.click(logoutBtn);
    expect(mockSignOut).toHaveBeenCalled();
  });
});
