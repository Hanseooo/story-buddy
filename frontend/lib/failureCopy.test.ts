import { describe, it, expect } from "vitest";
import { FAILURE_COPY, resolveFailureCopy, SafeReason } from "./failureCopy";

const REASONS: SafeReason[] = [
  "child_text", "character_safety", "scene_safety", "service_busy",
  "worker_stopped", "service_limit", "book_limit", "system_error",
];

/**
 * `story-failure-recovery-ux.md` §3, transcribed. The child never sees a diff, so drift in this
 * table is invisible until a class does. Editing a string here is meant to be the moment you
 * check the spec still says it — `child_text` in particular is due to change with `story-titles`.
 */
const SPEC_COPY: Record<SafeReason, [heading: string, explanation: string]> = {
  child_text: [
    "Some words need changing.",
    "The submitted title or story didn’t pass the input safety check. You can change your title or words and try again.",
  ],
  character_safety: [
    "We couldn’t use a character picture.",
    "A character picture we made didn’t pass our safety check. Your story’s words passed.",
  ],
  scene_safety: [
    "We couldn’t use a story picture.",
    "A picture we made for your story didn’t pass our safety check. Your story’s words passed.",
  ],
  service_busy: [
    "The story maker couldn’t finish right now.",
    "A service we need was busy or unavailable. You can try making your book again.",
  ],
  worker_stopped: [
    "The story maker stopped before finishing.",
    "You can try making your book again.",
  ],
  service_limit: [
    "The story-making allowance has run out.",
    "Show your teacher this story reference for help.",
  ],
  book_limit: [
    "This book reached its picture-making limit.",
    "Show your teacher this story reference for help.",
  ],
  system_error: [
    "Something went wrong while making your book.",
    "We couldn’t finish it this time. You can try making it again.",
  ],
};

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
    const remakes: SafeReason[] = ["character_safety", "scene_safety", "service_busy", "worker_stopped", "system_error"];
    for (const r of remakes) {
      expect(FAILURE_COPY[r].action).toBe("retry");
      expect(FAILURE_COPY[r].actionLabel).toBe("Make the story again");
    }
  });

  it("says the child's words passed on both image-safety reasons", () => {
    expect(FAILURE_COPY.character_safety.explanation).toContain("Your story’s words passed.");
    expect(FAILURE_COPY.scene_safety.explanation).toContain("Your story’s words passed.");
  });

  it.each(REASONS)("%s matches the spec §3 heading and explanation word for word", (reason) => {
    const [heading, explanation] = SPEC_COPY[reason];
    expect(FAILURE_COPY[reason].heading).toBe(heading);
    expect(FAILURE_COPY[reason].explanation).toBe(explanation);
  });

  it("child_text names both title and story after titles ship", () => {
    expect(FAILURE_COPY.child_text.explanation).toContain("title or story");
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
