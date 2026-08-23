"use client";

import { Suspense } from "react";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { useSearchParams } from "next/navigation";
import { Backpack, ChalkboardTeacher, ArrowRight, ArrowLeft } from "@phosphor-icons/react";

function WelcomeContent() {
  const searchParams = useSearchParams();
  const shouldReduceMotion = useReducedMotion();
  const intent = searchParams.get("action") === "signup" ? "signup" : "login";
  const teacherHref = intent === "signup" ? "/signup" : "/login";

  return (
    <div className="font-sans min-h-[100dvh] bg-background text-foreground relative flex items-center justify-center p-6 sm:p-12 overflow-hidden">
      {/* Back Button */}
      <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-50">
        <Link 
          href="/" 
          className="inline-flex min-h-11 items-center gap-2 text-foreground/70 hover:text-primary font-bold text-sm transition-colors group focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary rounded-xl px-3 py-1.5 -ml-2"
        >
          <ArrowLeft size={18} weight="bold" className="transition-transform group-hover:-translate-x-1" />
          Home
        </Link>
      </div>

      {/* Tactile Playroom Background Shapes (Crisp Geometric Cutouts - No Blur Slop) */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <div className="absolute -top-16 -right-16 size-64 rounded-full bg-secondary/20" />
        <div className="absolute -bottom-20 -left-20 size-80 rounded-[48px] bg-primary/5 rotate-12" />
        <div className="absolute top-1/4 left-10 size-12 rounded-full bg-coral/15" />
      </div>

      <div className="relative z-10 w-full max-w-4xl mx-auto py-12">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="text-center mb-10 sm:mb-12"
        >
          <div className="mb-6 inline-grid size-16 place-items-center rounded-2xl bg-surface border border-primary/10 shadow-[0_12px_28px_rgba(24,32,74,0.12)] overflow-hidden mx-auto">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/logo.png" alt="" className="h-full w-full object-contain scale-[1.35]" />
          </div>
          <h1 className="font-display text-4xl sm:text-5xl font-extrabold tracking-[-0.04em] text-primary">
            {intent === "signup" ? "Ready to write?" : "Welcome to StoryBuddy"}
          </h1>
          <p className="mt-3 font-kid text-lg text-foreground/70 max-w-md mx-auto">
            Choose how you want to enter the playroom today.
          </p>
        </motion.div>

        {/* 2-Card Portal Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl mx-auto">
          {/* Student Card */}
          <motion.div
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut", delay: shouldReduceMotion ? 0 : 0.05 }}
          >
            <Link 
              href="/join"
              className="group flex flex-col justify-between h-full bg-surface border border-primary/15 rounded-[24px] p-7 sm:p-8 shadow-[0_10px_28px_rgba(49,85,217,0.08)] hover:shadow-[0_16px_42px_rgba(49,85,217,0.14)] hover:border-primary/30 active:scale-[0.98] transition-all duration-200 focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[4px] focus-visible:ring-offset-background"
            >
              <div>
                <div className="size-14 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-6 group-hover:scale-105 transition-transform duration-200">
                  <Backpack size={32} weight="duotone" />
                </div>
                <h2 className="font-display text-2xl sm:text-3xl font-extrabold text-primary tracking-tight mb-2">
                  I&apos;m a Student
                </h2>
                <p className="font-kid text-foreground/75 text-base leading-relaxed mb-8">
                  Enter the 6-letter class code from your teacher to join your classroom and start your story.
                </p>
              </div>

              <div className="inline-flex min-h-12 items-center justify-between w-full rounded-xl bg-primary text-on-primary px-5 py-3 font-display text-base font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 group-hover:-translate-y-0.5 active:translate-y-0.5 active:shadow-none">
                <span>Enter Class Code</span>
                <ArrowRight size={20} weight="bold" className="transition-transform group-hover:translate-x-1" />
              </div>
            </Link>
          </motion.div>

          {/* Teacher / Parent Card */}
          <motion.div
            initial={{ opacity: 0, y: shouldReduceMotion ? 0 : 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: "easeOut", delay: shouldReduceMotion ? 0 : 0.1 }}
          >
            <Link 
              href={teacherHref}
              className="group flex flex-col justify-between h-full bg-surface border border-primary/15 rounded-[24px] p-7 sm:p-8 shadow-[0_10px_28px_rgba(49,85,217,0.08)] hover:shadow-[0_16px_42px_rgba(49,85,217,0.14)] hover:border-primary/30 active:scale-[0.98] transition-all duration-200 focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary focus-visible:ring-offset-[4px] focus-visible:ring-offset-background"
            >
              <div>
                <div className="size-14 rounded-2xl bg-secondary/30 text-foreground flex items-center justify-center mb-6 group-hover:scale-105 transition-transform duration-200">
                  <ChalkboardTeacher size={32} weight="duotone" />
                </div>
                <h2 className="font-display text-2xl sm:text-3xl font-extrabold text-primary tracking-tight mb-2">
                  Teacher or Parent
                </h2>
                <p className="font-kid text-foreground/75 text-base leading-relaxed mb-8">
                  {intent === "signup"
                    ? "Create an account to set up classrooms, review stories, and guide your young authors."
                    : "Log in with your email to manage classrooms, student rosters, and story adventures."}
                </p>
              </div>

              <div className="inline-flex min-h-12 items-center justify-between w-full rounded-xl bg-secondary text-on-secondary px-5 py-3 font-display text-base font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 group-hover:-translate-y-0.5 active:translate-y-0.5 active:shadow-none">
                <span>{intent === "signup" ? "Create Teacher Account" : "Log In with Email"}</span>
                <ArrowRight size={20} weight="bold" className="transition-transform group-hover:translate-x-1" />
              </div>
            </Link>
          </motion.div>
        </div>

        {/* Alternate action switch */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="mt-8 text-center"
        >
          {intent === "signup" ? (
            <p className="font-kid text-sm text-foreground/70">
              Already have a teacher account?{" "}
              <Link 
                href="/welcome?action=login" 
                className="font-bold text-primary hover:text-primary-deep underline decoration-primary/30 underline-offset-4 transition-colors"
              >
                Log in instead
              </Link>
            </p>
          ) : (
            <p className="font-kid text-sm text-foreground/70">
              Need a teacher account?{" "}
              <Link 
                href="/welcome?action=signup" 
                className="font-bold text-primary hover:text-primary-deep underline decoration-primary/30 underline-offset-4 transition-colors"
              >
                Sign up here
              </Link>
            </p>
          )}
        </motion.div>
      </div>
    </div>
  );
}

export default function WelcomePage() {
  return (
    <Suspense fallback={
      <div className="min-h-[100dvh] bg-background flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
      </div>
    }>
      <WelcomeContent />
    </Suspense>
  );
}
