"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { AVATAR_IDS } from "@/lib/avatars";
import { Avatar } from "@/components/Avatar";

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
    <main className="font-kid p-6 max-w-md mx-auto">
      {/* ── Avatar picker ─────────────────────────────────────────── */}
      <h1 className="font-display text-2xl font-extrabold text-primary mb-4">
        Your Avatar
      </h1>

      {avatarMessage && (
        <div
          role="status"
          className="mb-4 p-3 rounded-xl bg-surface border border-primary/20 text-sm font-medium text-destructive"
        >
          {avatarMessage}
        </div>
      )}

      <fieldset>
        <legend className="sr-only">Choose your avatar</legend>
        <div className="grid grid-cols-6 gap-2 mb-3">
          {AVATAR_IDS.map((id, i) => (
            <label key={id} className="cursor-pointer">
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
                className={`rounded-full p-0.5 transition-all ${
                  avatarId === id
                    ? "ring-2 ring-offset-2 ring-primary"
                    : "ring-0"
                }`}
              >
                <Avatar avatarId={id} displayNickname="?" size={44} />
              </div>
            </label>
          ))}
        </div>
      </fieldset>

      <button
        type="button"
        onClick={() => handleAvatarSelect(null)}
        className="text-sm text-foreground/50 hover:text-primary transition-colors mb-8 underline underline-offset-2"
      >
        Use my letter instead
      </button>

      {/* ── Password form ─────────────────────────────────────────── */}
      <h2 className="font-display text-xl font-extrabold text-primary mb-4 mt-2">
        Change Password
      </h2>

      {message && (
        <div
          role="status"
          className="mb-4 p-3 rounded-xl bg-surface border border-primary/20 text-sm font-medium"
        >
          {message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div>
          <label htmlFor="new-password" className="block font-semibold mb-1">
            New password
          </label>
          <div className="relative">
            <input
              id="new-password"
              autoFocus
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full min-h-11 px-3.5 py-2.5 rounded-xl border border-primary/20 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-secondary pr-16"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-bold text-primary px-2"
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="confirm-password" className="block font-semibold mb-1">
            Confirm password
          </label>
          <input
            id="confirm-password"
            type={showPassword ? "text" : "password"}
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            className="w-full min-h-11 px-3.5 py-2.5 rounded-xl border border-primary/20 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-secondary"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full min-h-11 rounded-xl bg-primary text-on-primary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] disabled:opacity-50"
        >
          {loading ? "Saving..." : "Save password"}
        </button>
      </form>

      {/* ── Logout ────────────────────────────────────────────────── */}
      <div className="mt-8 border-t border-border pt-6">
        <form action="/auth/signout" method="post">
          <button
            type="submit"
            className="min-h-11 w-full rounded-xl border border-destructive/40 px-4 py-2 text-sm text-destructive hover:bg-destructive/5 transition-colors"
          >
            Log out
          </button>
        </form>
      </div>
    </main>
  );
}
