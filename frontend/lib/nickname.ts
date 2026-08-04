// Spec §5 — four-step pipeline. Must stay in sync with backend/app/nickname.py.

export function normalizeNickname(raw: string): string {
  // Step 1: NFKD + strip combining marks (\p{M} = Unicode Mark category)
  const nfkd = raw.normalize("NFKD").replace(/\p{M}/gu, "");
  // Step 2: lowercase, trim outer whitespace, collapse whitespace runs to a single hyphen
  const lowered = nfkd.toLowerCase().trim();
  const hyphened = lowered.replace(/\s+/g, "-");
  // Step 3: collapse repeated hyphens, strip leading/trailing hyphens
  const collapsed = hyphened.replace(/-{2,}/g, "-").replace(/^-+|-+$/g, "");
  // Step 4: reject if any character outside [a-z0-9-] survives, or length is out of range
  if (!collapsed || /[^a-z0-9-]/u.test(collapsed)) {
    throw new Error(`nickname "${raw}" contains characters that cannot be normalized`);
  }
  if (collapsed.length < 2) {
    throw new Error(`nickname "${raw}" normalizes to under 2 characters`);
  }
  if (collapsed.length > 32) {
    throw new Error(`nickname "${raw}" normalizes to over 32 characters`);
  }
  return collapsed;
}

export function composeStudentEmail(nickname: string, classroomCode: string): string {
  return `${normalizeNickname(nickname)}@${classroomCode}.students.storybuddy.invalid`;
}
