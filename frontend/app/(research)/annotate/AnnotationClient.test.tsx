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
    const sameCharCheckbox = screen.getByTestId("same-character-checkbox");
    const wrongColorCheckbox = screen.getByLabelText(/Wrong Color/i);
    const wrongSpeciesCheckbox = screen.getByLabelText(/Wrong Species/i);

    // Initial state: unselected
    expect(sameCharCheckbox).not.toBeChecked();
    expect(wrongColorCheckbox).not.toBeChecked();

    // Selecting a failure reason sets it and ensures same character is false
    fireEvent.click(wrongColorCheckbox);
    expect(wrongColorCheckbox).toBeChecked();
    expect(sameCharCheckbox).not.toBeChecked();

    // Selecting another failure reason allows multi-select
    fireEvent.click(wrongSpeciesCheckbox);
    expect(wrongColorCheckbox).toBeChecked();
    expect(wrongSpeciesCheckbox).toBeChecked();
    expect(sameCharCheckbox).not.toBeChecked();
    
    // Clicking Same Character clears all taxonomy failures
    fireEvent.click(sameCharCheckbox);
    expect(sameCharCheckbox).toBeChecked();
    expect(wrongColorCheckbox).not.toBeChecked();
    expect(wrongSpeciesCheckbox).not.toBeChecked();
    
    // Clicking taxonomy again clears Same Character
    fireEvent.click(wrongColorCheckbox);
    expect(wrongColorCheckbox).toBeChecked();
    expect(sameCharCheckbox).not.toBeChecked();
  });

  it("toggles gating booleans (Broken Anatomy & Text Visible) independently", () => {
    render(<AnnotationClient pair={mockPair} />);
    const brokenAnatomyCheckbox = screen.getByLabelText(/Broken Anatomy/i);
    const textVisibleCheckbox = screen.getByLabelText(/Text Visible/i);
    const sameCharCheckbox = screen.getByTestId("same-character-checkbox");

    fireEvent.click(sameCharCheckbox);
    expect(sameCharCheckbox).toBeChecked();

    fireEvent.click(brokenAnatomyCheckbox);
    expect(brokenAnatomyCheckbox).toBeChecked();
    expect(sameCharCheckbox).toBeChecked(); // Gating checkbox does not clear Same Character

    fireEvent.click(textVisibleCheckbox);
    expect(textVisibleCheckbox).toBeChecked();
  });

  it("submits valid annotation payload and refreshes router", async () => {
    render(<AnnotationClient pair={mockPair} />);
    const sameCharCheckbox = screen.getByTestId("same-character-checkbox");
    const submitBtn = screen.getByRole("button", { name: /Submit/i });

    fireEvent.click(sameCharCheckbox);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(actions.submitAnnotation).toHaveBeenCalledWith(
        "pair-123",
        [],
        true,
        true, // anatomy_intact (!brokenAnatomy)
        true  // text_free (!textVisible)
      );
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it("displays server error message on failure", async () => {
    vi.mocked(actions.submitAnnotation).mockResolvedValueOnce({
      error: "Invalid state: same_character is false but no failure reasons provided"
    });

    render(<AnnotationClient pair={mockPair} />);
    const submitBtn = screen.getByRole("button", { name: /Submit/i });

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Invalid state: same_character is false but no failure reasons provided/i)).toBeInTheDocument();
    });
  });

  it("supports keyboard shortcuts (0, 1-7, A, T, Enter)", async () => {
    render(<AnnotationClient pair={mockPair} />);
    const sameCharCheckbox = screen.getByTestId("same-character-checkbox");
    const wrongColorCheckbox = screen.getByLabelText(/Wrong Color/i);
    const brokenAnatomyCheckbox = screen.getByLabelText(/Broken Anatomy/i);
    const textVisibleCheckbox = screen.getByLabelText(/Text Visible/i);

    // Shortcut '1' for Wrong Color
    fireEvent.keyDown(window, { key: "1" });
    expect(wrongColorCheckbox).toBeChecked();
    expect(sameCharCheckbox).not.toBeChecked();

    // Shortcut '0' for Same Character
    fireEvent.keyDown(window, { key: "0" });
    expect(sameCharCheckbox).toBeChecked();
    expect(wrongColorCheckbox).not.toBeChecked();

    // Shortcut 'a' for Broken Anatomy
    fireEvent.keyDown(window, { key: "a" });
    expect(brokenAnatomyCheckbox).toBeChecked();

    // Shortcut 't' for Text Visible
    fireEvent.keyDown(window, { key: "t" });
    expect(textVisibleCheckbox).toBeChecked();

    // Shortcut 'Enter' for Submit
    fireEvent.keyDown(window, { key: "Enter" });
    await waitFor(() => {
      expect(actions.submitAnnotation).toHaveBeenCalledWith(
        "pair-123",
        [],
        true,
        false, // anatomy_intact is false because brokenAnatomy is true
        false  // text_free is false because textVisible is true
      );
    });
  });
});
