import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import FailureScreen, { resetFailChain } from "./FailureScreen";
import { act } from "react";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ profileId: "prof-123" }),
}));

beforeEach(() => {
  pushMock.mockClear();
  sessionStorage.clear();
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ job_id: "new-job" }),
  }) as unknown as typeof fetch;
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
  it("shows retry copy and Try again button", () => {
    render(<FailureScreen kind="retry" inputText="A story." />);
    expect(screen.getByText(/the story machine got stuck/i)).toBeDefined();
    expect(screen.getByRole("button", { name: /try again/i })).toBeDefined();
    expect(screen.queryByRole("button", { name: /change my words/i })).toBeNull();
  });

  it("retry POSTs inputText verbatim to /storybooks and navigates to new process page", async () => {
    render(<FailureScreen kind="retry" inputText="A dog runs." />);
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/s/prof-123/process/new-job"));
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/storybooks"),
      expect.objectContaining({ body: JSON.stringify({ text: "A dog runs." }) })
    );
  });

  it("retry increments sb.failChain counter", async () => {
    sessionStorage.setItem("sb.failChain", "1");
    render(<FailureScreen kind="retry" inputText="x" />);
    fireEvent.click(screen.getByRole("button", { name: /try again/i }));
    await waitFor(() => expect(pushMock).toHaveBeenCalled());
    expect(sessionStorage.getItem("sb.failChain")).toBe("2");
  });

  it("button disables on press (prevents double-submit)", async () => {
    let resolvePost!: (v: Response) => void;
    global.fetch = vi.fn().mockReturnValue(
      new Promise<Response>(r => { resolvePost = r; })
    ) as unknown as typeof fetch;

    render(<FailureScreen kind="retry" inputText="x" />);
    const btn = screen.getByRole("button", { name: /try again/i });
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
    expect(sessionStorage.getItem("sb.failChain")).toBe("2"); // unchanged
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
    expect(sessionStorage.getItem("sb.failChain")).toBe("2"); // unchanged
  });
});

describe("FailureScreen — chain counter & third offer", () => {
  it("does not show start-a-new-story at count 0", () => {
    render(<FailureScreen kind="retry" inputText="x" />);
    expect(screen.queryByText(/try a different story/i)).toBeNull();
  });

  it("shows start-a-new-story offer when chain count is already 3 (spec §4.5)", () => {
    sessionStorage.setItem("sb.failChain", "3");
    render(<FailureScreen kind="retry" inputText="x" />);
    expect(screen.getByText(/try a different story/i)).toBeDefined();
  });

  it("fourth press still works — counter never gates (spec invariant 7)", async () => {
    sessionStorage.setItem("sb.failChain", "4");
    render(<FailureScreen kind="retry" inputText="x" />);
    const btn = screen.getByRole("button", { name: /try again/i });
    expect((btn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(btn);
    await waitFor(() => expect(pushMock).toHaveBeenCalled());
  });
});

describe("resetFailChain", () => {
  it("clears sb.failChain from sessionStorage", () => {
    sessionStorage.setItem("sb.failChain", "5");
    resetFailChain();
    expect(sessionStorage.getItem("sb.failChain")).toBeNull();
  });
});
