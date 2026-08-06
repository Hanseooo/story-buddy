import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import JoinCodePage, { CRED_ERROR, NET_ERROR } from "./page";

const mockPush = vi.hoisted(() => vi.fn());
const mockSignIn = vi.hoisted(() => vi.fn());

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      signInWithPassword: mockSignIn,
    },
  },
}));

// Helper: render and wait for nickname step
async function renderJoinCode(code = "abcdef") {
  render(<JoinCodePage params={Promise.resolve({ code })} />);
  await waitFor(() => expect(screen.queryByText(/what's your nickname/i)).not.toBeNull());
}

describe("Join code page — §9.6–10", () => {
  beforeEach(() => vi.clearAllMocks());

  it("§9.10 — malformed code segment shows the code and a back link", async () => {
    render(<JoinCodePage params={Promise.resolve({ code: "abc" })} />);
    await waitFor(() => {
      expect(screen.getByText("abc")).toBeDefined();
      expect(screen.getByRole("link", { name: /try again/i })).toHaveAttribute("href", "/join");
    });
  });

  it("§9.8 — shows nickname step on load", async () => {
    await renderJoinCode();
    expect(screen.getByRole("heading", { name: /what's your nickname/i })).toBeDefined();
  });

  it("§9.8 — advances to password step when nickname submitted", async () => {
    await renderJoinCode();
    fireEvent.change(screen.getByLabelText(/nickname/i), { target: { value: "Juan" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /create your password/i })).toBeDefined()
    );
  });

  it("§9.6 — wrong credential produces CRED_ERROR (identical message regardless of cause)", async () => {
    mockSignIn.mockResolvedValue({ data: { user: null }, error: { message: "Invalid login credentials" } });
    await renderJoinCode();

    fireEvent.change(screen.getByLabelText(/nickname/i), { target: { value: "Juan" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => screen.getByRole("heading", { name: /create your password/i }));

    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "wrongpass" } });
    fireEvent.click(screen.getByRole("button", { name: /join class/i }));

    await waitFor(() => {
      // §9.6: asserted as string equality, not regex
      expect(screen.getByRole("alert").textContent).toBe(CRED_ERROR);
    });
  });

  it("§9.6 — all three failure scenarios produce the same CRED_ERROR string", async () => {
    for (const scenario of ["wrong-code", "wrong-nickname", "wrong-password"]) {
      cleanup();
      vi.clearAllMocks();
      mockSignIn.mockResolvedValue({ data: { user: null }, error: { message: scenario } });
      await renderJoinCode();

      fireEvent.change(screen.getByLabelText(/nickname/i), { target: { value: "test" } });
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      await waitFor(() => screen.getByRole("heading", { name: /create your password/i }));

      fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "pass" } });
      fireEvent.click(screen.getByRole("button", { name: /join class/i }));

      await waitFor(() => {
        expect(screen.getByRole("alert").textContent).toBe(CRED_ERROR);
      });
    }
  });

  it("§9.7 — network failure produces NET_ERROR, not CRED_ERROR", async () => {
    mockSignIn.mockRejectedValue(new Error("Network request failed"));
    await renderJoinCode();

    fireEvent.change(screen.getByLabelText(/nickname/i), { target: { value: "Juan" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => screen.getByRole("heading", { name: /create your password/i }));

    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "pass" } });
    fireEvent.click(screen.getByRole("button", { name: /join class/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert").textContent).toBe(NET_ERROR);
      expect(screen.getByRole("alert").textContent).not.toBe(CRED_ERROR);
    });
  });

  it("§9.8 — failed login returns to nickname step with nickname preserved", async () => {
    mockSignIn.mockResolvedValue({ data: { user: null }, error: { message: "bad" } });
    await renderJoinCode();

    fireEvent.change(screen.getByLabelText(/nickname/i), { target: { value: "Maria" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => screen.getByRole("heading", { name: /create your password/i }));

    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "pass" } });
    fireEvent.click(screen.getByRole("button", { name: /join class/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /what's your nickname/i })).toBeDefined();
      expect(screen.getByLabelText(/nickname/i)).toHaveValue("Maria");
    });
  });

  it("password is visible by default (type=text)", async () => {
    await renderJoinCode();
    fireEvent.change(screen.getByLabelText(/nickname/i), { target: { value: "Juan" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => screen.getByRole("heading", { name: /create your password/i }));
    expect(screen.getByLabelText(/password/i)).toHaveAttribute("type", "text");
  });

  it("show/hide toggle changes password visibility", async () => {
    await renderJoinCode();
    fireEvent.change(screen.getByLabelText(/nickname/i), { target: { value: "Juan" } });
    fireEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => screen.getByRole("heading", { name: /create your password/i }));

    const passwordInput = screen.getByLabelText(/password/i);
    expect(passwordInput).toHaveAttribute("type", "text");
    fireEvent.click(screen.getByRole("button", { name: /hide/i }));
    expect(passwordInput).toHaveAttribute("type", "password");
  });
});
