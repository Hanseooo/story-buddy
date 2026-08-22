"use server";

import { createSupabaseServerClient } from "@/utils/supabase/server";
import { User } from "@supabase/supabase-js";

export type { SubmissionPayload } from "./validation";

export async function verifyResearchAuth(requireAdjudicator: boolean = false): Promise<{ error: string | null, user: User | null }> {
  const supabase = await createSupabaseServerClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();

  if (authError || !user) {
    return { error: "Unauthorized", user: null };
  }

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  if (profileError || profile?.role !== "researcher") {
    return { error: "Unauthorized", user: null };
  }

  if (requireAdjudicator && !profile?.is_adjudicator) {
    return { error: "Unauthorized", user: null };
  }
  
  if (!requireAdjudicator && profile?.is_adjudicator) {
    return { error: "Unauthorized", user: null };
  }

  return { error: null, user };
}
