"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { changePassword, passwordLengthError } from "@/lib/password";

export default function PasswordForm({ profileId, displayNickname }: { profileId: string; displayNickname: string }) {
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [visible, setVisible] = useState(false);
  const [pending, setPending] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [message, setMessage] = useState("");
  const busy = useRef(false);
  const feedback = useRef<HTMLParagraphElement>(null);
  useEffect(() => { if (message) feedback.current?.focus(); }, [message]);

  function proceed(path?: string) {
    const root = `/s/${profileId}`;
    if (path !== root && path !== `${root}/introduction`) throw new Error("Incomplete password change");
    setCurrent(""); setPassword(""); setConfirmation(""); setVisible(false);
    router.replace(path);
    router.refresh();
  }

  async function checkState() {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session) throw new Error("Session unavailable");
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/me/onboarding`, {
      cache: "no-store", headers: { Authorization: `Bearer ${session.access_token}` },
    });
    if (!response.ok) throw new Error("State unavailable");
    const state = await response.json();
    if (state.password_change_required === false) { proceed(state.next_path); return; }
    setUncertain(false);
    setMessage("Your password change is still required. Check your current secret word and try again. If your teacher reset it, use the newest word.");
  }

  async function recover() {
    setUncertain(true);
    try { await checkState(); }
    catch { setMessage("We couldn't confirm your password was saved. Check your connection, then check again before changing it again."); }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    setMessage("");
    if (!current) { setMessage("Enter your current secret word."); return; }
    if (password !== confirmation) { setMessage("Your passwords don't match. Type them again."); return; }
    const lengthError = passwordLengthError(password);
    if (lengthError) { setMessage(lengthError); return; }
    if (password === current) { setMessage("Choose a password different from your current secret word."); return; }
    busy.current = true; setPending(true);
    try {
      const result = await changePassword(supabase, current, password, confirmation);
      if (!result.error) { proceed(result.next_path); return; }
      if (result.error.status >= 500) { await recover(); return; }
      const code = result.error.code;
      setMessage(code === "current_password_mismatch" || code === "current_password_required"
        ? "Your current secret word is incorrect. Check it and try again."
        : code === "same_password" || code === "weak_password"
          ? "Choose a different password with at least 8 characters. Spaces are okay."
          : result.error.status === 401 ? "Your session has ended. Log out and sign in again."
            : "We couldn't save your password. Try again, or ask your teacher for help.");
    } catch { await recover(); }
    finally { busy.current = false; setPending(false); }
  }

  return <section className="font-kid mx-auto w-full max-w-xl px-6 py-10 sm:py-16">
    <p className="font-bold text-primary mb-3">Signed in as {displayNickname}</p>
    <h1 className="font-display text-4xl sm:text-5xl font-extrabold mb-4">Choose your own password</h1>
    <p className="mb-2">Your new password replaces the secret word your teacher gave you.</p>
    <p className="mb-8">Use at least 8 characters. Spaces are okay. If you forget it, ask your teacher.</p>
    <form onSubmit={submit} onKeyDown={(event) => { if (event.key === "Escape") setVisible(false); }} className="space-y-5">
      {[
        { id: "current-secret", label: "Current secret word", value: current, update: setCurrent, autoComplete: "current-password" },
        { id: "new-password", label: "New password", value: password, update: setPassword, autoComplete: "new-password" },
        { id: "confirm-password", label: "Type your new password again", value: confirmation, update: setConfirmation, autoComplete: "new-password" },
      ].map((field) => <div key={field.id}>
        <label htmlFor={field.id} className="block font-bold mb-2">{field.label}</label>
        <input id={field.id} type={visible ? "text" : "password"} autoComplete={field.autoComplete} required
          value={field.value} onChange={(event) => field.update(event.target.value)} disabled={pending || uncertain}
          className="w-full min-h-12 rounded-xl border border-primary/25 bg-surface px-4 focus:outline-none focus:ring-[3px] focus:ring-secondary disabled:opacity-60" />
      </div>)}
      <button type="button" aria-pressed={visible} onClick={() => setVisible(!visible)} className="min-h-11 font-bold text-primary rounded-lg focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">{visible ? "Hide passwords" : "Show passwords"}</button>
      {message && <p ref={feedback} tabIndex={-1} role="alert" className="rounded-xl border border-primary/20 bg-surface p-4">{message}</p>}
      {uncertain ? <button type="button" disabled={pending} onClick={async () => {
        if (busy.current) return;
        busy.current = true; setPending(true);
        try { await recover(); } finally { busy.current = false; setPending(false); }
      }} className="min-h-12 w-full rounded-xl bg-primary text-on-primary font-bold disabled:opacity-60 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">{pending ? "Checking…" : "Check again"}</button>
        : <button type="submit" disabled={pending} className="min-h-12 w-full rounded-xl bg-primary text-on-primary font-bold disabled:opacity-60 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">{pending ? "Saving…" : "Save my password"}</button>}
    </form>
    <form action="/auth/signout" method="post" className="mt-6 text-center"><button className="min-h-11 px-5 font-bold text-primary rounded-lg focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">Log out</button></form>
  </section>;
}
