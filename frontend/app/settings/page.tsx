"use client";

import { useEffect, useRef, useState } from "react";
import { createBrowserClient } from "@supabase/ssr";
import Link from "next/link";
import { ArrowLeft } from "@phosphor-icons/react";
import { changePassword, passwordLengthError } from "@/lib/password";

export default function TeacherSettingsPage() {
  const [profile, setProfile] = useState<{
    display_name: string | null;
    email: string;
  } | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);
  const submittingPassword = useRef(false);
  const passwordFeedback = useRef<HTMLParagraphElement>(null);
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (pwError) passwordFeedback.current?.focus();
  }, [pwError]);

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
    if (submittingPassword.current) return;
    setPwError(null);
    setPwSuccess(false);
    if (!currentPassword) {
      setPwError("Enter your current password.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwError("Passwords do not match");
      return;
    }
    const lengthError = passwordLengthError(newPassword);
    if (lengthError) {
      setPwError(lengthError);
      return;
    }
    submittingPassword.current = true;
    setSavingPassword(true);
    try {
      const { error } = await changePassword(supabase, currentPassword, newPassword, confirmPassword);
      if (error) {
        if (error.code === "current_password_mismatch" || error.code === "current_password_required") {
          setPwError("Your current password is incorrect. Check it and try again.");
        } else if (error.code === "weak_password" || error.code === "same_password") {
          setPwError("Choose a different password with at least 8 characters. Spaces are okay.");
        } else if (error.status === 401 || error.code === "session_not_found" || error.code === "refresh_token_not_found") {
          setPwError("Your session has ended. Log out and sign in again.");
        } else {
          setPwError("We couldn't save your password. Check your connection and try again.");
        }
        return;
      }
      setPwSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setShowPasswords(false);
      showToast("Password changed");
    } catch {
      setPwError("We couldn't confirm your password was saved. Check your connection. Try signing in with your new password before changing it again.");
    } finally {
      submittingPassword.current = false;
      setSavingPassword(false);
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
        <p className="text-sm text-foreground/60 mb-4">Use at least 8 characters. Spaces are okay.</p>
        <form onSubmit={handleChangePassword} aria-busy={savingPassword} className="space-y-3">
          <label htmlFor="current-password" className="block text-sm font-bold">Current password</label>
          <input
            id="current-password"
            type={showPasswords ? "text" : "password"}
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
            required
            disabled={savingPassword}
            className="w-full min-h-11 bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <label htmlFor="new-password" className="block text-sm font-bold">New password</label>
          <input
            id="new-password"
            type={showPasswords ? "text" : "password"}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="New password"
            autoComplete="new-password"
            required
            disabled={savingPassword}
            className="w-full min-h-11 bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <label htmlFor="confirm-password" className="block text-sm font-bold">Confirm new password</label>
          <input
            id="confirm-password"
            type={showPasswords ? "text" : "password"}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
            autoComplete="new-password"
            required
            disabled={savingPassword}
            className="w-full min-h-11 bg-background border border-primary/20 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <button
            type="button"
            aria-pressed={showPasswords}
            onClick={() => setShowPasswords((shown) => !shown)}
            className="min-h-11 px-3 text-sm font-bold text-primary rounded-xl focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            {showPasswords ? "Hide passwords" : "Show passwords"}
          </button>
          {pwError && (
            <p ref={passwordFeedback} tabIndex={-1} className="text-destructive text-sm" role="alert">
              {pwError}
            </p>
          )}
          {pwSuccess && (
            <p className="text-success text-sm" role="status">Password changed successfully.</p>
          )}
          <button
            type="submit"
            disabled={savingPassword || !currentPassword || !newPassword || !confirmPassword}
            className="min-h-[44px] px-5 py-2 bg-primary text-on-primary rounded-xl text-sm font-bold disabled:opacity-50"
          >
            {savingPassword ? "Saving…" : "Change password"}
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
