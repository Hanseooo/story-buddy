import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import WriteStoryPage from "./page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
}));

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: async () => ({
        data: { session: { access_token: "test-token" } },
      }),
    },
  },
}));

describe("WriteStoryPage", () => {
  beforeEach(() => {
    pushMock.mockClear();
    sessionStorage.clear();
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

  it("sends the session bearer token — POST /storybooks is auth-guarded", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "A dog runs in a field." },
    });
    fireEvent.click(screen.getByText("Make my book"));

    await waitFor(() => expect(pushMock).toHaveBeenCalled());

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/storybooks"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token",
        }),
      })
    );
  });

  it("shows a live word count that updates as the user types", () => {
    render(<WriteStoryPage />);
    const textarea = screen.getByLabelText("story text");
    fireEvent.change(textarea, { target: { value: "one two three" } });

    const counter = screen.getByText(/3/i);
    expect(counter).toHaveAttribute("aria-live", "polite");
  });
});

describe("WriteStoryPage — prefill and chain counter", () => {
  beforeEach(() => {
    pushMock.mockClear();
    sessionStorage.clear();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "abc-123" }),
    }) as unknown as typeof fetch;
  });

  it("prefills the textarea from sb.prefill on mount and deletes the key", () => {
    sessionStorage.setItem("sb.prefill", "My story about a cat.");
    render(<WriteStoryPage />);
    const textarea = screen.getByLabelText("story text") as HTMLTextAreaElement;
    expect(textarea.value).toBe("My story about a cat.");
    expect(sessionStorage.getItem("sb.prefill")).toBeNull();
  });

  it("calls resetFailChain on mount when no sb.prefill is present", () => {
    sessionStorage.setItem("sb.failChain", "3");
    render(<WriteStoryPage />);
    // No prefill → fresh start → chain reset
    expect(sessionStorage.getItem("sb.failChain")).toBeNull();
  });

  it("does NOT call resetFailChain when sb.prefill is present (child is still in a chain)", () => {
    sessionStorage.setItem("sb.failChain", "2");
    sessionStorage.setItem("sb.prefill", "A story.");
    render(<WriteStoryPage />);
    expect(sessionStorage.getItem("sb.failChain")).toBe("2");
  });

  it("shows try-a-different-story offer at chain count 3", () => {
    sessionStorage.setItem("sb.failChain", "3");
    sessionStorage.setItem("sb.prefill", "A story.");
    render(<WriteStoryPage />);
    expect(screen.getByText(/start over/i)).toBeDefined();
  });

  it("try-a-different-story clears the textarea", () => {
    sessionStorage.setItem("sb.failChain", "3");
    sessionStorage.setItem("sb.prefill", "A story.");
    render(<WriteStoryPage />);
    fireEvent.click(screen.getByText(/start over/i));
    const textarea = screen.getByLabelText("story text") as HTMLTextAreaElement;
    expect(textarea.value).toBe("");
  });

  it("shows role=alert error when POST returns non-ok status (spec §4.6)", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    }) as unknown as typeof fetch;

    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "A story about a dog running around." },
    });
    fireEvent.click(screen.getByText("Make my book"));

    await waitFor(() => expect(screen.getByRole("alert")).toBeDefined());
    expect(pushMock).not.toHaveBeenCalled();
  });
});
