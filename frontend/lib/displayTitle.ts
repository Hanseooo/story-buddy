// spec docs/specs/story-titles.md §5: nonblank stored title, otherwise the existing
// first-line/60-character excerpt, otherwise "Untitled". One function keeps every
// surface's fallback label consistent; the fallback is presentation only.
export function displayTitle(
  title: string | null | undefined,
  inputText: string | null | undefined
): string {
  if (title && title.trim() !== "") return title;
  return (inputText ?? "").split("\n")[0].slice(0, 60) || "Untitled";
}
