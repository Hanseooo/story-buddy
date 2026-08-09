"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { AVATAR_IDS } from "@/lib/avatars";
import { Avatar } from "@/components/Avatar";
import { motion } from "framer-motion";

export default function SettingsPage() {
  const { profileId } = useParams<{ profileId: string }>();

  // Avatar state
  const [avatarId, setAvatarId] = useState<string | null>(null);
  const [avatarMessage, setAvatarMessage] = useState("");

  // Password state
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  // Fetch current avatar on mount
  useEffect(() => {
    if (!profileId) return;
    supabase
      .from("profiles")
      .select("avatar_id")
      .eq("id", profileId)
      .single()
      .then(({ data }) => {
        if (data) setAvatarId(data.avatar_id ?? null);
      });
  }, [profileId]);

  async function handleAvatarSelect(newId: string | null) {
    const previous = avatarId;
    setAvatarId(newId); // optimistic
    setAvatarMessage("");

    const {
      data: { session },
    } = await supabase.auth.getSession();

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/me/avatar`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session?.access_token}`,
      },
      body: JSON.stringify({ avatar_id: newId }),
    });

    if (!res.ok) {
      setAvatarId(previous); // revert
      setAvatarMessage("Couldn't save your avatar. Try again.");
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setMessage("Passwords don't match.");
      return;
    }
    setLoading(true);
    const { error } = await supabase.auth.updateUser({ password });
    setMessage(
      error
        ? error.message
        : "Password saved. If you forget it, ask your teacher."
    );
    setLoading(false);
  };

  return (
    <main className="font-kid p-6 max-w-3xl mx-auto pb-24">
      <h1 className="font-display text-4xl font-extrabold text-foreground tracking-tight mb-8">
        Settings
      </h1>

      <div className="space-y-6">
        {/* ── Avatar picker Bento ─────────────────────────────────────────── */}
        <div className="bg-surface border-2 border-primary/10 rounded-[28px] p-6 sm:p-10 shadow-[0_8px_24px_rgba(49,85,217,0.08)]">
          <h2 className="font-display text-2xl font-extrabold text-primary mb-4">
            Your Avatar
          </h2>

          {avatarMessage && (
            <div
              role="status"
              className="mb-4 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-sm font-bold text-destructive"
            >
              {avatarMessage}
            </div>
          )}

          <fieldset>
            <legend className="sr-only">Choose your avatar</legend>
            <motion.div 
              className="grid grid-cols-4 sm:grid-cols-6 gap-3 sm:gap-4 mb-6"
              initial="hidden"
              animate="show"
              variants={{
                hidden: { opacity: 0 },
                show: {
                  opacity: 1,
                  transition: { staggerChildren: 0.03 }
                }
              }}
            >
              {AVATAR_IDS.map((id, i) => (
                <motion.label 
                  key={id} 
                  className="cursor-pointer relative flex justify-center"
                  variants={{
                    hidden: { opacity: 0, scale: 0.8 },
                    show: { opacity: 1, scale: 1 }
                  }}
                  whileHover={{ scale: 1.1, y: -2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <input
                    type="radio"
                    name="avatar"
                    value={id}
                    checked={avatarId === id}
                    onChange={() => handleAvatarSelect(id)}
                    className="sr-only"
                    aria-label={`Avatar ${i + 1} of ${AVATAR_IDS.length}`}
                  />
                  <div
                    className={`rounded-full p-1.5 transition-all ${
                      avatarId === id
                        ? "bg-secondary/20 ring-4 ring-secondary ring-offset-2 ring-offset-surface shadow-[0_0_15px_rgba(255,168,0,0.5)]"
                        : "hover:bg-primary/5"
                    }`}
                  >
                    <Avatar avatarId={id} displayNickname="?" size={56} />
                  </div>
                </motion.label>
              ))}
            </motion.div>
          </fieldset>

          <button
            type="button"
            onClick={() => handleAvatarSelect(null)}
            className="w-full sm:w-auto px-6 py-3 rounded-xl border-2 border-primary/10 text-sm font-bold text-foreground/70 hover:bg-primary/5 hover:text-primary hover:border-primary/30 transition-all active:scale-[0.98]"
          >
            Use my letter instead
          </button>
        </div>

        {/* ── Password Bento ─────────────────────────────────────────── */}
        <div className="bg-surface border-2 border-primary/10 rounded-[28px] p-6 sm:p-10 shadow-[0_8px_24px_rgba(49,85,217,0.08)]">
          <h2 className="font-display text-2xl font-extrabold text-primary mb-4">
            Change Password
          </h2>

          {message && (
            <div
              role="status"
              className={`mb-6 p-4 rounded-xl border text-sm font-bold ${
                message.includes("match") || message.includes("error")
                  ? "bg-destructive/10 border-destructive/20 text-destructive"
                  : "bg-success/10 border-success/20 text-success"
              }`}
            >
              {message}
            </div>
          )}

          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full">
              <label htmlFor="new-password" className="block text-sm font-bold text-foreground/80 mb-2">
                New password
              </label>
              <div className="relative">
                <input
                  id="new-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full min-h-[48px] px-4 py-3 rounded-xl border-2 border-primary/10 bg-background text-foreground focus:outline-none focus:ring-[3px] focus:ring-secondary focus:border-transparent transition-all pr-16"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-sm font-bold text-primary px-3 py-1.5 rounded-lg hover:bg-primary/10 transition-colors"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <div className="flex-1 w-full">
              <label htmlFor="confirm-password" className="block text-sm font-bold text-foreground/80 mb-2">
                Confirm password
              </label>
              <input
                id="confirm-password"
                type={showPassword ? "text" : "password"}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                className="w-full min-h-[48px] px-4 py-3 rounded-xl border-2 border-primary/10 bg-background text-foreground focus:outline-none focus:ring-[3px] focus:ring-secondary focus:border-transparent transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full sm:w-auto min-h-[48px] px-8 rounded-xl bg-primary text-on-primary font-extrabold shadow-[0_6px_18px_rgba(49,85,217,0.1)] transition-all hover:-translate-y-[2px] hover:shadow-[0_10px_28px_rgba(49,85,217,0.12)] active:translate-y-0 active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
            >
              {loading ? "Saving..." : "Save password"}
            </button>
          </form>
        </div>

        {/* ── Logout Bento ────────────────────────────────────────────────── */}
        <div className="bg-surface border-2 border-destructive/10 rounded-[28px] p-6 sm:p-10 shadow-[0_8px_24px_rgba(239,68,68,0.05)]">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-center sm:text-left">
              <h2 className="font-display text-xl font-extrabold text-destructive">
                Log Out
              </h2>
              <p className="text-sm font-medium text-foreground/60 mt-1">
                See you next time!
              </p>
            </div>
            <form action="/auth/signout" method="post" className="w-full sm:w-auto">
              <button
                type="submit"
                className="w-full sm:w-auto min-h-[48px] px-8 rounded-xl bg-destructive/10 text-destructive font-extrabold hover:bg-destructive/20 hover:scale-105 active:scale-[0.98] transition-all"
              >
                Log out
              </button>
            </form>
          </div>
        </div>
      </div>
    </main>
  );
}
