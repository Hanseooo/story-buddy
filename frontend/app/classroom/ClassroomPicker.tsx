"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { type Classroom } from "@/utils/supabase/teacher";
import { motion } from "motion/react";

export default function ClassroomPicker({
  classrooms,
}: {
  classrooms: Classroom[];
}) {
  const router = useRouter();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const resp = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/classrooms`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ name: name.trim() }),
      });
      if (!resp.ok) {
        setError("Could not create classroom. Try again.");
        setIsSubmitting(false);
        return;
      }
      const cls = await resp.json();
      router.push(`/classroom/${cls.id}`);
    } catch {
      setError("An unexpected error occurred.");
      setIsSubmitting(false);
    }
  }

  if (classrooms.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] p-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="max-w-lg w-full bg-surface border-4 border-dashed border-primary/20 rounded-[32px] p-8 sm:p-12 text-center shadow-[0_10px_28px_rgba(49,85,217,0.08)]"
        >
          <div className="w-24 h-24 bg-primary/10 text-primary rounded-full flex items-center justify-center mx-auto mb-6">
            <span className="text-5xl">🏫</span>
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-primary mb-3">
            Welcome to your desk!
          </h1>
          <p className="text-base text-foreground/70 mb-10 max-w-[40ch] mx-auto">
            Create your first classroom to invite your students and start making magic.
          </p>
          <form onSubmit={handleCreate} className="space-y-4 text-left">
            <div>
              <label htmlFor="className" className="block text-sm font-bold text-foreground/80 mb-2">Classroom Name</label>
              <input
                id="className"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Grade 3 – Alon"
                required
                className="w-full bg-background border-2 border-primary/10 rounded-2xl px-5 py-4 text-base focus:outline-none focus:ring-[3px] focus:ring-secondary focus:border-transparent transition-all"
              />
            </div>
            {error && (
              <p className="text-destructive text-sm font-bold" role="alert">
                {error}
              </p>
            )}
            <motion.button
              whileTap={{ y: 4, boxShadow: "0 0px 0 var(--color-primary-deep)" }}
              type="submit"
              disabled={!name.trim() || isSubmitting}
              className="w-full min-h-[64px] mt-4 bg-primary text-on-primary rounded-2xl font-extrabold text-lg shadow-[0_4px_0_var(--color-primary-deep)] transition-colors disabled:opacity-50 disabled:shadow-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px] focus-visible:ring-offset-surface"
            >
              {isSubmitting ? "Creating..." : "Create classroom"}
            </motion.button>
          </form>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="p-6 sm:p-10 max-w-7xl mx-auto w-full min-h-[calc(100vh-80px)]">
      <div className="mb-10">
        <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-foreground tracking-tight">
          Teacher&apos;s Desk
        </h1>
        <p className="text-foreground/60 text-lg mt-2 font-medium">Manage your classrooms and students.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-[minmax(200px,auto)] pb-20">
        {classrooms.map((c, i) => {
          // Highlight the first classroom if there are multiple, making it span larger
          const isFeatured = i === 0 && classrooms.length > 1;
          return (
            <motion.button
              key={c.id}
              onClick={() => router.push(`/classroom/${c.id}`)}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              whileHover={{ y: -6, scale: 1.02, zIndex: 10 }}
              whileFocus={{ y: -6, scale: 1.02, zIndex: 10 }}
              className={`text-left bg-surface border-2 border-primary/10 rounded-[28px] p-6 shadow-[0_8px_24px_rgba(49,85,217,0.08)] hover:shadow-[0_22px_60px_rgba(49,85,217,0.16)] transition-shadow focus:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px] focus-visible:ring-offset-background flex flex-col justify-between group ${
                isFeatured ? "md:col-span-2 md:row-span-2 sm:p-10" : ""
              }`}
            >
              <div>
                <div className={`bg-secondary/20 rounded-2xl mb-5 flex items-center justify-center text-secondary ${isFeatured ? "w-16 h-16" : "w-12 h-12"}`}>
                  <svg width={isFeatured ? "32" : "24"} height={isFeatured ? "32" : "24"} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
                  </svg>
                </div>
                <p className={`font-display font-extrabold text-foreground mb-2 ${isFeatured ? "text-4xl" : "text-2xl"}`}>
                  {c.name}
                </p>
                <div className="inline-flex items-center gap-2 bg-background px-3 py-1.5 rounded-lg border border-primary/10">
                  <span className="text-xs font-bold text-foreground/50 uppercase tracking-wider">Code</span>
                  <span className="text-sm font-mono font-bold text-primary">{c.code}</span>
                </div>
              </div>
              <div className="mt-8 flex items-center justify-between text-primary font-bold opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="text-lg">Open roster</span>
                <span className="text-2xl leading-none">→</span>
              </div>
            </motion.button>
          );
        })}

        {/* New Classroom Bento Tile */}
        {!showCreateForm ? (
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: classrooms.length * 0.05 }}
            onClick={() => setShowCreateForm(true)}
            whileHover={{ y: -4, scale: 1.02 }}
            className="text-center bg-primary/5 border-4 border-dashed border-primary/15 rounded-[28px] p-6 hover:bg-primary/10 hover:border-primary/30 transition-colors focus:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px] focus-visible:ring-offset-background flex flex-col items-center justify-center min-h-[200px] group"
          >
            <div className="w-14 h-14 bg-primary text-on-primary rounded-full mb-4 flex items-center justify-center shadow-[0_4px_0_var(--color-primary-deep)] group-hover:shadow-none group-hover:translate-y-1 transition-all">
              <span className="text-3xl font-extrabold leading-none pb-1">+</span>
            </div>
            <p className="font-extrabold text-lg text-primary">New classroom</p>
          </motion.button>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface border-2 border-primary/20 rounded-[28px] p-6 sm:p-8 shadow-[0_22px_60px_rgba(49,85,217,0.16)] col-span-1 md:col-span-2 lg:col-span-1 flex flex-col justify-center min-h-[200px]"
          >
            <form onSubmit={handleCreate} className="space-y-4">
              <p className="font-extrabold text-xl text-primary mb-2">Create classroom</p>
              <input
                autoFocus
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Classroom name"
                className="w-full bg-background border-2 border-primary/10 rounded-xl px-4 py-3 text-base font-medium focus:outline-none focus:ring-[3px] focus:ring-secondary focus:border-transparent transition-all"
              />
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={!name.trim() || isSubmitting}
                  className="flex-1 min-h-[48px] bg-primary text-on-primary rounded-xl font-bold text-sm disabled:opacity-50 shadow-[0_4px_0_var(--color-primary-deep)] active:translate-y-[4px] active:shadow-none transition-all focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="flex-1 min-h-[48px] rounded-xl border-2 border-muted text-sm font-bold hover:bg-muted transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
                >
                  Cancel
                </button>
              </div>
              {error && (
                <p className="text-destructive text-sm font-bold" role="alert">
                  {error}
                </p>
              )}
            </form>
          </motion.div>
        )}
      </div>
    </div>
  );
}
