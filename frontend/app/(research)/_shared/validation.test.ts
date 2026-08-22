import { describe, it, expect } from "vitest";
import { validateSubmissionPayload, isConsensus, type SubmissionPayload } from "./validation";

describe("validation.ts unit tests", () => {
  describe("validateSubmissionPayload", () => {
    it("returns error if sameCharacter is true and failureReasons is non-empty", () => {
      const payload: SubmissionPayload = {
        pairId: "pair-1",
        failureReasons: ["wrong_colour"],
        sameCharacter: true,
        anatomyIntact: true,
        textFree: true,
      };
      const res = validateSubmissionPayload(payload);
      expect(res.error).toBe("Invalid state: same_character is true but failure reasons provided");
    });

    it("returns error if sameCharacter is false and failureReasons is empty", () => {
      const payload: SubmissionPayload = {
        pairId: "pair-1",
        failureReasons: [],
        sameCharacter: false,
        anatomyIntact: true,
        textFree: true,
      };
      const res = validateSubmissionPayload(payload);
      expect(res.error).toBe("Invalid state: same_character is false but no failure reasons provided");
    });

    it("returns error if anatomyIntact is not a boolean", () => {
      const payload = {
        pairId: "pair-1",
        failureReasons: [],
        sameCharacter: true,
        anatomyIntact: "yes" as unknown as boolean,
        textFree: true,
      };
      const res = validateSubmissionPayload(payload);
      expect(res.error).toBe("Invalid state: anatomy_intact and text_free must be explicitly provided");
    });

    it("returns error if textFree is not a boolean", () => {
      const payload = {
        pairId: "pair-1",
        failureReasons: [],
        sameCharacter: true,
        anatomyIntact: true,
        textFree: null as unknown as boolean,
      };
      const res = validateSubmissionPayload(payload);
      expect(res.error).toBe("Invalid state: anatomy_intact and text_free must be explicitly provided");
    });

    it("returns null error for valid sameCharacter=true payload", () => {
      const payload: SubmissionPayload = {
        pairId: "pair-1",
        failureReasons: [],
        sameCharacter: true,
        anatomyIntact: true,
        textFree: true,
      };
      const res = validateSubmissionPayload(payload);
      expect(res.error).toBeNull();
    });

    it("returns null error for valid sameCharacter=false payload", () => {
      const payload: SubmissionPayload = {
        pairId: "pair-1",
        failureReasons: ["wrong_style", "wrong_species"],
        sameCharacter: false,
        anatomyIntact: false,
        textFree: false,
      };
      const res = validateSubmissionPayload(payload);
      expect(res.error).toBeNull();
    });
  });

  describe("isConsensus", () => {
    it("returns true when both same_character=true and all fields match", () => {
      const a1 = { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true };
      const a2 = { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true };
      expect(isConsensus(a1, a2)).toBe(true);
    });

    it("returns true when same_character=false, reasons match (even with duplicates or different order)", () => {
      const a1 = { same_character: false, failure_reasons: ["wrong_style", "wrong_colour"], anatomy_intact: true, text_free: false };
      const a2 = { same_character: false, failure_reasons: ["wrong_colour", "wrong_style", "wrong_colour"], anatomy_intact: true, text_free: false };
      expect(isConsensus(a1, a2)).toBe(true);
    });

    it("handles undefined failure_reasons gracefully", () => {
      const a1 = { same_character: true, anatomy_intact: true, text_free: true };
      const a2 = { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true };
      expect(isConsensus(a1, a2)).toBe(true);
    });

    it("returns false when same_character disagrees", () => {
      const a1 = { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true };
      const a2 = { same_character: false, failure_reasons: ["wrong_colour"], anatomy_intact: true, text_free: true };
      expect(isConsensus(a1, a2)).toBe(false);
    });

    it("returns false when anatomy_intact disagrees", () => {
      const a1 = { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true };
      const a2 = { same_character: true, failure_reasons: [], anatomy_intact: false, text_free: true };
      expect(isConsensus(a1, a2)).toBe(false);
    });

    it("returns false when text_free disagrees", () => {
      const a1 = { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true };
      const a2 = { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: false };
      expect(isConsensus(a1, a2)).toBe(false);
    });

    it("returns false when failure_reasons disagree", () => {
      const a1 = { same_character: false, failure_reasons: ["wrong_style"], anatomy_intact: true, text_free: true };
      const a2 = { same_character: false, failure_reasons: ["wrong_colour"], anatomy_intact: true, text_free: true };
      expect(isConsensus(a1, a2)).toBe(false);
    });
  });
});
