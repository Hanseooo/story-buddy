import { FailureReason } from "@/lib/types/jobs";

export type FailureAction = "revise" | "retry" | "none";

export type FailureCopy = {
  heading: string;
  explanation: string;
  action: FailureAction;
  actionLabel: string | null;
};

/**
 * Child-facing copy for the eight ADR-038 safe reasons
 * (`docs/specs/story-failure-recovery-ux.md` §3, which owns this table).
 *
 * It is data, not a branch per reason, so the screen test can walk it instead of
 * restating it — a test that mirrors a switch passes no matter what the child sees.
 *
 * `child_text` carries the story-only sentence: there is no `jobs.title` column yet.
 * `story-titles.md` owns swapping in the "title or story" wording atomically with its
 * validation path. Never claim which field was blocked — the safe reason cannot tell them apart.
 */
export const FAILURE_COPY: Record<string, FailureCopy> = {
  child_text: {
    heading: "Some words need changing.",
    explanation: "Your story didn’t pass our safety check. You can change your words and try again.",
    action: "revise",
    actionLabel: "Change my words",
  },
  character_safety: {
    heading: "We couldn’t use a character picture.",
    explanation: "A character picture we made didn’t pass our safety check. Your story’s words passed.",
    action: "retry",
    actionLabel: "Make the story again",
  },
  scene_safety: {
    heading: "We couldn’t use a story picture.",
    explanation: "A picture we made for your story didn’t pass our safety check. Your story’s words passed.",
    action: "retry",
    actionLabel: "Make the story again",
  },
  service_busy: {
    heading: "The story maker couldn’t finish right now.",
    explanation: "A service we need was busy or unavailable. You can try making your book again.",
    action: "retry",
    actionLabel: "Make the story again",
  },
  worker_stopped: {
    heading: "The story maker stopped before finishing.",
    explanation: "You can try making your book again.",
    action: "retry",
    actionLabel: "Make the story again",
  },
  service_limit: {
    heading: "The story-making allowance has run out.",
    explanation: "Show your teacher this story reference for help.",
    action: "none",
    actionLabel: null,
  },
  book_limit: {
    heading: "This book reached its picture-making limit.",
    explanation: "Show your teacher this story reference for help.",
    action: "none",
    actionLabel: null,
  },
  system_error: {
    heading: "Something went wrong while making your book.",
    explanation: "We couldn’t finish it this time. You can try making it again.",
    action: "retry",
    actionLabel: "Make the story again",
  },
};

/** Shown adjacent to every new-job action, before activation (spec §3). Used by Part 2. */
export const RETRY_CONSEQUENCE = "This starts the whole book again. The pictures may look different.";

/**
 * `null`, legacy `machine`, and any unknown value are `system_error` (spec §2).
 * The `Object.hasOwn` guard matters: a bare index would return `Object.prototype.toString`
 * for `reason === "toString"` and render a function where the copy should be.
 */
export function resolveFailureCopy(
  reason: FailureReason | string | null | undefined
): FailureCopy {
  if (typeof reason === "string" && Object.hasOwn(FAILURE_COPY, reason)) {
    return FAILURE_COPY[reason];
  }
  return FAILURE_COPY.system_error;
}
