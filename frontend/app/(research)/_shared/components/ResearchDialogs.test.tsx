import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { EXAMPLES } from "../../research/(reference)/dataset/data";
import type { ResearchPair } from "../constants";
import { LightboxModal } from "./LightboxModal";
import { ShortcutsModal } from "./ShortcutsModal";

const sample = EXAMPLES.find((example) => example.record.pair_id === "033b8372e89e4c06")!;
const pair: ResearchPair = {
  id: sample.record.pair_id,
  canonical_signed_url: sample.reference.src,
  scene_signed_url: sample.page.src,
};

describe("research dialogs", () => {
  it("names the lightbox, uses the native modal, closes with Escape, and restores focus", () => {
    function Inspector() {
      const [isOpen, setIsOpen] = useState(false);
      return (
        <>
          <button onClick={() => setIsOpen(true)}>Open inspector</button>
          <LightboxModal
            isOpen={isOpen}
            onClose={() => setIsOpen(false)}
            pair={pair}
            activeTab="side-by-side"
            setActiveTab={vi.fn()}
          />
        </>
      );
    }
    render(
      <Inspector />,
    );

    const opener = screen.getByRole("button", { name: "Open inspector" });
    opener.focus();
    fireEvent.click(opener);
    const dialog = screen.getByRole("dialog", { name: /high-resolution image inspector/i });
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute("open");
    expect(document.activeElement).toBe(dialog);

    fireEvent.keyDown(dialog, { key: "Enter", bubbles: true });
    expect(dialog).toBeInTheDocument();
    fireEvent(dialog, new Event("cancel", { cancelable: true }));
    expect(screen.queryByRole("dialog", { name: /high-resolution image inspector/i })).not.toBeInTheDocument();
    expect(document.activeElement).toBe(opener);
  });

  it("gives the shortcuts guide a name and keeps Enter from reaching the page", () => {
    const onPageKeyDown = vi.fn();
    function Guide() {
      const [isOpen, setIsOpen] = useState(false);
      return (
        <div onKeyDown={onPageKeyDown}>
          <button onClick={() => setIsOpen(true)}>Open guide</button>
          <ShortcutsModal isOpen={isOpen} onClose={() => setIsOpen(false)} />
        </div>
      );
    }
    render(<Guide />);

    fireEvent.click(screen.getByRole("button", { name: "Open guide" }));
    const dialog = screen.getByRole("dialog", { name: /shortcuts & labelling rulebook/i });
    expect(document.activeElement).toBe(dialog);
    fireEvent.keyDown(dialog, { key: "Enter", bubbles: true });
    expect(onPageKeyDown).not.toHaveBeenCalled();

    fireEvent(dialog, new Event("cancel", { cancelable: true }));
    expect(screen.queryByRole("dialog", { name: /shortcuts & labelling rulebook/i })).not.toBeInTheDocument();
  });
});
