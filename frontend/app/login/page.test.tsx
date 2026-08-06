import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import Login from "./page";
import Signup from "../signup/page";

const mockSignIn = vi.hoisted(() => vi.fn());
const mockSignUp = vi.hoisted(() => vi.fn());
const mockPush = vi.hoisted(() => vi.fn());
const mockSearchParamsGet = vi.hoisted(() => vi.fn(() => null as string | null));

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      signInWithPassword: mockSignIn,
      signUp: mockSignUp,
    },
  },
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
  useSearchParams: () => ({ get: mockSearchParamsGet }),
}));

describe("Teacher Auth Pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParamsGet.mockImplementation(() => null);
  });

  it("renders login form with Inter font", () => {
    const { container } = render(<Login />);
    expect(screen.getByRole("heading", { name: /log in/i })).toBeDefined();
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/password/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /log in/i })).toBeDefined();
    expect(container.firstChild).toHaveClass("font-sans");
  });

  it("redirects to /dashboard on successful login", async () => {
    mockSignIn.mockResolvedValueOnce({ error: null });
    render(<Login />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "teacher@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/dashboard");
    });
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

  it("shows email-confirmed message when ?message=email-confirmed is in the URL", () => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "message" ? "email-confirmed" : null
    );
    render(<Login />);
    expect(screen.getByRole("status")).toHaveTextContent(/your email is confirmed/i);
  });

  it("renders signup form with Inter font and always shows 'check your email'", async () => {
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

  it("shows 'check your email' even when signUp returns an error (no account-existence disclosure)", async () => {
    mockSignUp.mockResolvedValueOnce({ error: { message: "User already registered" } });
    render(<Signup />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "existing@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /sign up/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/check your email/i);
      expect(screen.queryByText(/user already registered/i)).toBeNull();
    });
  });
});
