"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { type Classroom } from "@/utils/supabase/teacher";
import { motion, useReducedMotion } from "framer-motion";
import { Buildings, ChalkboardTeacher, Plus, Flask, ArrowRight } from "@phosphor-icons/react";

export default function ClassroomPicker({
  classrooms,
}: {
  classrooms: Classroom[];
}) {
  const router = useRouter();
  const shouldReduceMotion = useReducedMotion();
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
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="max-w-lg w-full bg-surface border-2 border-dashed border-primary/20 rounded-[32px] p-8 sm:p-12 text-center shadow-[0_10px_28px_rgba(49,85,217,0.08)]"
        >
          <div className="w-20 h-20 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mx-auto mb-6">
            <Buildings weight="duotone" className="w-10 h-10" aria-hidden="true" />
          </div>
          <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-primary mb-3">
            Welcome to your desk!
          </h1>
          <p className="font-kid text-base text-foreground/75 mb-8 max-w-[40ch] mx-auto">
            Create your first classroom to invite your students and start creating stories.
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
                className="w-full bg-background border-2 border-primary/15 rounded-xl px-4 py-3.5 text-base focus:outline-none focus:ring-[3px] focus:ring-secondary transition-all"
              />
            </div>
            {error && (
              <p className="text-destructive text-sm font-bold" role="alert">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={!name.trim() || isSubmitting}
              className="w-full min-h-[52px] mt-4 bg-primary text-on-primary rounded-xl font-extrabold text-base shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed disabled:transform-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
            >
              {isSubmitting ? "Creating..." : "Create Classroom"}
            </button>
          </form>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="p-6 sm:p-10 max-w-7xl mx-auto w-full min-h-[calc(100vh-80px)]">
      <div className="mb-10">
        <h1 className="font-display text-4xl sm:text-5xl font-extrabold text-primary tracking-tight">
          Teacher&apos;s Desk
        </h1>
        <p className="font-kid text-foreground/70 text-lg mt-2 font-medium">Manage your classrooms, student rosters, and stories.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-[minmax(220px,auto)] pb-20">
        {classrooms.map((c, i) => (
          <motion.button
            key={c.id}
            onClick={() => router.push(`/classroom/${c.id}`)}
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: shouldReduceMotion ? 0 : i * 0.05, duration: 0.4 }}
            whileHover={{ y: -4, scale: 1.01 }}
            className="text-left bg-surface border border-primary/15 rounded-[24px] p-6 sm:p-7 shadow-[0_8px_24px_rgba(49,85,217,0.08)] hover:shadow-[0_16px_42px_rgba(49,85,217,0.14)] hover:border-primary/30 transition-all focus:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px] focus-visible:ring-offset-background flex flex-col justify-between group cursor-pointer"
          >
            <div>
              <div className="bg-secondary/30 rounded-2xl mb-5 flex items-center justify-center text-foreground w-12 h-12">
                <ChalkboardTeacher size={24} weight="duotone" />
              </div>
              <p className="font-display font-extrabold text-foreground mb-2 text-2xl tracking-tight">
                {c.name}
              </p>
              <div className="inline-flex items-center gap-2 bg-background px-3 py-1.5 rounded-lg border border-primary/10">
                <span className="text-xs font-bold text-foreground/50 uppercase tracking-wider">Class Code</span>
                <span className="text-sm font-mono font-bold text-primary">{c.code}</span>
              </div>
            </div>
            <div className="mt-8 flex items-center justify-between text-primary font-bold opacity-70 group-hover:opacity-100 transition-opacity">
              <span className="font-kid text-base">Open roster</span>
              <ArrowRight size={20} weight="bold" className="transition-transform group-hover:translate-x-1" />
            </div>
          </motion.button>
        ))}

        {/* New Classroom Tile */}
        {!showCreateForm ? (
          <motion.button
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: shouldReduceMotion ? 0 : classrooms.length * 0.05, duration: 0.4 }}
            onClick={() => setShowCreateForm(true)}
            whileHover={{ y: -4, scale: 1.01 }}
            className="text-center bg-surface border-2 border-dashed border-primary/20 rounded-[24px] p-6 hover:bg-primary/5 hover:border-primary/35 transition-all focus:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px] focus-visible:ring-offset-background flex flex-col items-center justify-center min-h-[220px] group cursor-pointer"
          >
            <div className="size-14 bg-primary text-on-primary rounded-2xl mb-4 flex items-center justify-center shadow-[0_4px_0_var(--color-primary-deep)] group-hover:-translate-y-0.5 transition-transform">
              <Plus size={24} weight="bold" />
            </div>
            <p className="font-display font-extrabold text-lg text-primary">New classroom</p>
          </motion.button>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-surface border-2 border-primary/25 rounded-[24px] p-6 sm:p-7 shadow-[0_16px_42px_rgba(49,85,217,0.12)] col-span-1 flex flex-col justify-center min-h-[220px]"
          >
            <form onSubmit={handleCreate} className="space-y-4">
              <p className="font-display font-extrabold text-xl text-primary mb-2">Create classroom</p>
              <input
                autoFocus
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Classroom name"
                className="w-full bg-background border-2 border-primary/15 rounded-xl px-4 py-3 text-base font-medium focus:outline-none focus:ring-[3px] focus:ring-secondary focus:border-transparent transition-all"
              />
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={!name.trim() || isSubmitting}
                  className="flex-1 min-h-[44px] bg-primary text-on-primary rounded-xl font-bold text-sm disabled:opacity-50 shadow-[0_3px_0_var(--color-primary-deep)] active:translate-y-[2px] active:shadow-none transition-all focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
                >
                  Create
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="flex-1 min-h-[44px] rounded-xl border border-muted text-sm font-bold hover:bg-muted transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
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

        {/* Research & Methodology Tile */}
        <motion.button
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: shouldReduceMotion ? 0 : (classrooms.length + 1) * 0.05, duration: 0.4 }}
          onClick={() => router.push('/research')}
          whileHover={{ y: -4, scale: 1.01 }}
          className="text-left bg-primary text-on-primary rounded-[24px] p-6 sm:p-7 shadow-[0_10px_28px_rgba(49,85,217,0.14)] hover:shadow-[0_22px_60px_rgba(49,85,217,0.22)] transition-all cursor-pointer focus:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[3px] focus-visible:ring-offset-background flex flex-col justify-between group min-h-[220px]"
        >
          <div>
            <div className="bg-surface/20 rounded-2xl mb-5 flex items-center justify-center text-on-primary size-12">
              <Flask size={24} weight="duotone" />
            </div>
            <p className="font-display font-extrabold text-2xl mb-2 leading-tight">
              Capstone Research
            </p>
            <p className="text-[#DFE5FF] font-kid text-sm leading-relaxed max-w-[28ch]">
              Explore our transparent open-weight pipeline, methodology, and live metrics.
            </p>
          </div>
          <div className="mt-6 flex items-center justify-between font-bold text-on-primary opacity-80 group-hover:opacity-100 transition-opacity w-full">
            <span className="font-kid text-sm">Read methodology</span>
            <ArrowRight size={18} weight="bold" className="transition-transform group-hover:translate-x-1" />
          </div>
        </motion.button>
      </div>
    </div>
  );
}
