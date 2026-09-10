import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import * as fs from "node:fs";
import * as path from "node:path";
import WriteStoryPage from "./page";

const pushMock = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushMock }),
  useParams: () => ({ profileId: "prof-123" }),
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
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "My Book" },
    });
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "A dog runs in a field." },
    });
    fireEvent.click(screen.getByText("Make my book"));

    await waitFor(() => expect(pushMock).toHaveBeenCalledWith("/s/prof-123/process/abc-123"));

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/storybooks"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          text: "A dog runs in a field.",
          title: "My Book",
          style_preset_id: "gouache",
        }),
      })
    );
  });

  it("sends the selected style_preset_id (ADR-022), defaulting to gouache (ADR-042)", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "My Book" },
    });
    expect(screen.queryByText("Comic")).toBeNull();
    expect(screen.getByText("Paper Cutout")).toBeDefined();
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "A dog runs in a field." },
    });
    fireEvent.click(screen.getByLabelText("Cartoon"));
    fireEvent.click(screen.getByText("Make my book"));

    await waitFor(() => expect(pushMock).toHaveBeenCalled());

    const body = JSON.parse(
      (global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][1].body
    );
    expect(body.style_preset_id).toBe("cel");
  });

  it("sends the session bearer token — POST /storybooks is auth-guarded", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "My Book" },
    });
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

// Mirrors Avatar.test.tsx's manifest-integrity check: the picker is useless if the
// sample art is missing or misnamed.
describe("Style preset sample art", () => {
  it("every ADR-042 selectable preset has a sample image in public/style-presets/", () => {
    const dir = path.resolve(__dirname, "..", "..", "..", "..", "public", "style-presets");
    for (const id of ["cel", "gouache", "cut_paper"]) {
      expect(fs.existsSync(path.join(dir, `${id}.png`)), `missing file: ${id}.png`).toBe(true);
    }
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
    sessionStorage.setItem(
      "sb.prefill",
      JSON.stringify({ text: "My story about a cat.", title: "Cat Book" })
    );
    render(<WriteStoryPage />);
    const textarea = screen.getByLabelText("story text") as HTMLTextAreaElement;
    expect(textarea.value).toBe("My story about a cat.");
    expect((screen.getByLabelText("Story title") as HTMLInputElement).value).toBe("Cat Book");
    expect(sessionStorage.getItem("sb.prefill")).toBeNull();
  });

  it("restores the selected style from sb.prefill", () => {
    sessionStorage.setItem(
      "sb.prefill",
      JSON.stringify({ text: "My story about a cat.", title: "Cat Book", style_preset_id: "cut_paper" })
    );
    render(<WriteStoryPage />);
    expect(screen.getByLabelText("Paper Cutout")).toBeChecked();
  });

  it("calls resetFailChain on mount when no sb.prefill is present", () => {
    sessionStorage.setItem("sb.failChain", "3");
    render(<WriteStoryPage />);
    // No prefill → fresh start → chain reset
    expect(sessionStorage.getItem("sb.failChain")).toBeNull();
  });

  it("does NOT call resetFailChain when sb.prefill is present (child is still in a chain)", () => {
    sessionStorage.setItem("sb.failChain", "2");
    sessionStorage.setItem("sb.prefill", JSON.stringify({ text: "A story.", title: "Book" }));
    render(<WriteStoryPage />);
    expect(sessionStorage.getItem("sb.failChain")).toBe("2");
  });

  it("shows try-a-different-story offer at chain count 3", () => {
    sessionStorage.setItem("sb.failChain", "3");
    sessionStorage.setItem("sb.prefill", JSON.stringify({ text: "A story.", title: "Book" }));
    render(<WriteStoryPage />);
    expect(screen.getByText(/start over/i)).toBeDefined();
  });

  it("try-a-different-story clears the textarea", () => {
    sessionStorage.setItem("sb.failChain", "3");
    sessionStorage.setItem("sb.prefill", JSON.stringify({ text: "A story.", title: "Book" }));
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
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "My Book" },
    });
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "A story about a dog running around." },
    });
    fireEvent.click(screen.getByText("Make my book"));

    await waitFor(() => expect(screen.getByRole("alert")).toBeDefined());
    expect(pushMock).not.toHaveBeenCalled();
  });
});

