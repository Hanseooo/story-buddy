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
    <div className="min-h-screen bg-gray-50 flex flex-col items-center pt-8">
      {children}
    </div>
  );
}
