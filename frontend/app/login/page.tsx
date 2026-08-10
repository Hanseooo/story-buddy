"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import { motion } from "framer-motion";

export default function Login() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const confirmed = searchParams.get("message") === "email-confirmed";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
      router.push("/classroom");
    }
  };

  return (
    <div className="font-sans min-h-[100dvh] flex flex-col lg:flex-row bg-background text-foreground relative">
      {/* Back Button */}
      <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-50">
        <Link href="/" className="inline-flex items-center gap-2 text-on-primary/80 hover:text-on-primary font-bold text-sm transition-colors group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-secondary rounded-lg px-2 py-1 -ml-2">
          <svg className="w-4 h-4 transition-transform group-hover:-translate-x-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5"><path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
          Home
        </Link>
      </div>

      {/* Brand Side - Cobalt */}
      <div className="w-full lg:w-5/12 xl:w-1/2 bg-primary relative flex flex-col p-8 lg:p-16 justify-center overflow-hidden">
        {/* Decorative CSS Shapes */}
        <div className="absolute inset-0 pointer-events-none opacity-20" aria-hidden="true">
          <div className="absolute top-[-10%] right-[-10%] w-64 h-64 rounded-full bg-secondary/30 blur-3xl"></div>
          <div className="absolute bottom-[-10%] left-[-10%] w-80 h-80 rounded-full bg-surface/20 blur-2xl"></div>
        </div>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
          className="relative z-10 text-on-primary max-w-lg mx-auto lg:mx-0 w-full text-center lg:text-left"
        >
          <div className="mb-6 lg:mb-8 w-14 h-14 mx-auto lg:mx-0 rounded-2xl bg-surface border border-primary/5 shadow-[0_12px_28px_rgba(24,32,74,0.15)] flex items-center justify-center overflow-hidden">
             {/* eslint-disable-next-line @next/next/no-img-element */}
             <img src="/logo.png" alt="" className="h-full w-full object-contain scale-[1.35]" />
          </div>
          <h1 className="font-display text-4xl lg:text-5xl xl:text-6xl font-extrabold tracking-tight mb-4 leading-none">
            Welcome back to your <span className="text-secondary">classroom.</span>
          </h1>
          <p className="text-lg lg:text-xl text-on-primary/80 max-w-[40ch] leading-relaxed hidden sm:block mx-auto lg:mx-0">
            The stories are waiting. Log in to manage your students, review their creations, and guide their adventures.
          </p>
        </motion.div>
      </div>

      {/* Form Side - Ivory Canvas */}
      <div className="w-full lg:w-7/12 xl:w-1/2 flex-1 flex items-center justify-center p-6 lg:p-12 border-t lg:border-t-0 lg:border-l border-primary/10">
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.6, ease: "easeOut", delay: 0.2 }}
          className="w-full max-w-md"
        >
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-primary mb-2">
            Log In
          </h2>
          <p className="text-sm text-foreground/70 mb-8">
            Enter your account details to access your dashboard.
          </p>

          {confirmed && (
            <div
              role="status"
              className="mb-6 p-4 rounded-xl bg-success/10 border border-success/20 text-success text-sm font-bold"
            >
              Your email is confirmed — log in.
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="mb-6 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm font-bold"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleLogin} className="flex flex-col gap-5">
            <div>
              <label htmlFor="email" className="block text-sm font-bold mb-1.5 text-foreground">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full min-h-[44px] px-4 py-3 rounded-xl border border-primary/20 bg-surface text-foreground placeholder-foreground/40 transition-colors focus:outline-none focus:border-primary focus-visible:outline-[3px] focus-visible:outline-secondary focus-visible:outline-offset-[3px]"
                placeholder="teacher@school.edu"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-bold mb-1.5 text-foreground">
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full min-h-[44px] px-4 py-3 rounded-xl border border-primary/20 bg-surface text-foreground transition-colors focus:outline-none focus:border-primary focus-visible:outline-[3px] focus-visible:outline-secondary focus-visible:outline-offset-[3px] pr-16"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-bold text-primary min-h-11 px-2"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileTap={{ y: loading ? 0 : 2, boxShadow: loading ? "0 4px 0 var(--color-primary-deep)" : "0 0px 0 var(--color-primary-deep)" }}
              className="w-full min-h-[44px] mt-4 inline-flex items-center justify-center rounded-xl bg-primary px-4 py-3 text-base font-extrabold text-on-primary shadow-[0_4px_0_var(--color-primary-deep)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Logging in..." : "Log in"}
            </motion.button>
          </form>

          <p className="mt-5 text-xs text-center text-foreground/60 leading-relaxed">
            By logging in, you agree to our{" "}
            <Link href="/terms" className="underline decoration-primary/30 hover:text-primary transition-colors">Terms of Service</Link>
            {" "}and{" "}
            <Link href="/privacy" className="underline decoration-primary/30 hover:text-primary transition-colors">Privacy Policy</Link>.
          </p>

          <div className="mt-8 flex flex-col gap-3 text-center text-sm font-bold text-foreground/70">
            <div>
              Need an account?{" "}
              <Link href="/signup" className="text-primary hover:text-primary-deep underline decoration-primary/30 underline-offset-4 transition-colors">
                Sign up
              </Link>
            </div>
            <div>
              Student?{" "}
              <Link href="/join" className="text-primary hover:text-primary-deep underline decoration-primary/30 underline-offset-4 transition-colors">
                Join your class
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
