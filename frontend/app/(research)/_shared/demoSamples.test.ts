import { describe, expect, it } from "vitest";
import { EXAMPLES } from "../research/(reference)/dataset/data";
import { DEMO_SAMPLES } from "./demoSamples";
import { existsSync } from "node:fs";
import path from "node:path";
import { TAXONOMY_LABELS } from "./constants";
import { validateSubmissionPayload } from "./validation";

describe("DEMO_SAMPLES", () => {
  it("uses the two approved synthetic pipeline examples in order", () => {
    expect(DEMO_SAMPLES.map(({ pair }) => pair.id)).toEqual([
      "demo-syn-025-c0",
      "demo-syn-016-c0",
    ]);

    const sourceIds = ["033b8372e89e4c06", "1843d7d4835a8397"];
    for (const [index, sourceId] of sourceIds.entries()) {
      const source = EXAMPLES.find((example) => example.record.pair_id === sourceId);
      expect(source?.record.provenance).toBe("synthetic");
      expect(source?.record.pair_type).toBe("pipeline");
      expect(DEMO_SAMPLES[index].pair.canonical_signed_url).toBe(source?.reference.src);
      expect(DEMO_SAMPLES[index].pair.scene_signed_url).toBe(source?.page.src);
      for (const url of [DEMO_SAMPLES[index].pair.canonical_signed_url, DEMO_SAMPLES[index].pair.scene_signed_url]) {
        expect(url).toMatch(/^\/research\/dataset\/[a-f0-9]+-(reference|page)\.webp$/);
        expect(existsSync(path.join(process.cwd(), "public", url))).toBe(true);
      }
    }
    expect(JSON.stringify(DEMO_SAMPLES)).not.toContain("don-");
  });

  it("includes illustrative adjudication disagreements across the conflict fields", () => {
    expect(DEMO_SAMPLES.map(({ annotationA, annotationB }) => [annotationA, annotationB])).toEqual([
      [
        { same_character: true, failure_reasons: [], anatomy_intact: true, text_free: true },
        { same_character: false, failure_reasons: ["different_face"], anatomy_intact: true, text_free: true },
      ],
      [
        { same_character: false, failure_reasons: ["different_face"], anatomy_intact: true, text_free: true },
        { same_character: false, failure_reasons: ["different_face", "wrong_body_feature"], anatomy_intact: false, text_free: false },
      ],
    ]);
    for (const sample of DEMO_SAMPLES) {
      for (const annotation of [sample.annotationA, sample.annotationB]) {
        for (const reason of annotation.failure_reasons) expect(reason in TAXONOMY_LABELS).toBe(true);
        expect(validateSubmissionPayload({ pairId: sample.pair.id, sameCharacter: annotation.same_character, failureReasons: annotation.failure_reasons, anatomyIntact: annotation.anatomy_intact, textFree: annotation.text_free })).toEqual({ error: null });
      }
    }
    expect(DEMO_SAMPLES.map(({ annotationA, annotationB }) => [
      annotationA.same_character !== annotationB.same_character,
      annotationA.failure_reasons.join(",") !== annotationB.failure_reasons.join(","),
      annotationA.anatomy_intact !== annotationB.anatomy_intact,
      annotationA.text_free !== annotationB.text_free,
    ])).toEqual([
      [true, true, false, false],
      [false, true, true, true],
    ]);
  });
});
