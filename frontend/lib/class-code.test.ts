import { describe, expect, it } from "vitest";
import { normalizeCode, toCodeChar } from "./class-code";

describe("toCodeChar", () => {
  it("takes any letter or digit as its lowercase self", () => {
    for (const c of ["A", "z", "L", "I", "i", "1", "O", "0", "9"]) {
      expect(toCodeChar(c)).toBe(c.toLowerCase());
    }
  });

  it("rejects anything that isn't a single letter or digit", () => {
    for (const c of ["!", "/", " ", "é", "ab"]) expect(toCodeChar(c)).toBeNull();
  });
});

describe("normalizeCode", () => {
  it("lowercases a six-character code without changing any character", () => {
    expect(normalizeCode("ABCI1Z")).toBe("abci1z");
  });

  it("rejects the wrong length or a non-alphanumeric character", () => {
    expect(normalizeCode("abc")).toBeNull();
    expect(normalizeCode("abcdefg")).toBeNull();
    expect(normalizeCode("abcde!")).toBeNull();
  });
});
