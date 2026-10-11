import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AnnotationClient from "./AnnotationClient";
import * as actions from "./actions";
import { DEMO_SAMPLES } from "../_shared/demoSamples";

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

  const samples = DEMO_SAMPLES;

  it("completes and restarts the synthetic demo without a submission or refresh", () => {
    render(<AnnotationClient mode="demo" samples={samples} />);
    expect(screen.getByText(/Synthetic samples/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Example 1 of 2" })).toBeInTheDocument();
    expect(screen.getAllByRole("img").map((image) => image.getAttribute("src"))).toEqual([
      "/research/dataset/033b8372e89e4c06-reference.webp",
      "/research/dataset/033b8372e89e4c06-page.webp",
    ]);
    screen.getAllByRole("img").forEach((image) => fireEvent.load(image));
    fireEvent.keyDown(window, { key: "1" });
    expect(screen.getByRole("checkbox", { name: "Wrong Color" })).toBeChecked();
    fireEvent.keyDown(window, { key: "0" });
    expect(screen.getByRole("checkbox", { name: "Wrong Color" })).not.toBeChecked();
    const different = screen.getByRole("radio", { name: /Different Character/ });
    different.focus();
    fireEvent.keyDown(different, { key: "D", shiftKey: true });
    fireEvent.keyDown(different, { key: "1" });
    expect(screen.getByRole("checkbox", { name: "Wrong Color" })).toBeChecked();
    for (const [key, label] of [
      ["2", "Wrong Species"], ["3", "Wrong Body Feature"],
      ["4", "Wrong Clothing/Accessories"], ["5", "Wrong Style"],
      ["6", "Different Face"], ["7", "Character Absent"],
    ]) {
      fireEvent.keyDown(window, { key });
      expect(screen.getByRole("checkbox", { name: label })).toBeChecked();
      fireEvent.keyDown(window, { key });
      expect(screen.getByRole("checkbox", { name: label })).not.toBeChecked();
    }
    fireEvent.keyDown(window, { key: "?" });
    expect(screen.getByRole("dialog", { name: /Shortcuts/ })).toHaveFocus();
    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByRole("heading", { name: "Example 1 of 2" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.keyDown(window, { key: "a" });
    fireEvent.keyDown(window, { key: "t" });
    fireEvent.click(screen.getByRole("button", { name: /Submit demo answer/ }));
    expect(screen.getByRole("heading", { name: "Example 2 of 2" })).toHaveFocus();
    expect(screen.getAllByRole("img").map((image) => image.getAttribute("src"))).toEqual([
      "/research/dataset/1843d7d4835a8397-reference.webp",
      "/research/dataset/1843d7d4835a8397-page.webp",
    ]);

    expect(screen.getByRole("button", { name: /Submit demo answer/ })).toBeDisabled();
    expect(screen.getByLabelText("Broken Anatomy")).not.toBeChecked();
    expect(screen.getByRole("radio", { name: /Same Character/ })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: /Different Character/ })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Wrong Color" })).not.toBeChecked();
    expect(screen.getByLabelText("Text Visible")).not.toBeChecked();
    fireEvent.keyDown(window, { key: "0" });
    expect(screen.getByRole("button", { name: /Submit demo answer/ })).toBeDisabled();
    fireEvent.keyDown(window, { key: "Enter" });
    screen.getAllByRole("img").forEach((image) => fireEvent.load(image));
    fireEvent.keyDown(window, { key: "0" });
    fireEvent.keyDown(window, { key: " " });
    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByRole("heading", { name: "Example 2 of 2" })).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByRole("heading", { name: /Demo complete/ })).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Restart demo" }));
    expect(screen.getByRole("heading", { name: "Example 1 of 2" })).toHaveFocus();
    expect(screen.getByRole("button", { name: /Submit demo answer/ })).toBeDisabled();
    expect(actions.submitAnnotation).not.toHaveBeenCalled();
    expect(mockRefresh).not.toHaveBeenCalled();
  });

  it("keeps shortcuts working from inside an open dialog and never submits from one", () => {
    render(<AnnotationClient mode="demo" samples={samples} />);
    screen.getAllByRole("img").forEach((image) => fireEvent.load(image));

    fireEvent.keyDown(window, { key: " " });
    const inspector = screen.getByRole("dialog", { name: /Image Inspector/ });
    fireEvent.keyDown(inspector, { key: "0" });
    expect(screen.getByRole("radio", { name: /Same Character/ })).toBeChecked();
    fireEvent.keyDown(inspector, { key: "Enter" });
    expect(screen.getByRole("heading", { name: "Example 1 of 2" })).toBeInTheDocument();
    fireEvent.keyDown(inspector, { key: " " });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    fireEvent.keyDown(window, { key: "?" });
    fireEvent.keyDown(screen.getByRole("dialog", { name: /Shortcuts/ }), { key: "?" });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(actions.submitAnnotation).not.toHaveBeenCalled();
  });

  it("blocks an unselected or failed-image demo and retains selections on retry", () => {
    render(<AnnotationClient mode="demo" samples={samples} />);
    fireEvent.keyDown(window, { key: "Enter" });
    screen.getAllByRole("img").forEach((image) => fireEvent.load(image));
    expect(screen.getByRole("button", { name: /Submit demo answer/ })).toBeDisabled();
    fireEvent.keyDown(window, { key: "Enter" });
    fireEvent.keyDown(window, { key: "0" });
    expect(screen.getByRole("button", { name: /Submit demo answer/ })).toBeEnabled();
    fireEvent.error(screen.getAllByRole("img")[0]);
    expect(screen.getByRole("alert")).toHaveTextContent(/sample/i);
    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByRole("heading", { name: "Example 1 of 2" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Exit demo" })).toHaveAttribute("href", "/annotate");
    fireEvent.click(screen.getByRole("button", { name: /Retry/ }));
    expect(screen.getByRole("radio", { name: /Same Character/ })).toBeChecked();
    screen.getAllByRole("img").forEach((image) => fireEvent.load(image));
    expect(screen.getByRole("button", { name: /Submit demo answer/ })).toBeEnabled();
    expect(actions.submitAnnotation).not.toHaveBeenCalled();
    expect(mockRefresh).not.toHaveBeenCalled();
  });

  it("asserts NO metadata leaks in DOM (strict blinding verification)", () => {
    const { container } = render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} />);
    
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
    render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} />);
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

  // labelling-rulebook.md Step 3: the screen accepts Different with only Clothing or Style,
  // which is always a mistake, so it warns without blocking.
  it("warns, without blocking, when Different rests on clothing or style alone", () => {
    render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} />);
    fireEvent.click(screen.getByRole("radio", { name: /Different Character/i }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Wrong Clothing/Accessories" }));

    expect(screen.getByRole("status")).toHaveTextContent(/clothing or style alone/i);
    expect(screen.getByRole("button", { name: /Submit Annotation/i })).toBeEnabled();

    fireEvent.click(screen.getByRole("checkbox", { name: "Wrong Color" }));
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("toggles gating booleans (Broken Anatomy & Text Visible) independently", () => {
    render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} />);
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
    render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} />);
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
        textFree: true,      // (!textVisible)
        round: 1
      });
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it("displays server error message on failure", async () => {
    vi.mocked(actions.submitAnnotation).mockResolvedValueOnce({
      error: "Invalid state: same_character is false but no failure reasons provided"
    });

    render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} />);
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
    render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} />);
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
        textFree: false,      // text_free is false because textVisible is true
        round: 1
      });
    });
  });
});

