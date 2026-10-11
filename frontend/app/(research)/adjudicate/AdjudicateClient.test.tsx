import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AdjudicateClient from "./AdjudicateClient";
import * as actions from "./actions";
import { DEMO_SAMPLES } from "../_shared/demoSamples";

const mockRefresh = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRefresh }),
}));

vi.mock("./actions", () => ({
  submitAdjudication: vi.fn().mockResolvedValue({ success: true }),
}));

describe("AdjudicateClient Component Tests", () => {
  const mockPair = {
    id: "pair-conflict-123",
    canonical_signed_url: "https://example.com/canonical-test.png",
    scene_signed_url: "https://example.com/scene-test.png",
  };

  const mockAnnotationA = {
    same_character: true,
    failure_reasons: [],
    anatomy_intact: true,
    text_free: true,
  };

  const mockAnnotationB = {
    same_character: false,
    failure_reasons: ["wrong_colour", "wrong_style"],
    anatomy_intact: false,
    text_free: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const samples = DEMO_SAMPLES;

  it("completes and restarts the synthetic demo without a submission or refresh", () => {
    render(<AdjudicateClient mode="demo" samples={samples} />);
    expect(screen.getByText(/Synthetic samples/)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Example 1 of 2" })).toBeInTheDocument();
    expect(screen.getAllByRole("img").map((image) => image.getAttribute("src"))).toEqual([
      "/research/dataset/033b8372e89e4c06-reference.webp",
      "/research/dataset/033b8372e89e4c06-page.webp",
    ]);
    expect(screen.getAllByText("Disagreement")).toHaveLength(2);
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
    fireEvent.click(screen.getByRole("button", { name: /Submit demo decision/ }));
    expect(screen.getByRole("heading", { name: "Example 2 of 2" })).toHaveFocus();
    expect(screen.getAllByRole("img").map((image) => image.getAttribute("src"))).toEqual([
      "/research/dataset/1843d7d4835a8397-reference.webp",
      "/research/dataset/1843d7d4835a8397-page.webp",
    ]);
    expect(screen.getAllByText("Disagreement")).toHaveLength(3);

    expect(screen.getByRole("button", { name: /Submit demo decision/ })).toBeDisabled();
    expect(screen.getByLabelText("Broken Anatomy")).not.toBeChecked();
    expect(screen.getByRole("radio", { name: /Same Character/ })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: /Different Character/ })).not.toBeChecked();
    expect(screen.getByRole("checkbox", { name: "Wrong Color" })).not.toBeChecked();
    expect(screen.getByLabelText("Text Visible")).not.toBeChecked();
    fireEvent.keyDown(window, { key: "0" });
    expect(screen.getByRole("button", { name: /Submit demo decision/ })).toBeDisabled();
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
    expect(screen.getByRole("button", { name: /Submit demo decision/ })).toBeDisabled();
    expect(actions.submitAdjudication).not.toHaveBeenCalled();
    expect(mockRefresh).not.toHaveBeenCalled();
  });

  it("labels the demo comparison as illustrative, not as blinded rater answers", () => {
    render(<AdjudicateClient mode="demo" samples={samples} />);

    const summary = screen.getByRole("region", { name: "Annotator Discrepancies" });
    expect(within(summary).getByText("Illustrative disagreements — not recorded rater answers")).toBeInTheDocument();
    expect(screen.queryByText(/Blinded Dual Annotations/)).not.toBeInTheDocument();
  });

  it("keeps shortcuts working from inside an open dialog and never submits from one", () => {
    render(<AdjudicateClient mode="demo" samples={samples} />);
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
    expect(actions.submitAdjudication).not.toHaveBeenCalled();
  });

  it("blocks an unselected or failed-image demo and retains selections on retry", () => {
    render(<AdjudicateClient mode="demo" samples={samples} />);
    fireEvent.keyDown(window, { key: "Enter" });
    screen.getAllByRole("img").forEach((image) => fireEvent.load(image));
    expect(screen.getByRole("button", { name: /Submit demo decision/ })).toBeDisabled();
    fireEvent.keyDown(window, { key: "Enter" });
    fireEvent.keyDown(window, { key: "0" });
    expect(screen.getByRole("button", { name: /Submit demo decision/ })).toBeEnabled();
    fireEvent.error(screen.getAllByRole("img")[0]);
    expect(screen.getByRole("alert")).toHaveTextContent(/sample/i);
    fireEvent.keyDown(window, { key: "Enter" });
    expect(screen.getByRole("heading", { name: "Example 1 of 2" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Exit demo" })).toHaveAttribute("href", "/adjudicate");
    fireEvent.click(screen.getByRole("button", { name: /Retry/ }));
    expect(screen.getByRole("radio", { name: /Same Character/ })).toBeChecked();
    screen.getAllByRole("img").forEach((image) => fireEvent.load(image));
    expect(screen.getByRole("button", { name: /Submit demo decision/ })).toBeEnabled();
    expect(actions.submitAdjudication).not.toHaveBeenCalled();
    expect(mockRefresh).not.toHaveBeenCalled();
  });

  it("asserts NO metadata leaks in DOM (strict blinding verification)", () => {
    const { container } = render(
      <AdjudicateClient
        mode="live" submitAction={actions.submitAdjudication}
        pair={mockPair}
        annotationA={mockAnnotationA}
        annotationB={mockAnnotationB}
      />
    );

    // DOM should contain the signed URLs and image elements
    expect(container.innerHTML).toContain("https://example.com/canonical-test.png");
    expect(container.innerHTML).toContain("https://example.com/scene-test.png");

    // DOM must NOT leak annotator IDs, emails, timestamps, or secret DB columns
    expect(container.innerHTML).not.toContain("annotator_id");
    expect(container.innerHTML).not.toContain("user_id");
    expect(container.innerHTML).not.toContain("created_at");
    expect(container.innerHTML).not.toContain("char_id");
    expect(container.innerHTML).not.toContain("is_pilot");
    expect(container.innerHTML).not.toContain("is_constructed_negative");
    expect(container.innerHTML).not.toContain("split");
    expect(container.innerHTML).not.toContain("canonical_storage_path");
    expect(container.innerHTML).not.toContain("scene_storage_path");
  });

  it("renders conflict summary highlighting differing fields between Annotator 1 and Annotator 2", () => {
    render(
      <AdjudicateClient
        mode="live" submitAction={actions.submitAdjudication}
        pair={mockPair}
        annotationA={mockAnnotationA}
        annotationB={mockAnnotationB}
      />
    );

    expect(screen.getByText("Conflicts Detected")).toBeInTheDocument();
    expect(screen.getAllByText("A1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("A2").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Same Character").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Failure Reasons")).toBeInTheDocument();
    expect(screen.getAllByText("Broken Anatomy").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Text Visible").length).toBeGreaterThanOrEqual(1);
  });

  it("handles form state transitions between Same Character and failure taxonomy", () => {
    render(
      <AdjudicateClient
        mode="live" submitAction={actions.submitAdjudication}
        pair={mockPair}
        annotationA={mockAnnotationA}
        annotationB={mockAnnotationB}
      />
    );

    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });
    const diffCharRadio = screen.getByRole("radio", { name: /Different Character/i });
    const wrongColorCheckbox = screen.getByLabelText(/Wrong Color/i);
    const wrongSpeciesCheckbox = screen.getByLabelText(/Wrong Species/i);

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

    fireEvent.click(wrongSpeciesCheckbox);
    expect(wrongColorCheckbox).toBeChecked();
    expect(wrongSpeciesCheckbox).toBeChecked();

    // Clicking Same Character clears all failure reasons
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
    render(
      <AdjudicateClient
        mode="live" submitAction={actions.submitAdjudication}
        pair={mockPair}
        annotationA={mockAnnotationA}
        annotationB={mockAnnotationB}
      />
    );

    const brokenAnatomyCheckbox = screen.getByLabelText(/Broken Anatomy/i);
    const textVisibleCheckbox = screen.getByLabelText(/Text Visible/i);
    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });

    fireEvent.click(sameCharRadio);
    expect(sameCharRadio).toBeChecked();

    fireEvent.click(brokenAnatomyCheckbox);
    expect(brokenAnatomyCheckbox).toBeChecked();
    expect(sameCharRadio).toBeChecked();

    fireEvent.click(textVisibleCheckbox);
    expect(textVisibleCheckbox).toBeChecked();
  });

  it("submits authoritative adjudication decision and refreshes router", async () => {
    render(
      <AdjudicateClient
        mode="live" submitAction={actions.submitAdjudication}
        pair={mockPair}
        annotationA={mockAnnotationA}
        annotationB={mockAnnotationB}
      />
    );

    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });
    const submitBtn = screen.getByRole("button", { name: /Submit Final Decision/i });

    fireEvent.click(sameCharRadio);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(actions.submitAdjudication).toHaveBeenCalledWith({
        pairId: "pair-conflict-123",
        failureReasons: [],
        sameCharacter: true,
        anatomyIntact: true, // (!brokenAnatomy)
        textFree: true       // (!textVisible)
      });
      expect(mockRefresh).toHaveBeenCalled();
    });
  });

  it("displays server error message on failure", async () => {
    vi.mocked(actions.submitAdjudication).mockResolvedValueOnce({
      error: "Pair is no longer conflicted",
    });

    render(
      <AdjudicateClient
        mode="live" submitAction={actions.submitAdjudication}
        pair={mockPair}
        annotationA={mockAnnotationA}
        annotationB={mockAnnotationB}
      />
    );

    const sameCharRadio = screen.getByRole("radio", { name: /Same Character/i });
    const submitBtn = screen.getByRole("button", { name: /Submit Final Decision/i });
    
    // Make submission valid
    fireEvent.click(sameCharRadio);
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText("Pair is no longer conflicted")).toBeInTheDocument();
    });
  });

  it("supports keyboard shortcuts (0, 1-7, A, T, Enter)", async () => {
    render(
      <AdjudicateClient
        mode="live" submitAction={actions.submitAdjudication}
        pair={mockPair}
        annotationA={mockAnnotationA}
        annotationB={mockAnnotationB}
      />
    );

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

    // Shortcut 'Shift+D' for Different Character
    fireEvent.keyDown(window, { key: "D", shiftKey: true });
    expect(diffCharRadio).toBeChecked();
    expect(sameCharRadio).not.toBeChecked();

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
      expect(actions.submitAdjudication).toHaveBeenCalledWith({
        pairId: "pair-conflict-123",
        failureReasons: ["wrong_colour"],
        sameCharacter: false, // explicit same character is false
        anatomyIntact: false, // anatomy_intact is false
        textFree: false       // text_free is false
      });
    });
  });
});
