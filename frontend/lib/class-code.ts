// Class codes are six letters or digits. The generator (backend/app/classrooms.py) leaves out
// I, O, 0 and 1 so handwritten codes stay readable, but input takes any letter or digit as
// typed: the screen font tells them apart, and a wrong code fails at sign-in like any typo.
export const CODE_LENGTH = 6;

/** One typed or pasted character → lowercase, or null if it isn't a letter or digit. */
export function toCodeChar(raw: string): string | null {
  const c = raw.toLowerCase();
  return /^[a-z0-9]$/.test(c) ? c : null;
}

/** A whole code (e.g. from a /join/[code] link) → lowercase code, or null if malformed. */
export function normalizeCode(raw: string): string | null {
  const chars = [...raw].map(toCodeChar);
  if (chars.length !== CODE_LENGTH || chars.some((c) => c === null)) return null;
  return chars.join("");
}
