import { EXAMPLES } from "../research/(reference)/dataset/data";
import type { BlindAnnotation } from "../adjudicate/actions";
import type { ResearchPair } from "./constants";

export type DemoSample = {
  pair: ResearchPair;
  annotationA: BlindAnnotation;
  annotationB: BlindAnnotation;
};

function examplePair(sourceId: string, demoId: string): ResearchPair {
  const example = EXAMPLES.find(({ record }) => record.pair_id === sourceId);
  if (!example || example.record.provenance !== "synthetic" || example.record.pair_type !== "pipeline") {
    throw new Error(`Missing approved synthetic demo pair: ${sourceId}`);
  }

  return {
    id: demoId,
    canonical_signed_url: example.reference.src,
    scene_signed_url: example.page.src,
  };
}

// The answers below are invented only to demonstrate adjudication conflicts. They are not
// observations from the frozen research examples or recorded annotations.
export const DEMO_SAMPLES: DemoSample[] = [
  {
    pair: examplePair("033b8372e89e4c06", "demo-syn-025-c0"),
    annotationA: {
      same_character: true,
      failure_reasons: [],
      anatomy_intact: true,
      text_free: true,
    },
    annotationB: {
      same_character: false,
      failure_reasons: ["different_face"],
      anatomy_intact: true,
      text_free: true,
    },
  },
  {
    pair: examplePair("1843d7d4835a8397", "demo-syn-016-c0"),
    annotationA: {
      same_character: false,
      failure_reasons: ["different_face"],
      anatomy_intact: true,
      text_free: true,
    },
    annotationB: {
      same_character: false,
      failure_reasons: ["different_face", "wrong_body_feature"],
      anatomy_intact: false,
      text_free: false,
    },
  },
];
