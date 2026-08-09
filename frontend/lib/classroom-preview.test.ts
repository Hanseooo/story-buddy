import { describe, expect, it } from "vitest";
import { computePreview } from "./classroom-preview";

const EMPTY = new Set<string>();

// Test 15: Maria Santos + Maria Reyes under "first" escalate to maria-s / maria-r
describe("computePreview — collision escalation", () => {
  it("test 15a: two Maria* names escalate to first-last-initial under 'first' preset", () => {
    const rows = computePreview(["Maria Santos", "Maria Reyes"], EMPTY, "first");
    const nicknames = rows.map((r) => r.nickname);
    expect(nicknames).toContain("maria-s");
    expect(nicknames).toContain("maria-r");
    rows.forEach((r) => expect(r.editable).toBe(false));
  });

  it("test 15b: non-colliding names under 'first' stay at level 0", () => {
    const rows = computePreview(["Ana", "Juan"], EMPTY, "first");
    expect(rows[0].nickname).toBe("ana");
    expect(rows[1].nickname).toBe("juan");
    rows.forEach((r) => expect(r.editable).toBe(false));
  });

  it("test 15c: collisions against existing roster also escalate", () => {
    const existing = new Set(["maria"]);
    const rows = computePreview(["Maria Santos"], existing, "first");
    expect(rows[0].nickname).toBe("maria-s");
    expect(rows[0].editable).toBe(false);
  });

  // Test 16: single-token name colliding → level 2, no crash
  it("test 16: single-token name colliding escalates to level 2 (not a crash)", () => {
    const existing = new Set(["madonna"]);
    const rows = computePreview(["Madonna"], existing, "first");
    expect(rows[0].editable).toBe(true);
    expect(rows[0].reason).toBeDefined();
  });

  it("test 16b: two identical single-token names — second one goes to level 2", () => {
    const rows = computePreview(["Madonna", "Madonna"], EMPTY, "first");
    expect(rows[0].editable).toBe(false);
    expect(rows[1].editable).toBe(true);
  });
});

// Test 17: rejection vectors mark rows editable, not crash
describe("computePreview — normalization rejections", () => {
  const REJECTION_CASES = [
    ["Juan!", "illegal character"],
    ["J", "too short"],
    ["😀", "emoji"],
    ["ᜃᜌ", "Baybayin"],
  ] as const;

  it.each(REJECTION_CASES)(
    "test 17: '%s' (%s) → editable row, no throw",
    (name) => {
      expect(() => computePreview([name], EMPTY, "first")).not.toThrow();
      const rows = computePreview([name], EMPTY, "first");
      expect(rows[0].editable).toBe(true);
      expect(rows[0].reason).toBeDefined();
    }
  );

  it("test 17b: rejection does not block other rows in the same paste", () => {
    const rows = computePreview(["Juan!", "Ana"], EMPTY, "first");
    expect(rows).toHaveLength(2);
    expect(rows[0].editable).toBe(true);  // Juan! rejected
    expect(rows[1].editable).toBe(false); // Ana fine
  });

  it("test 17c: 33-char name normalizes to over-32 → editable", () => {
    const long = "a".repeat(33);
    const rows = computePreview([long], EMPTY, "first");
    expect(rows[0].editable).toBe(true);
  });
});

// Preset behavior
describe("computePreview — presets", () => {
  it("full preset preserves full name", () => {
    const rows = computePreview(["Juan Dela Cruz"], EMPTY, "full");
    expect(rows[0].displayNickname).toBe("Juan Dela Cruz");
    expect(rows[0].nickname).toBe("juan-dela-cruz");
  });

  it("first-last-initial preset produces 'Juan D.'", () => {
    const rows = computePreview(["Juan Dela Cruz"], EMPTY, "first-last-initial");
    expect(rows[0].displayNickname).toBe("Juan D.");
  });

  it("empty lines are skipped", () => {
    const rows = computePreview(["", "  ", "Ana", ""], EMPTY, "first");
    expect(rows).toHaveLength(1);
    expect(rows[0].nickname).toBe("ana");
  });
});
