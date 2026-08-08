"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import Link from "next/link";
import { motion } from "motion/react";

export default function Signup() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { display_name: displayName } },
    });
    if (error) {
      setErrorMsg(error.message);
      setLoading(false);
      return;
    }
    // Email confirmation OFF → Supabase returns a live session; go straight in.
    // Email confirmation ON  → session is null; show the check-your-email prompt.
    // Non-disclosure: existing-email returns no error but empty identities — both paths show same success.
    if (data.session) {
      router.push("/classroom");
      return;
    }
    setSubmitted(true);
    setLoading(false);
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
          <div className="mb-6 lg:mb-8 w-12 h-12 mx-auto lg:mx-0 rounded-2xl bg-surface/10 border border-surface/20 backdrop-blur-sm flex items-center justify-center">
             <span className="font-display font-extrabold text-2xl text-secondary">SB</span>
          </div>
          <h1 className="font-display text-4xl lg:text-5xl xl:text-6xl font-extrabold tracking-tight mb-4 leading-none">
            Start a new <span className="text-secondary">adventure.</span>
          </h1>
          <p className="text-lg lg:text-xl text-on-primary/80 max-w-[40ch] leading-relaxed hidden sm:block mx-auto lg:mx-0">
            Create an account to build your classroom, review stories, and guide your students safely.
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
            Sign Up
          </h2>
          <p className="text-sm text-foreground/70 mb-8">
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

          {errorMsg && (
            <div
              role="alert"
              className="mb-6 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm font-bold"
            >
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSignup} className="flex flex-col gap-5">
            <div>
              <label htmlFor="displayName" className="block text-sm font-bold mb-1.5 text-foreground">
                Your name
              </label>
              <input
                id="displayName"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                className="w-full min-h-[44px] px-4 py-3 rounded-xl border border-primary/20 bg-surface text-foreground placeholder-foreground/40 transition-colors focus:outline-none focus:border-primary focus-visible:outline-[3px] focus-visible:outline-secondary focus-visible:outline-offset-[3px]"
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
                className="w-full min-h-[44px] px-4 py-3 rounded-xl border border-primary/20 bg-surface text-foreground placeholder-foreground/40 transition-colors focus:outline-none focus:border-primary focus-visible:outline-[3px] focus-visible:outline-secondary focus-visible:outline-offset-[3px]"
                placeholder="teacher@school.edu"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-bold mb-1.5 text-foreground">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full min-h-[44px] px-4 py-3 rounded-xl border border-primary/20 bg-surface text-foreground transition-colors focus:outline-none focus:border-primary focus-visible:outline-[3px] focus-visible:outline-secondary focus-visible:outline-offset-[3px]"
                placeholder="••••••••"
              />
            </div>

            <motion.button
              type="submit"
              disabled={loading}
              whileTap={{ y: loading ? 0 : 2, boxShadow: loading ? "0 4px 0 var(--color-primary-deep)" : "0 0px 0 var(--color-primary-deep)" }}
              className="w-full min-h-[44px] mt-4 inline-flex items-center justify-center rounded-xl bg-primary px-4 py-3 text-base font-extrabold text-on-primary shadow-[0_4px_0_var(--color-primary-deep)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Signing up..." : "Sign up"}
            </motion.button>
          </form>

          <div className="mt-8 text-center text-sm font-bold text-foreground/70">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:text-primary-deep underline decoration-primary/30 underline-offset-4 transition-colors">
              Log in
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
