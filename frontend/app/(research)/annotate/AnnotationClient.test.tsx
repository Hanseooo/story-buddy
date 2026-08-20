import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AnnotationClient from "./AnnotationClient";
import * as actions from "./actions";

const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRefresh })
}));

vi.mock("./actions", () => ({
  submitAnnotation: vi.fn().mockResolvedValue({ success: true })
}));

describe("Tier 1: AnnotationClient Component Tests", () => {
  const mockPair = {
    id: "pair-123",
    canonical_signed_url: "https://example.com/canonical-test-url.png",
    scene_signed_url: "https://example.com/scene-test-url.png",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("asserts NO metadata leaks in DOM (strict blinding verification)", () => {
    const { container } = render(<AnnotationClient pair={mockPair} />);
    
    // DOM should contain the signed URLs and image elements
    expect(container.innerHTML).toContain("https://example.com/canonical-test-url.png");
    expect(container.innerHTML).toContain("https://example.com/scene-test-url.png");

    // DOM must NOT leak database identifiers, split, pilot flags, prompt text, or model verdicts
    expect(container.innerHTML).not.toContain("char_id");
    expect(container.innerHTML).not.toContain("is_pilot");
    expect(container.innerHTML).not.toContain("is_constructed_negative");
    expect(container.innerHTML).not.toContain("split");
    expect(container.innerHTML).not.toContain("canonical_storage_path");
    expect(container.innerHTML).not.toContain("scene_storage_path");
    expect(container.innerHTML).not.toContain("model_verdict");
  });

  it("handles form state transitions properly between Same Character and failure taxonomy", () => {
    render(<AnnotationClient pair={mockPair} />);
    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });
    const diffCharRadio = screen.getByRole("radio", { name: /Different Character/i });
    const wrongColorCheckbox = screen.getByLabelText(/Wrong Color/i);
    const wrongSpeciesCheckbox = screen.getByLabelText(/Wrong Species/i);

    // Initial state: unselected
    expect(sameCharRadio).not.toBeChecked();
    expect(diffCharRadio).not.toBeChecked();
    expect(wrongColorCheckbox).not.toBeChecked();

    // Must select Different Character first to enable taxonomy
    fireEvent.click(diffCharRadio);
    expect(diffCharRadio).toBeChecked();
    expect(sameCharRadio).not.toBeChecked();

    // Selecting a failure reason sets it
    fireEvent.click(wrongColorCheckbox);
    expect(wrongColorCheckbox).toBeChecked();
    expect(sameCharRadio).not.toBeChecked();

    // Selecting another failure reason allows multi-select
    fireEvent.click(wrongSpeciesCheckbox);
    expect(wrongColorCheckbox).toBeChecked();
    expect(wrongSpeciesCheckbox).toBeChecked();
    
    // Clicking Same Character clears all taxonomy failures
    fireEvent.click(sameCharRadio);
    expect(sameCharRadio).toBeChecked();
    expect(diffCharRadio).not.toBeChecked();
    expect(wrongColorCheckbox).not.toBeChecked();
    expect(wrongSpeciesCheckbox).not.toBeChecked();
    
    // Clicking Different Character allows selecting taxonomy again
    fireEvent.click(diffCharRadio);
    fireEvent.click(wrongColorCheckbox);
    expect(diffCharRadio).toBeChecked();
    expect(wrongColorCheckbox).toBeChecked();
    expect(sameCharRadio).not.toBeChecked();
  });

  it("toggles gating booleans (Broken Anatomy & Text Visible) independently", () => {
    render(<AnnotationClient pair={mockPair} />);
    const brokenAnatomyCheckbox = screen.getByLabelText(/Broken Anatomy/i);
    const textVisibleCheckbox = screen.getByLabelText(/Text Visible/i);
    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });

    fireEvent.click(sameCharRadio);
    expect(sameCharRadio).toBeChecked();

    fireEvent.click(brokenAnatomyCheckbox);
    expect(brokenAnatomyCheckbox).toBeChecked();
    expect(sameCharRadio).toBeChecked(); // Gating checkbox does not clear Same Character

    fireEvent.click(textVisibleCheckbox);
    expect(textVisibleCheckbox).toBeChecked();
  });

  it("submits valid annotation payload and refreshes router", async () => {
    render(<AnnotationClient pair={mockPair} />);
    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });
    const submitBtn = screen.getByRole("button", { name: /Submit/i });

    fireEvent.click(sameCharRadio);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(actions.submitAnnotation).toHaveBeenCalledWith({
        pairId: "pair-123",
        failureReasons: [],
        sameCharacter: true,
        anatomyIntact: true, // (!brokenAnatomy)
        textFree: true       // (!textVisible)
      });
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it("displays server error message on failure", async () => {
    vi.mocked(actions.submitAnnotation).mockResolvedValueOnce({
      error: "Invalid state: same_character is false but no failure reasons provided"
    });

    render(<AnnotationClient pair={mockPair} />);
    const submitBtn = screen.getByRole("button", { name: /Submit/i });
    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });
    
    // The submit button won't do anything if we don't have a valid submission
    // Let's ensure it's valid so it calls submitAnnotation
    fireEvent.click(sameCharRadio);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Invalid state: same_character is false but no failure reasons provided/i)).toBeInTheDocument();
    });
  });

  it("supports keyboard shortcuts (0, 1-7, A, T, Enter)", async () => {
    render(<AnnotationClient pair={mockPair} />);
    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });
    const diffCharRadio = screen.getByRole("radio", { name: /Different Character/i });
    const wrongColorCheckbox = screen.getByLabelText(/Wrong Color/i);
    const brokenAnatomyCheckbox = screen.getByLabelText(/Broken Anatomy/i);
    const textVisibleCheckbox = screen.getByLabelText(/Text Visible/i);

    // Shortcut 'Shift+D' for Different Character
    fireEvent.keyDown(window, { key: "D", shiftKey: true });
    expect(diffCharRadio).toBeChecked();
    expect(sameCharRadio).not.toBeChecked();

    // Shortcut '1' for Wrong Color
    fireEvent.keyDown(window, { key: "1" });
    expect(wrongColorCheckbox).toBeChecked();
    expect(diffCharRadio).toBeChecked();
    expect(sameCharRadio).not.toBeChecked();

    // Shortcut '0' for Same Character
    fireEvent.keyDown(window, { key: "0" });
    expect(sameCharRadio).toBeChecked();
    expect(diffCharRadio).not.toBeChecked();
    expect(wrongColorCheckbox).not.toBeChecked();

    // Shortcut 'Shift+D' again to prepare for submit
    fireEvent.keyDown(window, { key: "D", shiftKey: true });
    expect(diffCharRadio).toBeChecked();

    // Select a reason to make it valid for submission
    fireEvent.keyDown(window, { key: "1" });

    // Shortcut 'a' for Broken Anatomy
    fireEvent.keyDown(window, { key: "a" });
    expect(brokenAnatomyCheckbox).toBeChecked();

    // Shortcut 't' for Text Visible
    fireEvent.keyDown(window, { key: "t" });
    expect(textVisibleCheckbox).toBeChecked();

    // Shortcut 'Enter' for Submit
    fireEvent.keyDown(window, { key: "Enter" });
    await waitFor(() => {
      expect(actions.submitAnnotation).toHaveBeenCalledWith({
        pairId: "pair-123",
        failureReasons: ["wrong_colour"],
        sameCharacter: false, // Explicit same character is false when different character is selected
        anatomyIntact: false, // anatomy_intact is false because brokenAnatomy is true
        textFree: false       // text_free is false because textVisible is true
      });
    });
  });
});
