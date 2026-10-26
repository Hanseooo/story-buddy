import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import PasswordForm from "./PasswordForm";

const { replace, refresh, getSession } = vi.hoisted(() => ({ replace: vi.fn(), refresh: vi.fn(), getSession: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace, refresh }) }));
vi.mock("@/lib/supabaseClient", () => ({ supabase: { auth: { getSession } } }));
beforeEach(() => {
  vi.clearAllMocks();
  getSession.mockResolvedValue({ data: { session: { access_token: "student-session" } } });
});

it("identifies the child, sends exact input once and enters the introduction", async () => {
  const request = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ next_path: "/s/student-1/introduction" }) });
  vi.stubGlobal("fetch", request);
  render(<PasswordForm profileId="student-1" displayNickname="Juan" />);
  expect(screen.getByText(/signed in as juan/i)).toBeDefined();
  fireEvent.change(screen.getByLabelText("Current secret word"), { target: { value: "teacher-word-12" } });
  fireEvent.change(screen.getByLabelText("New password"), { target: { value: "        " } });
  fireEvent.change(screen.getByLabelText("Type your new password again"), { target: { value: "        " } });
  fireEvent.click(screen.getByRole("button", { name: /save my password/i }));
  fireEvent.submit(screen.getByRole("button", { name: /saving/i }).closest("form")!);
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/s/student-1/introduction"));
  expect(request).toHaveBeenCalledTimes(1);
  expect(JSON.parse(request.mock.calls[0][1].body)).toEqual({
    current_password: "teacher-word-12", password: "        ", confirmation: "        ",
  });
  expect(screen.getByRole("button", { name: /log out/i })).toBeDefined();
});

it("recovers a lost save response from trusted state without another password change", async () => {
  const request = vi.fn().mockRejectedValueOnce(new TypeError("network"))
    .mockResolvedValueOnce({ ok: true, json: async () => ({ password_change_required: false, next_path: "/s/student-1/introduction" }) });
  vi.stubGlobal("fetch", request);
  render(<PasswordForm profileId="student-1" displayNickname="Juan" />);
  fireEvent.change(screen.getByLabelText("Current secret word"), { target: { value: "teacher-word-12" } });
  fireEvent.change(screen.getByLabelText("New password"), { target: { value: "chosen-password" } });
  fireEvent.change(screen.getByLabelText("Type your new password again"), { target: { value: "chosen-password" } });
  fireEvent.click(screen.getByRole("button", { name: /save my password/i }));
  await waitFor(() => expect(replace).toHaveBeenCalledWith("/s/student-1/introduction"));
  expect(request).toHaveBeenCalledTimes(2);
  expect(request.mock.calls[1][0]).toContain("/me/onboarding");
});
