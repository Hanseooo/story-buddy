import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { expect, it, describe, vi } from "vitest";
import SettingsPage from "./page";

vi.mock("next/navigation", () => ({
  useParams: () => ({ classroomId: "cls-123" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
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
