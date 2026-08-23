"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, Eye, EyeSlash } from "@phosphor-icons/react";

export default function Signup() {
  const router = useRouter();
  const shouldReduceMotion = useReducedMotion();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { display_name: displayName } },
    });
    if (!error && data?.session) {
      // Email confirmation OFF → Supabase returns a live session; go straight in.
      router.push("/classroom");
      return;
    }
    // Email confirmation ON → session is null; show check-your-email.
    // Non-disclosure: existing-email returns an error — we must NOT reveal it.
    // Always show the same success-looking prompt to prevent account enumeration.
    setSubmitted(true);
    setLoading(false);
  };

  return (
    <div className="font-sans min-h-[100dvh] flex flex-col lg:flex-row bg-background text-foreground relative overflow-hidden">
      {/* Back Button */}
      <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-50">
        <Link 
          href="/" 
          className="inline-flex min-h-11 items-center gap-2 text-on-primary/80 hover:text-on-primary font-bold text-sm transition-colors group focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary rounded-xl px-3 py-1.5 -ml-2"
        >
          <ArrowLeft size={18} weight="bold" className="transition-transform group-hover:-translate-x-1" />
          Home
        </Link>
      </div>

      {/* Brand Side - Cobalt */}
      <div className="w-full lg:w-5/12 xl:w-1/2 bg-primary relative flex flex-col p-8 sm:p-12 lg:p-16 justify-center overflow-hidden">
        {/* Crisp Tactile Geometric Shapes (No Blur Slop) */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
          <div className="absolute -top-12 -right-12 size-56 rounded-full bg-secondary/20" />
          <div className="absolute -bottom-16 -left-16 size-72 rounded-[40px] bg-surface/10 rotate-12" />
          <div className="absolute bottom-1/4 right-10 size-12 rounded-full bg-coral/20" />
        </div>

        <motion.div 
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="relative z-10 text-on-primary max-w-lg mx-auto lg:mx-0 w-full text-center lg:text-left pt-12 lg:pt-0"
        >
          <div className="mb-6 lg:mb-8 size-16 mx-auto lg:mx-0 rounded-2xl bg-surface border border-primary/10 shadow-[0_12px_28px_rgba(24,32,74,0.15)] flex items-center justify-center overflow-hidden">
             {/* eslint-disable-next-line @next/next/no-img-element */}
             <img src="/logo.png" alt="" className="h-full w-full object-contain scale-[1.35]" />
          </div>
          <h1 className="font-display text-4xl lg:text-5xl xl:text-6xl font-extrabold tracking-tight mb-4 leading-none text-balance">
            Start a new <span className="text-secondary">adventure.</span>
          </h1>
          <p className="text-lg lg:text-xl text-[#DFE5FF] max-w-[40ch] leading-relaxed hidden sm:block mx-auto lg:mx-0 font-kid">
            Create an account to build your classroom, review stories, and guide your students safely.
          </p>
        </motion.div>
      </div>

      {/* Form Side - Ivory Canvas with Tactile Ambient Shapes */}
      <div className="w-full lg:w-7/12 xl:w-1/2 flex-1 flex items-center justify-center p-6 lg:p-12 border-t lg:border-t-0 lg:border-l border-primary/10 relative">
        <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
          <div className="absolute top-10 right-10 size-32 rounded-full bg-secondary/15" />
          <div className="absolute bottom-10 right-1/4 size-48 rounded-[32px] bg-primary/5 -rotate-6" />
        </div>

        <motion.div 
          initial={{ opacity: 0, x: shouldReduceMotion ? 0 : 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5, ease: "easeOut", delay: shouldReduceMotion ? 0 : 0.1 }}
          className="w-full max-w-md relative z-10 bg-surface border border-primary/15 rounded-[24px] p-7 sm:p-10 shadow-[0_10px_28px_rgba(49,85,217,0.08)]"
        >
          <h2 className="font-display text-3xl font-extrabold tracking-tight text-primary mb-1.5">
            Sign Up
          </h2>
          <p className="font-kid text-sm text-foreground/75 mb-6">
            Create your account to start managing your classroom.
          </p>

          {submitted && (
            <div
              role="alert"
              className="mb-6 p-4 rounded-xl bg-success/10 border border-success/20 text-success text-sm font-bold"
            >
              Check your email for a confirmation link.
            </div>
          )}

          <form onSubmit={handleSignup} className="flex flex-col gap-4">
            <div>
              <label htmlFor="displayName" className="block text-sm font-bold mb-1.5 text-foreground">
                Your name
              </label>
              <input
                id="displayName"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full min-h-[48px] px-4 py-3 rounded-xl border border-primary/20 bg-background text-foreground placeholder-foreground/40 transition-colors focus:outline-none focus:border-primary focus-visible:ring-[3px] focus-visible:ring-secondary text-base"
                placeholder="Ms. Frizzle"
              />
            </div>

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
                className="w-full min-h-[48px] px-4 py-3 rounded-xl border border-primary/20 bg-background text-foreground placeholder-foreground/40 transition-colors focus:outline-none focus:border-primary focus-visible:ring-[3px] focus-visible:ring-secondary text-base"
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
                  className="w-full min-h-[48px] px-4 py-3 rounded-xl border border-primary/20 bg-background text-foreground transition-colors focus:outline-none focus:border-primary focus-visible:ring-[3px] focus-visible:ring-secondary pr-14 text-base"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 min-h-10 px-2 text-sm font-bold text-primary hover:text-primary-deep transition-colors flex items-center gap-1.5 cursor-pointer"
                >
                  {showPassword ? (
                    <>
                      <EyeSlash size={18} weight="bold" />
                      Hide
                    </>
                  ) : (
                    <>
                      <Eye size={18} weight="bold" />
                      Show
                    </>
                  )}
                </button>
              </div>
              <p className="text-xs text-foreground/60 mt-1.5 ml-1 font-kid">Must be at least 6 characters</p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full min-h-[48px] mt-2 inline-flex items-center justify-center rounded-xl bg-primary px-4 py-3 text-base font-extrabold text-on-primary shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed disabled:transform-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
            >
              {loading ? "Signing up..." : "Sign up"}
            </button>
          </form>

          <p className="mt-5 text-xs text-center text-foreground/60 leading-relaxed font-kid">
            By signing up, you agree to our{" "}
            <Link href="/terms" className="underline decoration-primary/30 hover:text-primary transition-colors">Terms of Service</Link>
            {" "}and{" "}
            <Link href="/privacy" className="underline decoration-primary/30 hover:text-primary transition-colors">Privacy Policy</Link>.
          </p>

          <div className="mt-6 pt-5 border-t border-primary/10 flex flex-col gap-2 text-center text-sm font-bold text-foreground/75 font-kid">
            <div>
              Already have an account?{" "}
              <Link href="/login" className="text-primary hover:text-primary-deep underline decoration-primary/30 underline-offset-4 transition-colors">
                Log in
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
