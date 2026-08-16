import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import FailureScreen, { resetFailChain } from "./FailureScreen";
import { act } from "react";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ profileId: "prof-123" }),
}));

vi.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: { getSession: async () => ({ data: { session: { access_token: "test-token" } } }) },
  },
}));

beforeEach(() => {
  pushMock.mockClear();
  sessionStorage.clear();
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ job_id: "new-job" }),
  }) as unknown as typeof fetch;
});

describe("FailureScreen — safe reason taxonomy", () => {
  it("renders child_text", () => {
    render(<FailureScreen reason="child_text" />);
    expect(screen.getByText("Some words need changing before we can make this book.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Change my words" })).toBeDefined();
  });

  it("renders character_safety", () => {
    render(<FailureScreen reason="character_safety" />);
    expect(screen.getByText("We couldn’t safely use the character picture we made. Your words aren’t in trouble.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Make the story again" })).toBeDefined();
  });

  it("renders scene_safety", () => {
    render(<FailureScreen reason="scene_safety" />);
    expect(screen.getByText("One of the pictures we made couldn’t be used.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Make the story again" })).toBeDefined();
  });

  it("renders service_busy", () => {
    render(<FailureScreen reason="service_busy" />);
    expect(screen.getByText("The story-making service is busy right now.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Try again" })).toBeDefined();
  });

  it("renders worker_stopped", () => {
    render(<FailureScreen reason="worker_stopped" />);
    expect(screen.getByText("The story maker stopped before it finished.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Try again" })).toBeDefined();
  });

  it("renders service_limit with no retry control and shows story ref", () => {
    render(<FailureScreen reason="service_limit" jobId="12345678-abcd-efgh-1234" />);
    expect(screen.getByText("The story-making allowance has run out.")).toBeDefined();
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Make the story again" })).toBeNull();
    expect(screen.getByText("12345678")).toBeDefined();
  });

  it("renders book_limit with no retry control", () => {
    render(<FailureScreen reason="book_limit" jobId="87654321-abcd" />);
    expect(screen.getByText("This book reached its picture-making limit.")).toBeDefined();
    expect(screen.queryByRole("button", { name: "Try again" })).toBeNull();
    expect(screen.getByText("87654321")).toBeDefined();
  });

  it("renders system_error for unknown values", () => {
    render(<FailureScreen reason="unknown_garbage" />);
    expect(screen.getByText("Something interrupted your story.")).toBeDefined();
    expect(screen.getByRole("button", { name: "Try again" })).toBeDefined();
  });

  it("renders system_error for legacy machine reason", () => {
    render(<FailureScreen reason="machine" />);
    expect(screen.getByText("Something interrupted your story.")).toBeDefined();
  });

  it("copies full story reference ID to clipboard when copy button clicked", async () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });

    render(<FailureScreen reason="service_busy" jobId="12345678-full-uuid-here" />);
    const copyBtn = screen.getByRole("button", { name: "Copy story reference ID" });
    fireEvent.click(copyBtn);

    expect(writeTextMock).toHaveBeenCalledWith("12345678-full-uuid-here");
    await waitFor(() => expect(screen.getByText("Copied!")).toBeDefined());
  });
});

