import { cache } from "react";
import { createSupabaseServerClient } from "./server";

export const getStudentProfile = cache(async (profileId: string) => {
  const client = await createSupabaseServerClient();
  const result = await client.from("profiles")
    .select("id, display_nickname, role, classroom_id, avatar_id, is_adjudicator, removed_at, password_reset_version, password_completed_version, introduction_dismissed_at")
    .eq("id", profileId).single();
  if (result.error) throw new Error("Couldn't load your account. Try again.");
  return result.data;
});
