"use client";

import { useState } from "react";
import { createBrowserClient } from "@supabase/ssr";
import Link from "next/link";

export default function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const supabase = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  );

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");
    setError("");

    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
    });

    if (signUpError) {
      setError(signUpError.message);
    } else {
      setMessage("Check your email for confirmation link.");
    }
    setLoading(false);
  };

  return (
    <div className="font-sans min-h-screen bg-background text-foreground flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-surface border border-primary/20 rounded-2xl p-6 sm:p-8 shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-primary mb-2">
          Sign Up
        </h1>
        <p className="text-sm text-foreground/70 mb-6">
          Create an account to start writing stories and managing your classroom.
        </p>

        {error && (
          <div
            role="alert"
            className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium"
          >
            {error}
          </div>
        )}

        {message && (
          <div
            role="alert"
            className="mb-4 p-3 rounded-xl bg-success/10 border border-success/20 text-success text-sm font-medium"
          >
            {message}
          </div>
        )}

        <form onSubmit={handleSignup} className="flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="block text-sm font-semibold mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full min-h-11 px-3.5 py-2.5 rounded-xl border border-primary/20 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2"
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-semibold mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full min-h-11 px-3.5 py-2.5 rounded-xl border border-primary/20 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full min-h-11 mt-2 inline-flex items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-base font-extrabold text-on-primary shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Signing up..." : "Sign up"}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-foreground/70">
          Already have an account?{" "}
          <Link href="/login" className="font-bold text-primary underline">
            Log in
          </Link>
        </div>
      </div>
    </div>
  );
}