describe("FailureScreen — kind=revise", () => {
  it("shows revise copy and Change my words button", () => {
    render(<FailureScreen kind="revise" inputText="A story." />);
    expect(screen.getByText(/let's change a few words/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /change my words/i })).toBeDefined();
    expect(screen.queryByRole("button", { name: /try again/i })).toBeNull();
  });

  it("revise stashes inputText in sb.prefill and navigates to /write", () => {
    render(<FailureScreen kind="revise" inputText="A story about a dog." />);
    fireEvent.click(screen.getByRole("button", { name: /change my words/i }));
    expect(sessionStorage.getItem("sb.prefill")).toBe("A story about a dog.");
    expect(pushMock).toHaveBeenCalledWith("/s/prof-123/write");
  });

  it("revise increments sb.failChain counter", () => {
    sessionStorage.setItem("sb.failChain", "1");
    render(<FailureScreen kind="revise" inputText="x" />);
    fireEvent.click(screen.getByRole("button", { name: /change my words/i }));
    expect(sessionStorage.getItem("sb.failChain")).toBe("2");
  });

  it("does NOT write to jobs row when revise is pressed (spec invariant 9)", () => {
    render(<FailureScreen kind="revise" inputText="A story." />);
    fireEvent.click(screen.getByRole("button", { name: /change my words/i }));
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe("FailureScreen — kind=retry", () => {
  it("shows retry copy and both choices", () => {
    render(<FailureScreen kind="retry" inputText="A story." />);
    expect(screen.getByText(/machine got stuck/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /make this story again/i })).toBeDefined();
    expect(screen.getByRole("button", { name: /write something new/i })).toBeDefined();
    expect(screen.queryByRole("button", { name: /change my words/i })).toBeNull();
  });

  it("retry POSTs inputText verbatim to /storybooks and navigates to new process page", async () => {
    render(<FailureScreen kind="retry" inputText="A dog runs." />);
    fireEvent.click(screen.getByRole("button", { name: /make this story again/i }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/s/prof-123/process/new-job"));
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/storybooks"),
      expect.objectContaining({ body: JSON.stringify({ text: "A dog runs.", style_preset_id: null }) })
    );
  });

  it("retry sends the Bearer token", async () => {
    render(<FailureScreen kind="retry" inputText="A dog runs." />);
    fireEvent.click(screen.getByRole("button", { name: /make this story again/i }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/storybooks"),
      expect.objectContaining({
        headers: expect.objectContaining({ Authorization: "Bearer test-token" }),
      })
    ));
  });

  it("retry carries the original style preset so the redo is not silently re-styled", async () => {
    render(<FailureScreen kind="retry" inputText="A dog runs." stylePresetId="gouache" />);
    fireEvent.click(screen.getByRole("button", { name: /make this story again/i }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/storybooks"),
      expect.objectContaining({
        body: JSON.stringify({ text: "A dog runs.", style_preset_id: "gouache" }),
      })
    ));
  });

  it("a failed retry says so instead of silently doing nothing", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 500 }) as unknown as typeof fetch;
    render(<FailureScreen kind="retry" inputText="x" />);
    fireEvent.click(screen.getByRole("button", { name: /make this story again/i }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeDefined());
    expect(pushMock).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: /make this story again/i }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("write something new goes to /write without POSTing", () => {
    render(<FailureScreen kind="retry" inputText="x" />);
    fireEvent.click(screen.getByRole("button", { name: /write something new/i }));
    expect(pushMock).toHaveBeenCalledWith("/s/prof-123/write");
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it("retry increments sb.failChain counter", async () => {
    sessionStorage.setItem("sb.failChain", "1");
    render(<FailureScreen kind="retry" inputText="x" />);
    fireEvent.click(screen.getByRole("button", { name: /make this story again/i }));
    await waitFor(() => expect(pushMock).toHaveBeenCalled());
    expect(sessionStorage.getItem("sb.failChain")).toBe("2");
  });

  it("button disables on press (prevents double-submit)", async () => {
    let resolvePost!: (v: Response) => void;
    global.fetch = vi.fn().mockReturnValue(
      new Promise<Response>(r => { resolvePost = r; })
    ) as unknown as typeof fetch;

    render(<FailureScreen kind="retry" inputText="x" />);
    const btn = screen.getByRole("button", { name: /make this story again/i });
    fireEvent.click(btn);
    expect((btn as HTMLButtonElement).disabled).toBe(true);

    await act(async () => {
      resolvePost({ ok: true, json: async () => ({ job_id: "new" }) } as Response);
    });
  });
});

describe("FailureScreen — kind=not-found", () => {
  it("shows not-found copy and Write a new story button", () => {
    render(<FailureScreen kind="not-found" />);
    expect(screen.getByText(/can't find that story/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /write a new story/i })).toBeDefined();
  });

  it("not-found navigates to /write empty, counter does NOT increment", () => {
    sessionStorage.setItem("sb.failChain", "2");
    render(<FailureScreen kind="not-found" />);
    fireEvent.click(screen.getByRole("button", { name: /write a new story/i }));
    expect(pushMock).toHaveBeenCalledWith("/s/prof-123/write");
    expect(sessionStorage.getItem("sb.failChain")).toBe("2");
  });

  it("not-found does not POST to /storybooks (spec invariant 9)", () => {
    render(<FailureScreen kind="not-found" />);
    fireEvent.click(screen.getByRole("button", { name: /write a new story/i }));
    expect(global.fetch).not.toHaveBeenCalled();
  });
});

describe("FailureScreen — kind=asleep", () => {
  it("shows asleep copy and Make it again button", () => {
    render(<FailureScreen kind="asleep" inputText="A story." />);
    expect(screen.getByText(/went to sleep/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /make it again/i })).toBeDefined();
  });

  it("asleep POSTs inputText and navigates, counter does NOT increment", async () => {
    sessionStorage.setItem("sb.failChain", "2");
    render(<FailureScreen kind="asleep" inputText="A story." />);
    fireEvent.click(screen.getByRole("button", { name: /make it again/i }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/s/prof-123/process/new-job"));
    expect(sessionStorage.getItem("sb.failChain")).toBe("2");
  });
});

describe("FailureScreen — chain counter & third offer", () => {
  it("does not show start-a-new-story at count 0", () => {
    render(<FailureScreen kind="revise" inputText="x" />);
    expect(screen.queryByText(/try a different story/i)).toBeNull();
  });

  it("shows start-a-new-story offer when chain count is already 3 (spec §4.5)", () => {
    sessionStorage.setItem("sb.failChain", "3");
    render(<FailureScreen kind="revise" inputText="x" />);
    expect(screen.getByText(/try a different story/i)).toBeDefined();
  });

  it("retry offers the escape at count 0 — the second choice supersedes the §4.5 gate", () => {
    render(<FailureScreen kind="retry" inputText="x" />);
    expect(screen.getByRole("button", { name: /write something new/i })).toBeDefined();
    expect(screen.queryByText(/try a different story/i)).toBeNull();
  });

  it("fourth press still works — counter never gates (spec invariant 7)", async () => {
    sessionStorage.setItem("sb.failChain", "4");
    render(<FailureScreen kind="retry" inputText="x" />);
    const btn = screen.getByRole("button", { name: /make this story again/i });
    expect((btn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(btn);
    await waitFor(() => expect(pushMock).toHaveBeenCalled());
  });
});

describe("FailureScreen — secondary navigation", () => {
  it("renders Back to Bookshelf link when profileId is present", () => {
    render(<FailureScreen kind="revise" inputText="x" />);
    const link = screen.getByRole("link", { name: /back to bookshelf/i });
    expect(link).toHaveAttribute("href", "/s/prof-123");
  });
});

describe("resetFailChain", () => {
  it("clears sb.failChain from sessionStorage", () => {
    sessionStorage.setItem("sb.failChain", "5");
    resetFailChain();
    expect(sessionStorage.getItem("sb.failChain")).toBeNull();
  });
});
