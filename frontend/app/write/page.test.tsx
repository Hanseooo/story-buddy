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
});
