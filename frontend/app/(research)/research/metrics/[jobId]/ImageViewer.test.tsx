import { fireEvent, render, screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";
import ImageViewer from "./ImageViewer";

beforeAll(() => {
  // jsdom has <dialog> but not its modal methods. These do to `open` what the browser does.
  HTMLDialogElement.prototype.showModal = function () {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function () {
    this.removeAttribute("open");
  };
});

describe("ImageViewer", () => {
  it("opens the image large and closes it", () => {
    render(<ImageViewer src="https://img.test/a.webp" alt="Page 1, attempt 2" />);

    const trigger = screen.getByRole("button", { name: "Enlarge Page 1, attempt 2" });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Page 1, attempt 2" });
    expect(dialog).toHaveAttribute("open");

    fireEvent.click(screen.getByRole("button", { name: "Close image" }));
    expect(dialog).not.toHaveAttribute("open");
    expect(trigger).toHaveFocus();
  });

  it("closes on Escape and backdrop click, returning focus to the opener", () => {
    render(<ImageViewer src="https://img.test/a.webp" alt="Page 1" />);
    const trigger = screen.getByRole("button", { name: "Enlarge Page 1" });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Page 1" });

    fireEvent(dialog, new Event("cancel", { cancelable: true }));
    expect(dialog).not.toHaveAttribute("open");
    expect(trigger).toHaveFocus();

    fireEvent.click(trigger);
    fireEvent.click(dialog);
    expect(dialog).not.toHaveAttribute("open");
    expect(trigger).toHaveFocus();
  });

  it("keeps the image trigger at the minimum touch target size", () => {
    render(<ImageViewer src="https://img.test/a.webp" alt="Page 1" className="w-24 aspect-square" />);
    const trigger = screen.getByRole("button", { name: "Enlarge Page 1" });

    expect(trigger).toHaveClass("min-h-11", "min-w-11");
  });

  it("shows a named placeholder when there is no image or it fails to load", () => {
    const { unmount } = render(<ImageViewer src={null} alt="Reference for Mia" />);
    expect(screen.getByRole("img", { name: "Reference for Mia" })).toHaveTextContent("Image unavailable");
    unmount();

    render(<ImageViewer src="https://img.test/gone.webp" alt="Page 2, attempt 1" />);
    fireEvent.error(screen.getAllByAltText("Page 2, attempt 1")[0]);
    expect(screen.getByRole("img", { name: "Page 2, attempt 1" })).toHaveTextContent("Image unavailable");
    expect(screen.queryByRole("button", { name: /Enlarge/ })).toBeNull();
  });

  it("keeps a failed enlarged image dismissible and returns focus to the opener", () => {
    render(<ImageViewer src="https://img.test/a.webp" alt="Page 1" />);
    const trigger = screen.getByRole("button", { name: "Enlarge Page 1" });
    fireEvent.click(trigger);
    const dialog = screen.getByRole("dialog", { name: "Page 1" });
    const close = screen.getByRole("button", { name: "Close image" });
    close.focus();

    fireEvent.error(dialog.querySelector("img")!);

    expect(dialog).toHaveAttribute("open");
    expect(close).toHaveFocus();
    expect(dialog.querySelector('[role="img"]')).toHaveTextContent("Image unavailable");
    fireEvent.click(close);
    expect(dialog).not.toHaveAttribute("open");
    expect(trigger).toHaveFocus();
  });
});
