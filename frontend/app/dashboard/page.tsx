"use client";

// ponytail: S4 stated placeholder; teacher-dashboard is the successor (spec §6.3)
import { supabase } from "@/lib/supabaseClient";

export default function Dashboard() {
  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <div className="font-sans min-h-screen bg-background text-foreground p-6 sm:p-10">
      <div className="max-w-4xl mx-auto">
        <header className="flex items-center justify-between pb-6 border-b border-primary/15 mb-8">
          <div>
            <h1 className="font-display text-3xl font-extrabold text-primary">
              Dashboard
            </h1>
            <p className="text-sm text-foreground/70 mt-1">
              Teacher &amp; Classroom Management
            </p>
          </div>
          <button
            onClick={handleSignOut}
            className="min-h-11 px-4 py-2 rounded-xl border border-primary/20 bg-surface font-bold text-foreground hover:bg-muted transition-colors"
          >
            Log out
          </button>
        </header>

        <main>
          <div className="bg-surface border border-primary/20 rounded-2xl p-8 shadow-[0_6px_18px_rgba(49,85,217,0.10)]">
            <h2 className="font-display text-xl font-bold text-primary mb-2">
              Classroom Overview
            </h2>
            <p className="text-foreground/70">
              Classroom tools are not built yet. Classroom setup and student
              accounts will be available in a future update.
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
