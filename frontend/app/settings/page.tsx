"use client";

import { useEffect, useState } from "react";
import { createBrowserClient } from "@supabase/ssr";
import Link from "next/link";
import { ArrowLeft } from "@phosphor-icons/react";

export default function TeacherSettingsPage() {
  const [profile, setProfile] = useState<{
    display_name: string | null;
    email: string;
  } | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co",
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key"
  );

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (!user) return;
      supabase
        .from("profiles")
        .select("display_name")
        .eq("id", user.id)
        .single()
        .then(({ data }) => {
          setProfile({
            display_name: data?.display_name ?? null,
            email: user.email ?? "",
          });
          setDisplayName(data?.display_name ?? "");
        });
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSaveName(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;
      await supabase
        .from("profiles")
        .update({ display_name: displayName.trim() })
        .eq("id", user.id);
      setProfile((p) => p && { ...p, display_name: displayName.trim() });
      showToast("Name updated");
    } finally {
      setSaving(false);
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
    setPwError(null);
    if (newPassword !== confirmPassword) {
      setPwError("Passwords do not match");
      return;
    }
    if (newPassword.length < 8) {
      setPwError("Password must be at least 8 characters");
      return;
    }
    const { error } = await supabase.auth.updateUser({ password: newPassword });
    if (error) {
      setPwError(error.message);
    } else {
      setPwSuccess(true);
      setNewPassword("");
      setConfirmPassword("");
      showToast("Password changed");
    }
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  }

  if (!profile) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-foreground/40 text-sm animate-pulse">
          Loading…
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 sm:p-8 max-w-xl mx-auto">
      <Link
        href="/classroom"
        className="inline-flex items-center gap-2 text-sm font-bold text-foreground/60 hover:text-primary transition-colors mb-6"
      >
        <ArrowLeft weight="bold" className="w-4 h-4" />
        Back to Teacher&apos;s Desk
      </Link>

      <h1 className="font-display text-2xl font-extrabold text-foreground mb-8">
        Account settings
      </h1>

      {/* Display name */}
      <section className="bg-surface border border-primary/15 rounded-2xl p-6 mb-6">
        <h2 className="font-bold text-foreground mb-4">Display name</h2>
        <form onSubmit={handleSaveName} className="flex gap-3">
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="flex-1 bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            type="submit"
            disabled={saving || displayName.trim() === (profile.display_name ?? "")}
            className="min-h-[44px] px-4 py-2 bg-primary text-on-primary rounded-xl text-sm font-bold disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </form>
      </section>

      {/* Email (read-only) */}
      <section className="bg-surface border border-primary/15 rounded-2xl p-6 mb-6">
        <h2 className="font-bold text-foreground mb-1">Email</h2>
        <p className="text-sm text-foreground/60">{profile.email}</p>
      </section>

      {/* Password change */}
      <section className="bg-surface border border-primary/15 rounded-2xl p-6 mb-6">
        <h2 className="font-bold text-foreground mb-4">Change password</h2>
        <form onSubmit={handleChangePassword} className="space-y-3">
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="New password"
            autoComplete="new-password"
            className="w-full bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
            autoComplete="new-password"
            className="w-full bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          {pwError && (
            <p className="text-destructive text-sm" role="alert">
              {pwError}
            </p>
          )}
          {pwSuccess && (
            <p className="text-success text-sm">Password changed successfully.</p>
          )}
          <button
            type="submit"
            disabled={!newPassword || !confirmPassword}
            className="min-h-[44px] px-5 py-2 bg-primary text-on-primary rounded-xl text-sm font-bold disabled:opacity-50"
          >
            Change password
          </button>
        </form>
      </section>

      {/* Account deletion — named, not shipped */}
      <section className="bg-surface border border-primary/15 rounded-2xl p-6 opacity-60">
        <h2 className="font-bold text-foreground mb-1">Delete account</h2>
        <p className="text-sm text-foreground/60">
          Account deletion removes all your classrooms, students, and books.
          Contact support to request deletion.
        </p>
      </section>

      {toast && (
        <div
          role="status"
          className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-foreground text-background px-5 py-3 rounded-xl text-sm font-bold shadow-lg z-50"
        >
          {toast}
        </div>
      )}
    </div>
  );
}
