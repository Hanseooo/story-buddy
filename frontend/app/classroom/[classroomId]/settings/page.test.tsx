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
            Promise.resolve({ data: { name: "Grade 3", code: "XYZ789", review_notes_enabled: false } }),
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

describe("optional classroom review themes", () => {
  it("saves choices only after a durable response", async () => {
    const themes = [
      { id: "spooky_suspense", name: "Mild suspense/spooky settings", trigger: "Narrative fear", exception: "Friendly magic" },
      { id: "story_conflict", name: "Non-graphic fighting, arguments or bullying", trigger: "Hostile conflict", exception: "Respectful disagreement" },
      { id: "loss_separation", name: "Sadness, loss or separation", trigger: "Narrative grief", exception: "Routine goodbye" },
    ];
    let finishSave!: (response: Response) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json({ theme_ids: [], settings_version: 0, editable: true, themes }))
      .mockImplementationOnce(() => new Promise<Response>(resolve => { finishSave = resolve; }));
    vi.stubGlobal("fetch", fetcher);
    render(<SettingsPage />);
    const toggle = await screen.findByRole("checkbox", { name: /mild suspense/i });
    expect(screen.getAllByRole("checkbox")).toHaveLength(4);
    expect(toggle).not.toBeChecked();
    fireEvent.click(toggle);
    fireEvent.click(screen.getByRole("button", { name: "Save review themes" }));
    expect(screen.queryByText("Review themes saved")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Saving review themes…" })).toBeDisabled();
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ expected_version: 0, theme_ids: ["spooky_suspense"] });
    finishSave(Response.json({ theme_ids: ["spooky_suspense"], settings_version: 1 }));
    expect(await screen.findByText("Review themes saved")).toBeInTheDocument();
    fireEvent.click(toggle);
    expect(screen.getByText(/Turning a theme off.*shared safety checks still apply/i)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("keeps unsaved choices on failure and retries the save", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json({ theme_ids: [], settings_version: 3, editable: true,
      themes: [{ id: "loss_separation", name: "Sadness, loss or separation", trigger: "Grief", exception: "Goodbyes" }] }))
      .mockRejectedValueOnce(new TypeError("offline"))
      .mockResolvedValueOnce(Response.json({ theme_ids: ["loss_separation"], settings_version: 4 }));
    vi.stubGlobal("fetch", fetcher);
    render(<SettingsPage />);
    const toggle = await screen.findByRole("checkbox", { name: /sadness/i });
    fireEvent.click(toggle);
    fireEvent.click(screen.getByRole("button", { name: "Save review themes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Could not save review themes/i);
    expect(toggle).toBeChecked();
    expect(screen.queryByText("Review themes saved")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry saving review themes" }));
    expect(await screen.findByText("Review themes saved")).toBeInTheDocument();
    expect(JSON.parse(fetcher.mock.calls[2][1].body)).toEqual({ expected_version: 3, theme_ids: ["loss_separation"] });
    vi.unstubAllGlobals();
  });
});

describe("failed teacher mutations are reported, not swallowed (#77)", () => {
  it("a rejected rename does not claim success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403 }));
    render(<SettingsPage />);

    const nameInput = await screen.findByDisplayValue("Grade 3");
    fireEvent.change(nameInput, { target: { value: "Grade 4" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

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

  it("a rename that never reaches the server is reported", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<SettingsPage />);

    const nameInput = await screen.findByDisplayValue("Grade 3");
    fireEvent.change(nameInput, { target: { value: "Grade 4" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(await screen.findByText(/could not rename/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).not.toHaveAttribute("disabled");
    vi.unstubAllGlobals();
  });

  it("a delete that never reaches the server is reported and stays put", async () => {
    REPLACE.mockClear();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<SettingsPage />);

    const input = await screen.findByPlaceholderText(/type "grade 3"/i);
    fireEvent.change(input, { target: { value: "Grade 3" } });
    fireEvent.click(screen.getByRole("button", { name: /delete classroom/i }));
    fireEvent.click(
      await screen.findByRole("button", { name: /yes, delete/i, hidden: true })
    );

    expect(await screen.findByText(/could not delete/i)).toBeInTheDocument();
    expect(REPLACE).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});

describe("student-readable notes setting", () => {
  it("defaults off and saves only after the server responds", async () => {
    let finishSave!: (response: Response) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json({ theme_ids: [], settings_version: 0, editable: true, themes: [] }))
      .mockImplementationOnce(() => new Promise<Response>(resolve => { finishSave = resolve; }));
    vi.stubGlobal("fetch", fetcher);
    render(<SettingsPage />);
    const toggle = await screen.findByRole("checkbox", { name: "Let students read my notes" });
    expect(toggle).not.toBeChecked();
    expect(toggle).toHaveAccessibleDescription(/students.*read.*notes/i);
    fireEvent.click(toggle);
    fireEvent.click(screen.getByRole("button", { name: "Save note setting" }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
    expect(toggle).toBeDisabled();
    expect(screen.queryByText("Note setting saved")).not.toBeInTheDocument();
    expect(fetcher.mock.calls[1]).toEqual([expect.stringContaining("/classrooms/cls-123/review-notes"), {
      method: "PATCH", headers: { "Content-Type": "application/json", Authorization: "Bearer tok" },
      body: JSON.stringify({ enabled: true }),
    }]);
    finishSave(Response.json({ enabled: true }));
    expect(await screen.findByText("Note setting saved")).toHaveAttribute("aria-live", "polite");
    expect(toggle).toBeChecked();
    expect(toggle).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "Save note setting" })).toBeDisabled();
    vi.unstubAllGlobals();
  });

  it("reverts to the stored value when saving fails, including turning off", async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(Response.json({ theme_ids: [], settings_version: 0, editable: true, themes: [] }))
      .mockResolvedValueOnce(Response.json({}, { status: 500 }))
      .mockResolvedValueOnce(Response.json({ enabled: true }))
      .mockRejectedValueOnce(new TypeError("offline"));
    vi.stubGlobal("fetch", fetcher);
    render(<SettingsPage />);
    const toggle = await screen.findByRole("checkbox", { name: "Let students read my notes" });
    fireEvent.click(toggle);
    fireEvent.click(screen.getByRole("button", { name: "Save note setting" }));
    expect(await screen.findByText(/Could not save note setting/)).toHaveAttribute("aria-live", "polite");
    expect(toggle).not.toBeChecked();
    fireEvent.click(toggle);
    fireEvent.click(screen.getByRole("button", { name: "Save note setting" }));
    expect(await screen.findByText("Note setting saved")).toBeInTheDocument();
    fireEvent.click(toggle);
    fireEvent.click(screen.getByRole("button", { name: "Save note setting" }));
    expect(await screen.findByText(/Could not save note setting/)).toHaveAttribute("aria-live", "polite");
    expect(toggle).toBeChecked();
    expect(toggle).not.toBeDisabled();
    vi.unstubAllGlobals();
  });
});
