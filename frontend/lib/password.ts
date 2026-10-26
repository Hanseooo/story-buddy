import type { SupabaseClient } from "@supabase/supabase-js";

export function passwordLengthError(password: string): string | null {
  if (Array.from(password).length < 8) return "Use at least 8 characters. Spaces are okay.";
  if (new TextEncoder().encode(password).length > 72) return "Your password is too long. Use fewer characters, including fewer emoji.";
  return null;
}

export async function changePassword(client: SupabaseClient, current: string, password: string, confirmation: string) {
  const { data: { session } } = await client.auth.getSession();
  if (!session) return { error: { code: "session_not_found", status: 401 }, next_path: undefined };
  const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/me/password`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.access_token}` },
    body: JSON.stringify({ current_password: current, password, confirmation }),
  });
  const data = await response.json();
  return {
    error: response.ok ? null : { code: typeof data.detail === "string" ? data.detail : "password_unavailable", status: response.status },
    next_path: typeof data.next_path === "string" ? data.next_path : undefined,
  };
}
