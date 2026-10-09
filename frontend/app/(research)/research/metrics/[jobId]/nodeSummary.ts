import { sceneFailureLabel, VERDICT_CHECK_LABELS } from "@/utils/metrics";
import type { RunAttempt, RunDetail } from "./types";

export type NodeSummary = { purpose: string; result: string; lines: string[]; section: { id: string; label: string } };

const STORY = { id: "story", label: "Story" };
const CHARACTERS = { id: "characters", label: "Characters" };
const PAGES = { id: "pages", label: "Pages" };
const SAFETY = { id: "safety", label: "Safety checks" };

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

// Presentation of the recorded decision, not a new pass predicate. Required findings mirror
// backend/pipeline/consistency_check.py's identity_clean/composition_clean (checked 2026-10-10).
export function reviewAttempt(attempt: RunAttempt) {
  const required: string[] = [];
  const warnings: string[] = [];
  for (const reason of attempt.failure_reasons) {
    const rejects = !attempt.passed && (reason === "wrong_colour" || reason === "wrong_body_feature");
    (rejects ? required : warnings).push(sceneFailureLabel(reason));
  }
  if (attempt.vlm_verdict) {
    for (const key of Object.keys(VERDICT_CHECK_LABELS) as (keyof typeof VERDICT_CHECK_LABELS)[]) {
      if (attempt.vlm_verdict[key] !== false) continue;
      const rejects = !attempt.passed && (key === "same_character" || key === "anatomy_intact");
      (rejects ? required : warnings).push(VERDICT_CHECK_LABELS[key]);
    }
  }
  (attempt.passed ? warnings : required).push(...(attempt.scene_contradictions ?? []));
  const outcome = attempt.passed ? "Passed required checks"
    : attempt.vlm_verdict == null && attempt.failure_reasons.length === 0 && !attempt.scene_contradictions?.length
      ? "Not checked" : "Failed required checks";
  return { outcome, required: [...new Set(required)], warnings: [...new Set(warnings)] };
}

function inputGate(run: RunDetail): string[] {
  const input = run.moderation?.input ?? null;
  const lines = [
    input == null
      ? "Input safety result not recorded."
      : input.passed
        ? "Story passed the safety check."
        : `Story flagged: ${input.categories.join(", ") || "no category given"}.`,
  ];
  if (run.story) lines.push(`${run.story.word_count} words after redaction.`);
  if (run.story?.truncated) lines.push("The story was cut to the word limit.");
  return lines;
}

function references(run: RunDetail): string[] {
  const lines = run.characters.map((c) => {
    const verdict = c.ref_verdict == null ? "not judged" : c.ref_verdict.matches_description ? "matches the description" : "does not match the description";
    return `${c.name}: reference ${verdict}.`;
  });
  return lines.length > 0 ? lines : ["No references were recorded."];
}

function attempts(run: RunDetail): string[] {
  const lines = run.scenes.flatMap((s, i) => {
    const outcome = s.shipped_attempt == null ? "no drawing selected for the book yet" : `attempt ${s.shipped_attempt + 1} selected for the book`;
    return [
      `Page ${i + 1}: ${plural(s.attempts.length, "attempt", "attempts")}, ${outcome}.`,
      ...s.attempts.map((attempt, index) => {
        const review = reviewAttempt(attempt);
        return `Page ${i + 1}, attempt ${index + 1}: ${review.outcome.toLowerCase()}.${review.required.length ? ` Required-check issues: ${review.required.join("; ")}.` : ""}${review.warnings.length ? ` Other warnings: ${review.warnings.join("; ")}.` : ""}`;
      }),
    ];
  });
  return lines.length > 0 ? lines : ["No pages were drawn."];
}

