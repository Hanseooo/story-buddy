import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import Login from "./page";
import Signup from "../signup/page";

const mockSignIn = vi.hoisted(() => vi.fn());
const mockSignUp = vi.hoisted(() => vi.fn());
const mockPush = vi.hoisted(() => vi.fn());
const mockSearchParamsGet = vi.hoisted(() => vi.fn(() => null as string | null));

const mockFrom = vi.hoisted(() => vi.fn());
const mockSelect = vi.hoisted(() => vi.fn());
const mockEq = vi.hoisted(() => vi.fn());
const mockSingle = vi.hoisted(() => vi.fn());

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      signInWithPassword: mockSignIn,
      signUp: mockSignUp,
    },
    from: mockFrom,
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
    
    mockFrom.mockReturnValue({ select: mockSelect });
    mockSelect.mockReturnValue({ eq: mockEq });
    mockEq.mockReturnValue({ single: mockSingle });
    mockSingle.mockResolvedValue({ data: { role: "teacher" } });
  });

  it("renders login form with Inter font", () => {
    const { container } = render(<Login />);
    expect(screen.getByRole("heading", { name: /log in/i })).toBeDefined();
    expect(screen.getByLabelText(/email/i)).toBeDefined();
    expect(screen.getByLabelText(/password/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /log in/i })).toBeDefined();
    expect(container.firstChild).toHaveClass("font-sans");
  });

  it("redirects to /classroom on successful login", async () => {
    mockSignIn.mockResolvedValueOnce({ data: { user: { id: "123" } }, error: null });
    render(<Login />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "teacher@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/classroom");
    });
  });

  it.each([
    ["teacher", false, "/classroom"],
    ["researcher", false, "/annotate"],
    ["researcher", true, "/adjudicate"],
    ["student", false, "/s/user-1"],
  ])("routes %s accounts to their role surface", async (role, isAdjudicator, expectedPath) => {
    mockSignIn.mockResolvedValueOnce({ data: { user: { id: "user-1" } }, error: null });
    mockSingle.mockResolvedValueOnce({
      data: { role, is_adjudicator: isAdjudicator },
    });
    render(<Login />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "person@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith(expectedPath);
    });
  });

  it("ignores an external next target and uses the account role", async () => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "next" ? "https://evil.example" : null
    );
    mockSignIn.mockResolvedValueOnce({ data: { user: { id: "user-1" } }, error: null });
    mockSingle.mockResolvedValueOnce({ data: { role: "teacher" } });
    render(<Login />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "teacher@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/classroom");
    });
    expect(mockPush).not.toHaveBeenCalledWith("https://evil.example");
  });

  it("does not let a researcher resume a student next target", async () => {
    mockSearchParamsGet.mockImplementation((key: string) =>
      key === "next" ? "/s/student-1/write" : null
    );
    mockSignIn.mockResolvedValueOnce({ data: { user: { id: "researcher-1" } }, error: null });
    mockSingle.mockResolvedValueOnce({ data: { role: "researcher", is_adjudicator: false } });
    render(<Login />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "researcher@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/annotate");
    });
    expect(mockPush).not.toHaveBeenCalledWith("/s/student-1/write");
  });

  it("does not fall back to the student tree when the profile lookup fails", async () => {
    mockSignIn.mockResolvedValueOnce({ data: { user: { id: "researcher-1" } }, error: null });
    mockSingle.mockResolvedValueOnce({ data: null, error: { message: "profile lookup failed" } });
    render(<Login />);

    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "researcher@school.org" } });
    fireEvent.change(screen.getByLabelText(/password/i), { target: { value: "secret123" } });
    fireEvent.click(screen.getByRole("button", { name: /log in/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/couldn't load your account/i);
    });
    expect(mockPush).not.toHaveBeenCalled();
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
      expect(mockSignUp).toHaveBeenCalledWith({ email: "newteacher@school.org", password: "secret123", options: expect.any(Object) });
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
