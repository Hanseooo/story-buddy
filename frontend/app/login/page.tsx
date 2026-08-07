"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";

export default function Login() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const confirmed = searchParams.get("message") === "email-confirmed";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (signInError) {
      setError(signInError.message);
      setLoading(false);
    } else {
      router.push("/dashboard");
    }
  };

  return (
    <div className="font-sans min-h-screen bg-background text-foreground flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-surface border border-primary/20 rounded-2xl p-6 sm:p-8 shadow-[0_10px_28px_rgba(49,85,217,0.12)]">
        <h1 className="font-display text-3xl font-extrabold tracking-tight text-primary mb-2">
          Log In
        </h1>
        <p className="text-sm text-foreground/70 mb-6">
          Welcome back. Enter your account details to access your classroom.
        </p>

        {confirmed && (
          <div
            role="status"
            className="mb-4 p-3 rounded-xl bg-success/10 border border-success/20 text-success text-sm font-medium"
          >
            Your email is confirmed — log in.
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium"
          >
            {error}
          </div>
        )}

        <form onSubmit={handleLogin} className="flex flex-col gap-4">
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
            {loading ? "Logging in..." : "Log in"}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-foreground/70">
          Need an account?{" "}
          <Link href="/signup" className="font-bold text-primary underline">
            Sign up
          </Link>
        </div>
      </div>
    </div>
  );
}
