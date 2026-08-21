export type SubmissionPayload = {
  pairId: string;
  failureReasons: string[];
  sameCharacter: boolean;
  anatomyIntact: boolean;
  textFree: boolean;
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
