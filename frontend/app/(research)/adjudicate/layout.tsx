import { createSupabaseServerClient } from "@/utils/supabase/server";

export default async function AdjudicateLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    throw new Error("Unauthorized");
  }

  const { data: profile } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();

  if (profile?.role !== "researcher" || !profile?.is_adjudicator) {
    throw new Error("Unauthorized");
  }

  return (
    <div className="min-h-[100dvh] bg-background text-foreground flex flex-col selection:bg-primary/20">
      {children}
    </div>
  );
}
