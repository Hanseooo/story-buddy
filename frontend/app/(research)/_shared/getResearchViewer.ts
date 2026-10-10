import { cache } from "react";
import { createSupabaseServerClient } from "@/utils/supabase/server";
import type { ResearchViewer } from "./viewer";

// cache(): the metrics layout and its page both ask in one request; one profile read serves both.
export const getResearchViewer = cache(async (): Promise<ResearchViewer | null> => {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return null;

  const { data: profile } = await supabase
    .from("profiles")
    .select("role, is_adjudicator, display_name")
    .eq("id", user.id)
    .single();

  return {
    id: user.id,
    role: profile?.role ?? null,
    isAdjudicator: profile?.is_adjudicator === true,
    displayName: profile?.display_name ?? null,
  };
});