export function summarizeNodes(run: RunDetail): Record<string, NodeSummary> {
  const objects = run.state?.objects?.map((o) => o.name) ?? [];
  const places = run.state?.locations?.map((l) => l.name) ?? [];
  const shipped = run.scenes.filter((s) => s.shipped_attempt != null).length;
  const drawings = run.scenes.flatMap((s) => s.attempts);
  const passed = drawings.filter((a) => a.passed).length;
  const unchecked = drawings.filter((a) => reviewAttempt(a).outcome === "Not checked").length;
  const redrawn = run.scenes.filter((s) => s.attempts.length > 1);
  const redraws = redrawn.reduce((sum, s) => sum + s.attempts.length - 1, 0);
  const input = inputGate(run);
  const summaries: Record<string, NodeSummary> = {
    input_gate: {
      purpose: "Checks the story for unsafe content and removes personal information before illustration.",
      result: input[0], lines: input.slice(1), section: SAFETY,
    },
    analyze: {
      purpose: "Finds the characters, objects and places that the illustrations need to keep consistent.",
      result: `Recorded ${plural(run.characters.length, "character", "characters")}, ${plural(objects.length, "object", "objects")} and ${plural(places.length, "place", "places")}.`,
      lines: [
        `Characters: ${run.characters.map((c) => c.name).join(", ") || "none"}.`,
        `Objects: ${objects.join(", ") || "none"}.`,
        `Places: ${places.join(", ") || "none"}.`,
      ],
      section: STORY,
    },
    segment: {
      purpose: "Splits the story into pages and describes what each illustration should show.",
      result: `Recorded ${plural(run.scenes.length, "page", "pages")}.`,
      lines: run.scenes.length > 0 ? run.scenes.map((s, i) => `Page ${i + 1}: ${s.visual_direction ?? s.text_excerpt}`) : ["No pages were made."],
      section: PAGES,
    },
    char_bible: {
      purpose: "Creates reference images that establish how the characters should look on every page.",
      result: `${run.characters.filter((c) => c.ref_image_url != null).length} of ${run.characters.length} characters have a recorded reference image.`,
      lines: references(run), section: CHARACTERS,
    },
    char_ref_mod: {
      purpose: "Checks character reference images for unsafe content before showing them to the child.",
      result: `${run.characters.filter((c) => c.ref_moderation_status === "passed").length} of ${run.characters.length} references have a recorded safety pass.`,
      lines: [
        ...run.characters.map((c) => `${c.name}: safety ${c.ref_moderation_status ?? "result not recorded"}.`),
        `Safety redraws: ${run.cost?.ref_mod_retry_count ?? "not recorded"}.`,
      ], section: CHARACTERS,
    },
    reveal: {
      purpose: "Shows the character references so the child can accept them or request a redraw.",
      result: run.characters.some((c) => c.ref_image_url != null)
        ? "This run reached the character confirmation step."
        : "No character reference images were recorded; this step can skip the child prompt.",
      lines: [
        `Requests to redraw the references: ${run.cost?.ref_retry_count ?? "not recorded"}.`,
      ],
      section: CHARACTERS,
    },
    generate_scene: {
      purpose: "Draws each page using the story, character references and chosen illustration style.",
      result: `Recorded initial drawings for ${plural(run.scenes.filter((s) => s.attempts.length > 0).length, "page", "pages")}.`,
      lines: run.scenes.map((s, i) => `Page ${i + 1}: ${s.attempts.length > 0 ? "initial drawing recorded" : "no drawing recorded yet"}.`), section: PAGES,
    },
    consistency_check: {
      purpose: "Compares each drawing with the character references and the page's requirements.",
      result: `${plural(passed, "drawing", "drawings")} passed required checks; ${drawings.length - passed - unchecked} failed; ${unchecked} have no check result.`,
      lines: attempts(run), section: PAGES,
    },
    regenerate: {
      purpose: "Draws a new version of a page after it fails the required checks.",
      result: `Recorded ${plural(redraws, "extra drawing", "extra drawings")} across ${plural(redrawn.length, "page", "pages")}.`,
      lines: run.scenes.flatMap((s, i) => s.attempts.length > 1
        ? [`Page ${i + 1}: ${plural(s.attempts.length - 1, "redraw", "redraws")} recorded. ${s.shipped_attempt == null ? "No drawing selected for the book yet." : `Attempt ${s.shipped_attempt + 1} was selected for the book.`}`]
        : []), section: PAGES,
    },
    output_mod: {
      purpose: "Checks the selected page illustrations for unsafe content before they reach the child.",
      result: `${run.scenes.filter((s) => s.moderation_status === "passed").length} of ${run.scenes.length} pages have a recorded safety pass.`,
      lines: run.scenes.length > 0 ? run.scenes.map((s, i) => `Page ${i + 1}: safety ${s.moderation_status ?? "not checked"}.`) : ["No pages were checked."],
      section: SAFETY,
    },
    compose: {
      purpose: "Assembles the selected illustrations and captions into the storybook.",
      result: `${shipped} of ${run.scenes.length} pages have a drawing selected for the book.`,
      lines: run.scenes.map((s, i) => `Page ${i + 1}: ${s.shipped_attempt == null ? "no drawing selected yet" : `attempt ${s.shipped_attempt + 1} selected`}.`), section: PAGES,
    },
  };
  for (const [id, summary] of Object.entries(summaries)) {
    const ended = run.ended_on?.node === id ? run.ended_on.kind : null;
    if (ended === "waiting") {
      summary.result = "Waiting for the child to confirm the character references.";
    } else if (ended === "running" || ended === "failed") {
      summary.lines.unshift(summary.result);
      summary.result = ended === "running"
        ? "This step is still running. Results below are not final."
        : "The run stopped at this step. Its result may be incomplete.";
    } else if (!run.steps.some((step) => step.node === id)) {
      summary.result = "This step did not run.";
      summary.lines = [];
    }
  }
  return summaries;
}