describe("Test-retest rounds (annotation-surface.md §4.1)", () => {
  const mockPair = {
    id: "pair-123",
    canonical_signed_url: "https://example.com/canonical-test-url.png",
    scene_signed_url: "https://example.com/scene-test-url.png",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("tells the rater which pass they are on", () => {
    render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} round={2} />);
    expect(screen.getByText(/Round 2/i)).toBeDefined();
  });

  it("submits the served round with the label", async () => {
    render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} round={2} />);
    fireEvent.click(screen.getByRole("radio", { name: /Same Character/i }));
    fireEvent.click(screen.getByRole("button", { name: /Submit/i }));

    await waitFor(() => {
      expect(actions.submitAnnotation).toHaveBeenCalledWith(
        expect.objectContaining({ pairId: "pair-123", round: 2 })
      );
    });
  });

  it("shows no trace of a previous round's answer", () => {
    const { container } = render(<AnnotationClient mode="live" submitAction={actions.submitAnnotation} pair={mockPair} round={2} />);
    const sameChar = screen.getByRole("radio", { name: /Same Character/i }) as HTMLInputElement;
    const diffChar = screen.getByRole("radio", { name: /Different Character/i }) as HTMLInputElement;
    expect(sameChar.checked).toBe(false);
    expect(diffChar.checked).toBe(false);
    expect(container.innerHTML).not.toContain("round_1");
    expect(container.innerHTML).not.toContain("previous");
  });
});
