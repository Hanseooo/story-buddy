"use server";

import { createSupabaseServerClient } from "@/utils/supabase/server";
import { User } from "@supabase/supabase-js";

export type SubmissionPayload = {
  pairId: string;
  failureReasons: string[];
  sameCharacter: boolean;
  anatomyIntact: boolean;
  textFree: boolean;
};

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

export function validateSubmissionPayload(payload: SubmissionPayload) {
  const { sameCharacter, failureReasons, anatomyIntact, textFree } = payload;
  if (sameCharacter && failureReasons.length > 0) {
    return { error: "Invalid state: same_character is true but failure reasons provided" };
  }
  if (!sameCharacter && failureReasons.length === 0) {
    return { error: "Invalid state: same_character is false but no failure reasons provided" };
  }
  if (typeof anatomyIntact !== "boolean" || typeof textFree !== "boolean") {
    return { error: "Invalid state: anatomy_intact and text_free must be explicitly provided" };
  }
  return { error: null };
}