// spend-and-retry-economics §6.1: "Frontend word count accepts 300, rejects 301, disables
// submission over cap, and keeps the textual `Too long!` state." The cap moved 800 → 300 with
// ADR-037; nothing pinned the boundary, so a stale constant would have shipped silently.
describe("WriteStoryPage — the 300-word cap", () => {
  const words = (n: number) => Array.from({ length: n }, (_, i) => `w${i}`).join(" ");
  const submitButton = () => screen.getByText("Make my book").closest("button");

  beforeEach(() => {
    pushMock.mockClear();
    sessionStorage.clear();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "abc-123" }),
    }) as unknown as typeof fetch;
  });

  it("accepts exactly 300 words — the boundary is inclusive", () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), { target: { value: words(300) } });

    expect(screen.queryByText("Too long!")).toBeNull();
    expect(submitButton()).not.toBeDisabled();
  });

  it("rejects 301 words with the textual Too long! state, not a colour-only cue (CC-6)", () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), { target: { value: words(301) } });

    expect(screen.getByText("Too long!")).toBeDefined();
    expect(submitButton()).toBeDisabled();
  });

  it("does not POST over cap — the child shortens the story, nothing is silently discarded", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), { target: { value: words(400) } });
    fireEvent.click(screen.getByText("Make my book"));

    // `handleSubmit` awaits getSession before it fetches, so a synchronous assertion here
    // passes even when the guard is broken. Flush the microtask queue first.
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(global.fetch).not.toHaveBeenCalled();
    expect(pushMock).not.toHaveBeenCalled();
  });
});

