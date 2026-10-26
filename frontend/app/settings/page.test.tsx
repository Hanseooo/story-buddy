import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import TeacherSettingsPage from "./page";

const { updateUser, getUser, from, getSession } = vi.hoisted(() => ({
  updateUser: vi.fn(),
  getUser: vi.fn(),
  from: vi.fn(),
  getSession: vi.fn(),
}));
vi.mock("@supabase/ssr", () => ({
  createBrowserClient: () => ({ auth: { getUser, getSession }, from }),
}));

beforeEach(() => {
  vi.clearAllMocks();
  getSession.mockResolvedValue({ data: { session: { access_token: "teacher-session" } } });
  vi.stubGlobal("fetch", vi.fn(async (_url, options) => {
    const result = await updateUser(JSON.parse(options.body));
    return { ok: !result.error, status: result.error?.status ?? 400,
      json: async () => result.error ? { detail: result.error.code } : {} };
  }));
  getUser.mockResolvedValue({ data: { user: { id: "teacher-test", email: "teacher@example.invalid" } } });
  from.mockReturnValue({ select: () => ({ eq: () => ({ single: async () => ({ data: { display_name: "Teacher" } }) }) }) });
});

describe("Teacher settings — password change", () => {
  it("sends current proof unchanged, prevents duplicate submission and confirms inline", async () => {
    let finish!: (value: { error: null }) => void;
    updateUser.mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    render(<TeacherSettingsPage />);
    await screen.findByRole("heading", { name: /account settings/i });
    fireEvent.change(screen.getByLabelText(/^current password$/i), { target: { value: "oldpass123" } });
    fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: "        " } });
    fireEvent.change(screen.getByLabelText(/^confirm new password$/i), { target: { value: "        " } });
    fireEvent.click(screen.getByRole("button", { name: /show passwords/i }));
    expect(screen.getByLabelText(/^current password$/i)).toHaveAttribute("type", "text");
    fireEvent.click(screen.getByRole("button", { name: /^change password$/i }));
    expect(screen.getByRole("button", { name: /saving/i })).toBeDisabled();
    fireEvent.submit(screen.getByRole("button", { name: /saving/i }).closest("form")!);
    await waitFor(() => expect(updateUser).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(updateUser).toHaveBeenCalledWith({ current_password: "oldpass123", password: "        ", confirmation: "        " }));
    finish({ error: null });
    await screen.findByText(/password changed successfully/i);
    expect(screen.getByLabelText(/^current password$/i)).toHaveValue("");
    expect(screen.getByRole("heading", { name: /account settings/i })).toBeDefined();
  });

  it("rejects invalid lengths and shows safe current-password/network failures with retry", async () => {
    render(<TeacherSettingsPage />);
    await screen.findByRole("heading", { name: /account settings/i });
    fireEvent.change(screen.getByLabelText(/^current password$/i), { target: { value: "oldpass123" } });
    for (const password of ["😀😀😀😀", "😀".repeat(19)]) {
      fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: password } });
      fireEvent.change(screen.getByLabelText(/^confirm new password$/i), { target: { value: password } });
      fireEvent.click(screen.getByRole("button", { name: /^change password$/i }));
      expect(screen.getByRole("alert")).toBeDefined();
      expect(updateUser).not.toHaveBeenCalled();
    }
    fireEvent.change(screen.getByLabelText(/^new password$/i), { target: { value: "newpass123" } });
    fireEvent.change(screen.getByLabelText(/^confirm new password$/i), { target: { value: "newpass123" } });
    updateUser.mockResolvedValueOnce({ error: { code: "current_password_mismatch", message: "private upstream detail" } });
    fireEvent.click(screen.getByRole("button", { name: /^change password$/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/current password.*incorrect/i));
    expect(screen.queryByText(/private upstream detail/i)).toBeNull();
    updateUser.mockRejectedValueOnce(new Error("private network detail"));
    fireEvent.click(screen.getByRole("button", { name: /^change password$/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/connection/i));
    expect(screen.getByRole("button", { name: /^change password$/i })).not.toBeDisabled();
  });
});
