import { createSupabaseServerClient } from "@/utils/supabase/server";
import { redirect } from "next/navigation";

export default async function AdjudicatePage() {
  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");
  
  // Verify adjudicator flag
  const { data: profile } = await supabase
    .from("profiles")
    .select("role, is_adjudicator")
    .eq("id", user.id)
    .single();
    
  if (profile?.role !== "researcher" || !profile?.is_adjudicator) {
    redirect("/login");
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center pt-8">
      <div className="w-full max-w-6xl px-4 flex flex-col items-center">
        <h1 className="text-2xl font-bold mb-6 text-purple-900">Adjudicate Conflicts</h1>
        
        <div className="p-8 bg-white rounded-lg shadow text-center w-full">
          <p className="text-gray-500">Conflict resolution queue and side-by-side annotation view to be implemented.</p>
        </div>
      </div>
    </div>
  );
}
