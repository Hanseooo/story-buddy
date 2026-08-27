"use server";

import { createSupabaseServerClient } from "@/utils/supabase/server";
import { User } from "@supabase/supabase-js";

export type { SubmissionPayload } from "./validation";

type ResearchAuthMode = boolean | "any";

export async function verifyResearchAuth(mode: ResearchAuthMode = false): Promise<{ error: string | null, user: User | null, isAdjudicator: boolean }> {
  const supabase = await createSupabaseServerClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();

  if (authError || !user) {
    return { error: "Unauthorized", user: null, isAdjudicator: false };
  }

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  if (profileError || profile?.role !== "researcher") {
    return { error: "Unauthorized", user: null, isAdjudicator: false };
  }

  const isAdjudicator = Boolean(profile?.is_adjudicator);

  if (mode === true && !isAdjudicator) {
    return { error: "Unauthorized", user: null, isAdjudicator: false };
  }
  
  if (mode === false && isAdjudicator) {
    return { error: "Unauthorized", user: null, isAdjudicator: false };
  }

  return { error: null, user, isAdjudicator };
}
