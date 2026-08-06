export function safe(path: string): string | null {
  if (!path.startsWith("/") || path.startsWith("//")) return null;
  return path;
}
