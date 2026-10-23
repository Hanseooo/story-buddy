import { render, screen, fireEvent } from "@testing-library/react";
import { expect, it, vi, beforeEach, describe } from "vitest";
import JoinPage from "./page";

const mockPush = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

describe("Join page — step 1 (§9.9, §9.8 code step)", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders six code input boxes", () => {
    render(<JoinPage />);
    const inputs = screen.getAllByRole("textbox");
    expect(inputs).toHaveLength(6);
  });

  it("accepts every generated code character in either case, including L", () => {
    render(<JoinPage />);
    const input = screen.getAllByRole("textbox")[0];
    for (const char of "LABCDEFGHJKMNPQRSTUVWXYZ23456789labcdefghjkmnpqrstuvwxyz") {
      fireEvent.change(input, { target: { value: char } });
      expect(input).toHaveValue(char.toLowerCase());
    }
  });

  it("§9.9 — invalid characters do not enter and show hint for typing and paste", () => {
    render(<JoinPage />);
    const inputs = screen.getAllByRole("textbox");
    const EXCLUDED = ["0", "O", "o", "1", "I", "i", "!", "/", " ", "é"];

    for (const char of EXCLUDED) {
      fireEvent.keyDown(inputs[0], { key: char });
      fireEvent.change(inputs[0], { target: { value: char } });
      expect(inputs[0]).toHaveValue("");
      expect(screen.getByRole("alert")).toHaveTextContent(
        "That letter isn't used in class codes."
      );
      fireEvent.paste(inputs[0], { clipboardData: { getData: () => char } });
      expect(inputs[0]).toHaveValue("");
    }
  });

  it("§9.9 — valid chars enter without showing hint", () => {
    render(<JoinPage />);
    const inputs = screen.getAllByRole("textbox");
    fireEvent.keyDown(inputs[0], { key: "a" });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("advances to next box on valid character entry", () => {
    render(<JoinPage />);
    const inputs = screen.getAllByRole("textbox");
    fireEvent.change(inputs[0], { target: { value: "a" } });
    // Next box should receive focus — we check by seeing inputs[1] focused
    expect(document.activeElement).toBe(inputs[1]);
  });

  it("handles paste: strips excluded chars and fills boxes", () => {
    render(<JoinPage />);
    const group = screen.getByRole("group", { name: /class code/i });
    const pasteData = { getData: () => "aL0!cd2" }; // Invalid characters are stripped, L is preserved.
    fireEvent.paste(group, { clipboardData: pasteData });
    const inputs = screen.getAllByRole("textbox");
    expect(inputs[0]).toHaveValue("a");
    expect(inputs[1]).toHaveValue("l");
    expect(inputs[2]).toHaveValue("c");
    expect(inputs[3]).toHaveValue("d");
    expect(inputs[4]).toHaveValue("2");
    expect(inputs[5]).toHaveValue("");
  });

  it("§9.8 — submit button disabled until all 6 boxes filled", () => {
    render(<JoinPage />);
    const submit = screen.getByRole("button", { name: /join class/i });
    expect(submit).toBeDisabled();
  });

  it("navigates to /join/[code] when 6 chars entered and submitted", () => {
    render(<JoinPage />);
    const inputs = screen.getAllByRole("textbox");
    ["a", "b", "c", "d", "e", "f"].forEach((c, i) => {
      fireEvent.change(inputs[i], { target: { value: c } });
    });
    fireEvent.click(screen.getByRole("button", { name: /join class/i }));
    expect(mockPush).toHaveBeenCalledWith("/join/abcdef");
  });
});
