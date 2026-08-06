import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import SettingsPage from "./page";

const mockUpdateUser = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      updateUser: mockUpdateUser,
    },
  },
}));

describe("Settings — password change", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders new-password and confirm-password fields", () => {
    render(<SettingsPage />);
    expect(screen.getByLabelText(/new password/i)).toBeDefined();
    expect(screen.getByLabelText(/confirm password/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /save password/i })).toBeDefined();
  });

  it("shows teacher reminder on success", async () => {
    mockUpdateUser.mockResolvedValueOnce({ error: null });
    render(<SettingsPage />);

    fireEvent.change(screen.getByLabelText(/new password/i), { target: { value: "newpass123" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "newpass123" } });
    fireEvent.click(screen.getByRole("button", { name: /save password/i }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(
        /if you forget it, ask your teacher/i
      );
    });
    expect(mockUpdateUser).toHaveBeenCalledWith({ password: "newpass123" });
  });

  it("validates password match before calling updateUser", async () => {
    render(<SettingsPage />);

    fireEvent.change(screen.getByLabelText(/new password/i), { target: { value: "abc" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "xyz" } });
    fireEvent.click(screen.getByRole("button", { name: /save password/i }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/passwords don't match/i);
    });
    expect(mockUpdateUser).not.toHaveBeenCalled();
  });

  it("stays on page after successful save (no redirect)", async () => {
    mockUpdateUser.mockResolvedValueOnce({ error: null });
    render(<SettingsPage />);

    fireEvent.change(screen.getByLabelText(/new password/i), { target: { value: "pass" } });
    fireEvent.change(screen.getByLabelText(/confirm password/i), { target: { value: "pass" } });
    fireEvent.click(screen.getByRole("button", { name: /save password/i }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toBeDefined();
      expect(screen.getByRole("heading", { name: /change password/i })).toBeDefined();
    });
  });
});
