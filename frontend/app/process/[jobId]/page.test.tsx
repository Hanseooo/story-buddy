import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import ProcessingPage from "./page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

let capturedCallback: (payload: unknown) => void;

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    channel: () => ({
      on: (_event: string, _filter: unknown, callback: (payload: unknown) => void) => {
        capturedCallback = callback;
        return { subscribe: () => ({}) };
      },
    }),
    removeChannel: vi.fn(),
  },
}));

describe("ProcessingPage", () => {
  beforeEach(() => {
    pushMock.mockClear();
  });

  it("redirects to the book page when the job completes", async () => {
    await act(async () => {
      render(<ProcessingPage params={Promise.resolve({ jobId: "abc-123" })} />);
    });

    act(() => {
      capturedCallback({ new: { id: "abc-123", status: "complete", current_stage: "compose" } });
    });

    expect(pushMock).toHaveBeenCalledWith("/book/abc-123");
  });

  it("shows the current stage while running", async () => {
    await act(async () => {
      render(<ProcessingPage params={Promise.resolve({ jobId: "abc-123" })} />);
    });

    act(() => {
      capturedCallback({ new: { id: "abc-123", status: "running", current_stage: "generate_scene" } });
    });

    expect(screen.getByText("generate_scene")).toBeDefined();
  });
});
