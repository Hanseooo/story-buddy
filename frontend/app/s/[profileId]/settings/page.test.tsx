import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import SettingsPage from "./page";
import { AVATAR_IDS } from "@/lib/avatars";

// Mock next/navigation for useParams
vi.mock("next/navigation", () => ({
  useParams: () => ({ profileId: "student-123" }),
}));

const mockUpdateUser = vi.hoisted(() => vi.fn());
const mockGetSession = vi.hoisted(() => vi.fn());
const mockFrom = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      updateUser: mockUpdateUser,
      getSession: mockGetSession,
    },
    from: mockFrom,
  },
}));

// Default: from returns avatar_id: null (avatar tests override per-test)
function setupDefaultFrom(avatar_id: string | null = null) {
  mockFrom.mockReturnValue({
    select: vi.fn().mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: { avatar_id } }),
      }),
    }),
  });
}

describe("Settings — password change", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupDefaultFrom();
  });

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

// spec §8 test 9 — 24 radio options, current one checked
it("renders 24 avatar options as a radio group with current one checked", async () => {
  mockGetSession.mockResolvedValue({ data: { session: { access_token: "tok" } } });
  setupDefaultFrom("peeps-01");

  render(<SettingsPage />);
  await waitFor(() => {
    const radios = screen.getAllByRole("radio");
    expect(radios.length).toBe(AVATAR_IDS.length); // 24
    const checked = screen.getByRole("radio", { checked: true });
    expect(checked.getAttribute("value")).toBe("peeps-01");
  });
});

// spec §8 test 10 — PATCH fired with bearer token
it("fires PATCH /me/avatar with bearer token on selection", async () => {
  mockGetSession.mockResolvedValue({ data: { session: { access_token: "my-token" } } });
  setupDefaultFrom(null);

  const fetchMock = vi.fn().mockResolvedValue({ ok: true });
  vi.stubGlobal("fetch", fetchMock);

  render(<SettingsPage />);
  await waitFor(() => screen.getAllByRole("radio"));

  const firstRadio = screen.getAllByRole("radio")[0];
  fireEvent.click(firstRadio);

  await waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/me/avatar"),
      expect.objectContaining({
        method: "PATCH",
        headers: expect.objectContaining({
          Authorization: "Bearer my-token",
        }),
      })
    );
  });

  vi.unstubAllGlobals();
});

// spec §8 test 11 — failed PATCH reverts and surfaces message
it("reverts selection and shows message on failed PATCH", async () => {
  mockGetSession.mockResolvedValue({ data: { session: { access_token: "tok" } } });
  setupDefaultFrom("peeps-01");

  const fetchMock = vi.fn().mockResolvedValue({ ok: false });
  vi.stubGlobal("fetch", fetchMock);

  render(<SettingsPage />);
  await waitFor(() => screen.getAllByRole("radio"));

  const secondRadio = screen.getAllByRole("radio")[1]; // peeps-02
  fireEvent.click(secondRadio);

  await waitFor(() => {
    // reverted — peeps-01 is checked again
    const checked = screen.getByRole("radio", { checked: true });
    expect(checked.getAttribute("value")).toBe("peeps-01");
    // error message shown
    expect(screen.getByRole("status")).toBeDefined();
  });

  vi.unstubAllGlobals();
});
