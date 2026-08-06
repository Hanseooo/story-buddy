import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi, beforeEach } from "vitest";
import Login from "./page";
import Signup from "../signup/page";

const mockSignIn = vi.fn();
const mockSignUp = vi.fn();

vi.mock("@supabase/ssr", () => ({
  createBrowserClient: () => ({
    auth: {
      signInWithPassword: mockSignIn,
      signUp: mockSignUp,
    },
  }),
}));

describe("Teacher Auth Pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form with Inter font", () => {
    const { container } = render(<Login />);
    expect(screen.getByRole("heading", { name: /log in/i })).toBeDefined();
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/password/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /log in/i })).toBeDefined();
    expect(container.firstChild).toHaveClass("font-sans");
  });

  it("handles login submit error", async () => {
    mockSignIn.mockResolvedValueOnce({ error: { message: "Invalid login credentials" } });
    render(<Login />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "teacher@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith({ email: "teacher@school.org", password: "secret123" });
      expect(screen.getByRole("alert")).toHaveTextContent("Invalid login credentials");
    });
  });

  it("renders signup form with Inter font and handles submit", async () => {
    mockSignUp.mockResolvedValueOnce({ error: null });
    const { container } = render(<Signup />);
    expect(screen.getByRole("heading", { name: /sign up/i })).toBeDefined();
    expect(container.firstChild).toHaveClass("font-sans");

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "newteacher@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign up/i }));

    await waitFor(() => {
      expect(mockSignUp).toHaveBeenCalledWith({ email: "newteacher@school.org", password: "secret123" });
      expect(screen.getByRole("alert")).toHaveTextContent(/check your email/i);
    });
  });
});
