import { describe, it, expect } from "vitest";
import { FAILURE_COPY, resolveFailureCopy } from "./failureCopy";

const REASONS = [
  "child_text", "character_safety", "scene_safety", "service_busy",
  "worker_stopped", "service_limit", "book_limit", "system_error",
];

describe("FAILURE_COPY", () => {
  it("has exactly the eight ADR-038 reasons and nothing else", () => {
    expect(Object.keys(FAILURE_COPY).sort()).toEqual([...REASONS].sort());
  });

  it("gives every reason a heading and a separate explanation", () => {
    for (const r of REASONS) {
      expect(FAILURE_COPY[r].heading.length).toBeGreaterThan(0);
      expect(FAILURE_COPY[r].explanation.length).toBeGreaterThan(0);
      expect(FAILURE_COPY[r].explanation).not.toBe(FAILURE_COPY[r].heading);
    }
  });

  it("offers no action for the two limit reasons", () => {
    expect(FAILURE_COPY.service_limit.action).toBe("none");
    expect(FAILURE_COPY.service_limit.actionLabel).toBeNull();
    expect(FAILURE_COPY.book_limit.action).toBe("none");
    expect(FAILURE_COPY.book_limit.actionLabel).toBeNull();
  });

  it("only child_text revises; every other actionable reason remakes the whole book", () => {
    expect(FAILURE_COPY.child_text.action).toBe("revise");
    for (const r of ["character_safety", "scene_safety", "service_busy", "worker_stopped", "system_error"]) {
      expect(FAILURE_COPY[r].action).toBe("retry");
      expect(FAILURE_COPY[r].actionLabel).toBe("Make the story again");
    }
  });

  it("says the child's words passed on both image-safety reasons", () => {
    expect(FAILURE_COPY.character_safety.explanation).toContain("Your story’s words passed.");
    expect(FAILURE_COPY.scene_safety.explanation).toContain("Your story’s words passed.");
  });

  it("uses the story-only child_text sentence until titles ship", () => {
    expect(FAILURE_COPY.child_text.explanation).toBe(
      "Your story didn’t pass our safety check. You can change your words and try again."
    );
  });
});

describe("resolveFailureCopy", () => {
  it("returns the exact entry for each known reason", () => {
    for (const r of REASONS) expect(resolveFailureCopy(r)).toBe(FAILURE_COPY[r]);
  });

  it.each([null, undefined, "machine", "unknown_garbage", ""])(
    "falls back to system_error for %s",
    (reason) => {
      expect(resolveFailureCopy(reason as string | null | undefined)).toBe(FAILURE_COPY.system_error);
    }
  );

  it.each(["toString", "constructor", "hasOwnProperty", "__proto__"])(
    "does not leak the Object prototype for the inherited key %s",
    (reason) => {
      expect(resolveFailureCopy(reason)).toBe(FAILURE_COPY.system_error);
    }
  );
});
