import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, describe, vi } from "vitest";
import SettingsPage from "./page";

const REPLACE = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ classroomId: "cls-123" }),
  useRouter: () => ({ push: vi.fn(), replace: REPLACE }),
}));

vi.mock("@supabase/ssr", () => ({
  createBrowserClient: () => ({
    from: () => ({
      select: () => ({
        eq: () => ({
          single: () =>
            Promise.resolve({ data: { name: "Grade 3", code: "XYZ789" } }),
        }),
      }),
    }),
    auth: {
      getSession: () =>
        Promise.resolve({ data: { session: { access_token: "tok" } } }),
    },
  }),
}));

describe("Classroom settings danger zone", () => {
  it("test 19: delete button is disabled until exact classroom name is typed", async () => {
    render(<SettingsPage />);

    // Wait for classroom name to load
    const input = await screen.findByPlaceholderText(/type "grade 3"/i);
    const deleteBtn = screen.getByRole("button", { name: /delete classroom/i });

    expect(deleteBtn).toHaveAttribute("disabled");

    fireEvent.change(input, { target: { value: "Grade 3" } });
    await waitFor(() =>
      expect(deleteBtn).not.toHaveAttribute("disabled")
    );

    fireEvent.change(input, { target: { value: "Grade 3 " } }); // trailing space
    await waitFor(() => expect(deleteBtn).toHaveAttribute("disabled"));
  });
});

describe("failed teacher mutations are reported, not swallowed (#77)", () => {
  it("a rejected rename does not claim success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403 }));
    render(<SettingsPage />);

    const nameInput = await screen.findByDisplayValue("Grade 3");
    fireEvent.change(nameInput, { target: { value: "Grade 4" } });
    fireEvent.click(screen.getByRole("button", { name: /save/i }));

    await waitFor(() =>
      expect(screen.queryByText(/classroom renamed/i)).not.toBeInTheDocument()
    );
    expect(await screen.findByText(/could not rename/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("a rejected delete does not navigate away as if it worked", async () => {
    REPLACE.mockClear();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    render(<SettingsPage />);

    const input = await screen.findByPlaceholderText(/type "grade 3"/i);
    fireEvent.change(input, { target: { value: "Grade 3" } });
    fireEvent.click(screen.getByRole("button", { name: /delete classroom/i }));
    // The button arms the confirm dialog; the DELETE fires from there.
    // `hidden: true` because ConfirmDialog is a native <dialog> and jsdom does not
    // implement showModal(), so its contents stay outside the accessibility tree.
    fireEvent.click(
      await screen.findByRole("button", { name: /yes, delete/i, hidden: true })
    );

    expect(await screen.findByText(/could not delete/i)).toBeInTheDocument();
    expect(REPLACE).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});
