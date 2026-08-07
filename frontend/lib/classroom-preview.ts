import { normalizeNickname } from "./nickname";

export type Preset = "first" | "first-last-initial" | "full";

export type PreviewRow = {
  line: string;
  displayNickname: string;
  nickname: string;
  editable: boolean;
  reason?: string;
  suggestion?: string;
};

function reduceByPreset(fullName: string, preset: Preset): string {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (preset === "first") return parts[0];
  if (preset === "full") return parts.join(" ");
  // first-last-initial: parts[1] is the first token of the last name (e.g. "Dela" in "Juan Dela Cruz")
  const first = parts[0];
  if (parts.length < 2) return first;
  return `${first} ${parts[1][0]}.`;
}

// Strip trailing period before normalizing — "Maria S." → "Maria S" → "maria-s"
function normalize(display: string): string {
  return normalizeNickname(display.replace(/\s*\.$/, ""));
}

export function computePreview(
  lines: string[],
  existingNicknames: Set<string>,
  preset: Preset
): PreviewRow[] {
  // Pass 1: compute display0 + nick0 for each non-empty line
  const pass1 = lines
    .map((l) => l.trim())
    .filter(Boolean)
    .map((trimmed) => {
      const display0 = reduceByPreset(trimmed, preset);
      let nick0: string | null = null;
      let error: string | undefined;
      try {
        nick0 = normalize(display0);
      } catch (err) {
        error = err instanceof Error ? err.message : "invalid name";
      }
      return { trimmed, display0, nick0, error };
    });

  // Pre-count nick0 occurrences for within-paste future-conflict detection
  const nick0Counts = new Map<string, number>();
  for (const { nick0 } of pass1) {
    if (nick0 !== null) nick0Counts.set(nick0, (nick0Counts.get(nick0) ?? 0) + 1);
  }

  const takenInPaste = new Set<string>();
  const rows: PreviewRow[] = [];

  for (const { trimmed, display0, nick0, error } of pass1) {
    // Normalization failure → level 2 immediately
    if (error !== undefined || nick0 === null) {
      rows.push({
        line: trimmed,
        displayNickname: display0,
        nickname: display0,
        editable: true,
        reason: error ?? "invalid name",
        suggestion: reduceByPreset(trimmed, "first-last-initial"),
      });
      continue;
    }

    const parts = trimmed.split(/\s+/).filter(Boolean);
    const canLevel1 = preset === "first" && parts.length > 1;

    // Definite conflict: nick0 already in roster or already claimed in this paste
    const definiteConflict = existingNicknames.has(nick0) || takenInPaste.has(nick0);
    // Future conflict: another row in this paste will also produce nick0 (not yet claimed)
    const futurePasteConflict = !definiteConflict && (nick0Counts.get(nick0) ?? 0) > 1;

    // Level 0: no conflict at all
    if (!definiteConflict && !futurePasteConflict) {
      takenInPaste.add(nick0);
      rows.push({ line: trimmed, displayNickname: display0, nickname: nick0, editable: false });
      continue;
    }

    // Conflict detected + can escalate → level 1
    if (canLevel1) {
      const display1 = reduceByPreset(trimmed, "first-last-initial");
      try {
        const nick1 = normalize(display1);
        if (!existingNicknames.has(nick1) && !takenInPaste.has(nick1)) {
          takenInPaste.add(nick1);
          rows.push({
            line: trimmed,
            displayNickname: display1,
            nickname: nick1,
            editable: false,
            reason: "escalated to include last initial",
          });
          continue;
        }
      } catch {
        // Level 1 normalization also fails → fall through
      }
    }

    // Future-paste conflict only + cannot escalate → first occurrence wins level 0
    if (futurePasteConflict) {
      takenInPaste.add(nick0);
      rows.push({ line: trimmed, displayNickname: display0, nickname: nick0, editable: false });
      continue;
    }

    // Level 2: editable
    const suggestion = preset === "first" ? reduceByPreset(trimmed, "first-last-initial") : "";
    rows.push({
      line: trimmed,
      displayNickname: display0,
      nickname: nick0,
      editable: true,
      reason: "nickname already taken",
      suggestion,
    });
  }

  return rows;
}
