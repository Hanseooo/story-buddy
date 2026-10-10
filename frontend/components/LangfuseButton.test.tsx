import { fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import LangfuseButton from "./LangfuseButton";

const TRACE = "https://cloud.langfuse.com/project/p/traces/abc";

beforeAll(() => {
  // jsdom has <dialog> but not its modal methods. These do to `open` what the browser does.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("LangfuseButton", () => {
  it("renders nothing with the flag off, or with no trace", () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "");
    const off = render(<LangfuseButton url={TRACE} />);
    expect(off.container).toBeEmptyDOMElement();
    off.unmount();

    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "TRUE");
    const wrongValue = render(<LangfuseButton url={TRACE} />);
    expect(wrongValue.container).toBeEmptyDOMElement();
    wrongValue.unmount();

    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "true");
    const noTrace = render(<LangfuseButton url={undefined} />);
    expect(noTrace.container).toBeEmptyDOMElement();
  });

  it("warns first; Cancel, Escape and backdrop close it without opening", () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "true");
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    render(<LangfuseButton url={TRACE} />);

    fireEvent.click(screen.getByRole("button", { name: "Open Langfuse trace" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("open");
    expect(within(dialog).getByRole("heading")).toHaveTextContent("Open the full Langfuse trace?");
    expect(within(dialog).getByText(
      "This trace is the full raw record of the run, including the story text before redaction. Open it only when you need that detail."
    )).toBeInTheDocument();
    expect(within(dialog).getAllByRole("button").map((button) => button.textContent)).toEqual([
      "Cancel",
      "Open in new tab",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(dialog).not.toHaveAttribute("open");

    fireEvent.click(screen.getByRole("button", { name: "Open Langfuse trace" }));
    fireEvent(dialog, new Event("cancel")); // what the browser fires on Escape
    expect(dialog).not.toHaveAttribute("open");

    fireEvent.click(screen.getByRole("button", { name: "Open Langfuse trace" }));
    fireEvent.click(dialog);
    expect(dialog).not.toHaveAttribute("open");
    expect(open).not.toHaveBeenCalled();
  });

  it("Open in new tab opens the trace with no opener", () => {
    vi.stubEnv("NEXT_PUBLIC_SHOW_LANGFUSE_LINKS", "true");
    const open = vi.spyOn(window, "open").mockReturnValue(null);
    render(<LangfuseButton url={TRACE} />);

    fireEvent.click(screen.getByRole("button", { name: "Open Langfuse trace" }));
    fireEvent.click(screen.getByRole("button", { name: "Open in new tab" }));

    expect(open).toHaveBeenCalledWith(TRACE, "_blank", "noopener,noreferrer");
  });
});
