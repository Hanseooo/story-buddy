import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WriteStoryPage from "./page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

describe("WriteStoryPage", () => {
  beforeEach(() => {
    pushMock.mockClear();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "abc-123" }),
    }) as unknown as typeof fetch;
  });

  it("submits the story text and redirects to the processing page", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "A dog runs in a field." },
    });
    fireEvent.click(screen.getByText("Make my book"));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/process/abc-123"));

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/storybooks"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ text: "A dog runs in a field." }),
      })
    );
  });

  it("shows a live word count that updates as the user types", () => {
    render(<WriteStoryPage />);
    const textarea = screen.getByLabelText("story text");
    fireEvent.change(textarea, { target: { value: "one two three" } });

    const counter = screen.getByText(/3 words/i);
    expect(counter).toHaveAttribute("aria-live", "polite");
  });

  it("does not navigate when the server responds with a non-ok status", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "Story text must be at least 5 words" }),
    }) as unknown as typeof fetch;

    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "too short lol ok fine" },
    });
    fireEvent.click(screen.getByText("Make my book"));

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(pushMock).not.toHaveBeenCalled();
  });
});
