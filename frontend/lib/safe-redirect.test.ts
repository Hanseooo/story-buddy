import { describe, it, expect } from "vitest";
import { safe } from "./safe-redirect";

describe("safe — §9 test 5", () => {
  it("accepts a normal path", () => expect(safe("/s/x/write")).toBe("/s/x/write"));
  it("accepts bare /", () => expect(safe("/")).toBe("/"));
  it("rejects a full URL", () => expect(safe("https://evil.com")).toBeNull());
  it("rejects a protocol-relative URL (open-redirect)", () =>
    expect(safe("//evil.com")).toBeNull());
  it("rejects an empty string", () => expect(safe("")).toBeNull());
  it("rejects a relative path with no leading slash", () =>
    expect(safe("evil.com")).toBeNull());
});