describe("WriteStoryPage title field", () => {
  beforeEach(() => {
    sessionStorage.clear();
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: "job-1" }),
    }) as unknown as typeof fetch;
  });

  it("shows a title input with an n/80 counter separate from the word counter", () => {
    render(<WriteStoryPage />);
    const titleInput = screen.getByLabelText("Story title");
    fireEvent.change(titleInput, { target: { value: "My Book" } });
    expect(screen.getByText("7 / 80")).toBeInTheDocument();
  });

  // spec §3 requires "1-80 characters after trimming", so a counter over the untrimmed value
  // reads 82 / 80 on a title this same page submits without complaint.
  it("counts the trimmed title so the counter agrees with the validator", () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: `  ${"x".repeat(80)}  ` },
    });
    expect(screen.getByText("80 / 80")).toBeInTheDocument();
  });

  // spec §3: "Count Unicode code points consistently in client and server, not UTF-16 units."
  // Each dragon is one code point and two UTF-16 units, so a `.length` counter would read
  // 160 / 80 and block a title the server accepts.
  it("counts astral-plane characters as one code point each", () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "\u{1F409}".repeat(80) },
    });
    expect(screen.getByText("80 / 80")).toBeInTheDocument();
  });

  it("accepts an 80-code-point astral title that a UTF-16 length would reject", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "\u{1F409}".repeat(80) },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(screen.queryByText("Keep your title to 80 characters.")).toBeNull();
  });

  it("blocks submit and shows the empty-title message", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));
    expect(await screen.findByText("Give your story a title.")).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Story title")).toHaveFocus();
  });

  it("blocks submit and shows the 81-character message without truncating input", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    const titleInput = screen.getByLabelText("Story title") as HTMLInputElement;
    const longTitle = "x".repeat(81);
    fireEvent.change(titleInput, { target: { value: longTitle } });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));
    expect(await screen.findByText("Keep your title to 80 characters.")).toBeInTheDocument();
    expect(titleInput.value).toBe(longTitle);
    expect(global.fetch).not.toHaveBeenCalled();
    expect(titleInput).toHaveFocus();
  });

  it("submits title and text together on valid input", async () => {
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    fireEvent.change(screen.getByLabelText("Story title"), { target: { value: "My Book" } });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    const body = JSON.parse((global.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body);
    expect(body.title).toBe("My Book");
    expect(body.text).toBe("one two three four five");
  });

  it("shows a checked title on 409 and resubmits with title_ack when accepted", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({ detail: { checked_title: "call me at <PH_MOBILE>" } }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ job_id: "job-2" }),
      }) as unknown as typeof fetch;
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "call me at 09171234567" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));
    expect(await screen.findByText(/call me at <PH_MOBILE>/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /use this title/i }));
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
    const secondBody = JSON.parse((global.fetch as ReturnType<typeof vi.fn>).mock.calls[1][1].body);
    expect(secondBody.title_ack).toBe("call me at <PH_MOBILE>");
    expect(secondBody.title).toBe("call me at 09171234567");
  });

  it("Enter in the title moves focus to the story without submitting", () => {
    render(<WriteStoryPage />);
    fireEvent.keyDown(screen.getByLabelText("Story title"), { key: "Enter", code: "Enter" });
    expect(screen.getByLabelText("story text")).toHaveFocus();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  // spec §4: "if it becomes empty or exceeds the limit, ask for a different title without
  // discarding the story." Reporting a rejected title as "Something went wrong. Try again!"
  // sends the child back with the same title, and spec §3 forbids the converse confusion:
  // "A transport error is not evidence that the title failed moderation."
  it("asks for a different title on a rejection instead of reporting a transport error", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "that title isn't allowed" }),
    }) as unknown as typeof fetch;
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    const titleInput = screen.getByLabelText("Story title") as HTMLInputElement;
    fireEvent.change(titleInput, { target: { value: "call me at 09171234567" } });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));

    expect(await screen.findByText("Try a different title.")).toBeInTheDocument();
    expect(screen.queryByText("Something went wrong. Try again!")).toBeNull();
    expect((screen.getByLabelText("story text") as HTMLTextAreaElement).value).toBe(
      "one two three four five",
    );
    expect(titleInput.value).toBe("call me at 09171234567");
    expect(titleInput).toHaveFocus();
  });

  it("still reports a lost response as a transport error", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("network down")) as unknown as typeof fetch;
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    fireEvent.change(screen.getByLabelText("Story title"), { target: { value: "My Book" } });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));

    expect(await screen.findByText("Something went wrong. Try again!")).toBeInTheDocument();
    expect(screen.queryByText("Try a different title.")).toBeNull();
  });

  // CC-6 and DESIGN.md §12: the panel blocks a paid submission, so a keyboard or screen-reader
  // child has to land on it and be able to leave it.
  it("focuses the privacy-replacement panel and dismisses it on Escape", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: { checked_title: "call me at <PH_MOBILE>" } }),
    }) as unknown as typeof fetch;
    render(<WriteStoryPage />);
    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    fireEvent.change(screen.getByLabelText("Story title"), {
      target: { value: "call me at 09171234567" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));

    const confirm = await screen.findByRole("button", { name: /use this title/i });
    const panel = confirm.closest('[role="alert"]') as HTMLElement;
    await waitFor(() => expect(panel).toHaveFocus());

    fireEvent.keyDown(panel, { key: "Escape", code: "Escape" });
    expect(screen.queryByRole("button", { name: /use this title/i })).toBeNull();
    expect(screen.getByLabelText("Story title")).toHaveFocus();
  });

  it("describes the title by its counter alone while no error is showing", async () => {
    render(<WriteStoryPage />);
    const titleInput = screen.getByLabelText("Story title");
    expect(titleInput).toHaveAttribute("aria-describedby", "title-count");

    fireEvent.change(screen.getByLabelText("story text"), {
      target: { value: "one two three four five" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "Write your story" }));
    await screen.findByText("Give your story a title.");
    expect(titleInput).toHaveAttribute("aria-describedby", "title-count title-error");
  });
});
