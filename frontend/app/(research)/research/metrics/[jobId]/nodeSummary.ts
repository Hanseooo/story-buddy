import { sceneFailureLabel } from "@/utils/metrics";
import type { RunDetail } from "./types";

export type NodeSummary = { lines: string[]; section: { id: string; label: string } };

const STORY = { id: "story", label: "Story" };
const CHARACTERS = { id: "characters", label: "Characters" };
const PAGES = { id: "pages", label: "Pages" };
const SAFETY = { id: "safety", label: "Safety checks" };

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

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
    return `${c.name}: reference ${verdict}; safety ${c.ref_moderation_status ?? "not checked"}.`;
  });
  if (run.cost && run.cost.ref_mod_retry_count > 0) lines.push(`${plural(run.cost.ref_mod_retry_count, "safety redraw", "safety redraws")}.`);
  return lines.length > 0 ? lines : ["No references were recorded."];
}

function attempts(run: RunDetail): string[] {
  const lines = run.scenes.flatMap((s, i) => {
    const outcome = s.shipped_attempt == null ? "nothing shipped yet" : `shipped attempt ${s.shipped_attempt + 1}`;
    return [
      `Page ${i + 1}: ${plural(s.attempts.length, "attempt", "attempts")}, ${outcome}.`,
      ...s.attempts.map((attempt, index) => {
        const verdict = attempt.passed
          ? "passed"
          : attempt.vlm_verdict == null && attempt.failure_reasons.length === 0 && !attempt.scene_contradictions?.length
            ? "not checked"
            : "failed";
        const reasons = [
          ...attempt.failure_reasons.map(sceneFailureLabel),
          ...(attempt.scene_contradictions ?? []),
        ].join(", ");
        return `Page ${i + 1}, attempt ${index + 1}: ${verdict}${reasons ? ` (${reasons})` : ""}.`;
      }),
    ];
  });
  return lines.length > 0 ? lines : ["No pages were drawn."];
}

export function summarizeNodes(run: RunDetail): Record<string, NodeSummary> {
  const objects = run.state?.objects?.map((o) => o.name) ?? [];
  const places = run.state?.locations?.map((l) => l.name) ?? [];
  const shipped = run.scenes.filter((s) => s.shipped_attempt != null).length;
  return {
    input_gate: { lines: inputGate(run), section: SAFETY },
    analyze: {
      lines: [
        `Characters: ${run.characters.map((c) => c.name).join(", ") || "none"}.`,
        `Objects: ${objects.join(", ") || "none"}.`,
        `Places: ${places.join(", ") || "none"}.`,
      ],
      section: STORY,
    },
    segment: {
      lines: run.scenes.length > 0 ? run.scenes.map((s, i) => `Page ${i + 1}: ${s.visual_direction ?? s.text_excerpt}`) : ["No pages were made."],
      section: PAGES,
    },
    char_bible: { lines: references(run), section: CHARACTERS },
    char_ref_mod: { lines: references(run), section: CHARACTERS },
    reveal: {
      lines: [
        "Waited for the child to confirm the characters.",
        `Try-again taps: ${run.cost?.ref_retry_count ?? 0}.`,
      ],
      section: CHARACTERS,
    },
    generate_scene: { lines: attempts(run), section: PAGES },
    consistency_check: { lines: attempts(run), section: PAGES },
    regenerate: { lines: attempts(run), section: PAGES },
    output_mod: {
      lines: run.scenes.length > 0 ? run.scenes.map((s, i) => `Page ${i + 1}: safety ${s.moderation_status ?? "not checked"}.`) : ["No pages were checked."],
      section: SAFETY,
    },
    compose: { lines: [`${shipped} of ${run.scenes.length} pages shipped.`], section: PAGES },
  };
}
