import { describe, expect, it } from "vitest";
import { composeStudentEmail, normalizeNickname } from "./nickname";

// Spec §5.1 — transcribed verbatim. Do not edit without updating the Python suite too.
const PASS_VECTORS: [string, string][] = [
  ["Juan", "juan"],
  ["MARIA", "maria"],
  ["Ana Mae", "ana-mae"],
  ["  Juan  Dela   Cruz ", "juan-dela-cruz"],
  ["Niño", "nino"],
  ["José-María", "jose-maria"],
  ["Kim  -  Lee", "kim-lee"],
  ["--Jun--", "jun"],
  ["R2D2", "r2d2"],
];

const REJECT_VECTORS = [
  "Juan!",       // illegal character survives
  "J",           // under 2 characters
  "a".repeat(33), // over 32 characters
  "😀",          // non-[a-z0-9-] survives
  "ᜃᜌ",        // Baybayin — non-[a-z0-9-] survives
];

describe("normalizeNickname", () => {
  it.each(PASS_VECTORS)("normalizes %s → %s", (raw, expected) => {
    expect(normalizeNickname(raw)).toBe(expected);
  });

  it.each(REJECT_VECTORS)("rejects %s", (raw) => {
    expect(() => normalizeNickname(raw)).toThrow();
  });
});

describe("composeStudentEmail", () => {
  it("composes the login address from a raw nickname and classroom code", () => {
    expect(composeStudentEmail("Juan Dela Cruz", "k4m7pq")).toBe(
      "juan-dela-cruz@k4m7pq.students.storybuddy.invalid"
    );
  });
});
