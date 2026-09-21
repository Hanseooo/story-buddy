import type { TaxonomyState } from "./constants";

export type SubmissionPayload = {
  pairId: string;
  failureReasons: string[];
  sameCharacter: boolean;
  anatomyIntact: boolean;
  textFree: boolean;
  // Which test-retest pass this label is (migration 0018). 1 and 2 are the solo
  // rater's two cold passes; 3 is the adjudication slot. Omitted means 1, which
  // matches both the column default and how annotation_truth reads a pre-0018 row.
  round?: number;
};

export function validateSubmissionPayload(payload: SubmissionPayload) {
  const { sameCharacter, failureReasons, anatomyIntact, textFree } = payload;
  if (sameCharacter && failureReasons.length > 0) {
    return { error: "Invalid state: same_character is true but failure reasons provided" };
  }
  if (!sameCharacter && failureReasons.length === 0) {
    return { error: "Invalid state: same_character is false but no failure reasons provided" };
  }
  if (typeof anatomyIntact !== "boolean" || typeof textFree !== "boolean") {
    return { error: "Invalid state: anatomy_intact and text_free must be explicitly provided" };
  }
  return { error: null };
}

export function isConsensus(
  a1: { same_character: boolean; failure_reasons?: string[]; anatomy_intact: boolean; text_free: boolean },
  a2: { same_character: boolean; failure_reasons?: string[]; anatomy_intact: boolean; text_free: boolean }
): boolean {
  const a1Set = new Set(a1.failure_reasons || []);
  const a2Set = new Set(a2.failure_reasons || []);
  const reasonsEqual = a1Set.size === a2Set.size && [...a1Set].every(r => a2Set.has(r));
  return (
    a1.same_character === a2.same_character &&
    a1.anatomy_intact === a2.anatomy_intact &&
    a1.text_free === a2.text_free &&
    reasonsEqual
  );
}

// labelling-rulebook.md Step 3: clothing and art style are never identity on their own, so
// Different resting on them alone is always a mistake. The screen warns and still accepts it,
// as the rulebook says it does.
// Typed by the taxonomy keys, so a misspelt reason fails the build.
const NON_IDENTITY_REASONS: ReadonlySet<string> = new Set<keyof TaxonomyState>(["wrong_clothing", "wrong_style"]);

export function isNonIdentityOnly(failureReasons: string[]): boolean {
  return failureReasons.length > 0 && failureReasons.every(r => NON_IDENTITY_REASONS.has(r));
}
