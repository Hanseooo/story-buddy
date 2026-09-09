import { describe, expect, it } from "vitest";
import { displayTitle } from "./displayTitle";

describe("displayTitle", () => {
  it("returns the stored title when nonblank", () => {
    expect(displayTitle("My Dragon Book", "Once upon a time a dragon...")).toBe(
      "My Dragon Book"
    );
  });

  it("falls back to the first line when title is null", () => {
    expect(displayTitle(null, "Once upon a time\nthe rest of the story")).toBe(
      "Once upon a time"
    );
  });

  it("falls back to the excerpt when title is an empty string or whitespace", () => {
    expect(displayTitle("", "A brave knight went on an adventure")).toBe(
      "A brave knight went on an adventure"
    );
    expect(displayTitle("   ", "A story about a cat")).toBe("A story about a cat");
  });

  it("truncates the excerpt fallback to 60 characters", () => {
    expect(displayTitle(null, "x".repeat(80))).toBe("x".repeat(60));
  });

  it("falls back to Untitled when there is no title and no story text", () => {
    expect(displayTitle(null, "")).toBe("Untitled");
    expect(displayTitle(undefined, undefined)).toBe("Untitled");
  });
});
