"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { normalizeNickname } from "@/lib/nickname";
import Link from "next/link";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, Eye, EyeSlash, UserCircle, Key } from "@phosphor-icons/react";

// S1-3 alphabet: a-z0-9 minus {0,o,1,i,l}
const CODE_REGEX = /^[a-hj-km-np-z2-9]{6}$/;

export const CRED_ERROR = "Something didn't work. Check your code and nickname.";
export const NET_ERROR = "We can't reach StoryBuddy right now. Try again in a moment.";

export default function JoinCodePage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const router = useRouter();
  const shouldReduceMotion = useReducedMotion();
  const [code, setCode] = useState<string | null>(null);
  const [malformed, setMalformed] = useState<string | null>(null);
  const [step, setStep] = useState<2 | 3>(2);
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    params.then(({ code: c }) => {
      if (!CODE_REGEX.test(c)) {
        setMalformed(c);
      } else {
        setCode(c);
      }
    });
  }, [params]);

  // popstate: back from step 3 returns to step 2
  useEffect(() => {
    const onPop = () => setStep(2);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const advanceToPassword = (e: React.FormEvent) => {
    e.preventDefault();
    window.history.pushState({ step: 3 }, "");
    setStep(3);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code) return;
    setLoading(true);
    setError("");

    try {
      let normalizedNick: string;
      try {
        normalizedNick = normalizeNickname(nickname);
      } catch {
        setError(CRED_ERROR);
        setStep(2);
        setLoading(false);
        return;
      }

      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email: `${normalizedNick}@${code}.students.storybuddy.invalid`,
        password,
      });

      if (signInError || !data.user) {
        setError(CRED_ERROR);
        setStep(2);
        setLoading(false);
      } else {
        router.push(`/s/${data.user.id}`);
      }
    } catch {
      // Network failure — distinct message (spec §5.2)
      setError(NET_ERROR);
      setStep(2);
      setLoading(false);
    }
  };

  if (malformed !== null) {
    return (
      <main className="font-kid min-h-[100dvh] bg-background text-foreground flex items-center justify-center p-6 relative overflow-hidden">
        {/* Tactile Background */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
          <div className="absolute -top-16 -right-16 size-64 rounded-full bg-secondary/20" />
          <div className="absolute -bottom-20 -left-20 size-80 rounded-[48px] bg-primary/5 rotate-12" />
        </div>

        <div className="max-w-md w-full text-center bg-surface border border-primary/15 rounded-[24px] p-8 shadow-[0_10px_28px_rgba(49,85,217,0.08)] relative z-10">
          <p className="text-lg font-bold mb-2">This code doesn&apos;t look right:</p>
          <p className="font-mono text-3xl font-extrabold text-primary mb-6 tracking-wider">{malformed}</p>
          <Link
            href="/join"
            className="inline-flex min-h-12 items-center justify-center px-6 py-3 rounded-xl bg-primary text-on-primary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform hover:-translate-y-0.5"
          >
            Try again
          </Link>
        </div>
      </main>
    );
  }

  if (!code) return null;

  const nicknamePreview = (() => {
    try { return normalizeNickname(nickname); } catch { return null; }
  })();

  return (
    <main className="font-kid min-h-[100dvh] bg-background text-foreground flex items-center justify-center p-4 sm:p-6 relative overflow-hidden">
      {/* Back Button */}
      <div className="absolute top-6 left-6 sm:top-8 sm:left-8 z-50">
        {step === 2 ? (
          <Link 
            href="/join" 
            className="inline-flex min-h-11 items-center gap-2 text-foreground/70 hover:text-primary font-bold text-sm transition-colors group focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary rounded-xl px-3 py-1.5 -ml-2"
          >
            <ArrowLeft size={18} weight="bold" className="transition-transform group-hover:-translate-x-1" />
            Class Code
          </Link>
        ) : (
          <button 
            type="button"
            onClick={() => setStep(2)} 
            className="inline-flex min-h-11 items-center gap-2 text-foreground/70 hover:text-primary font-bold text-sm transition-colors group focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary rounded-xl px-3 py-1.5 -ml-2 cursor-pointer"
          >
            <ArrowLeft size={18} weight="bold" className="transition-transform group-hover:-translate-x-1" />
            Nickname
          </button>
        )}
      </div>

      {/* Tactile Playroom Background Shapes */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <div className="absolute -top-16 -right-16 size-64 rounded-full bg-secondary/20" />
        <div className="absolute -bottom-20 -left-20 size-80 rounded-[48px] bg-primary/5 rotate-12" />
        <div className="absolute top-1/4 left-10 size-12 rounded-full bg-coral/15" />
      </div>

      <motion.div 
        initial={{ opacity: 0, scale: shouldReduceMotion ? 1 : 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="w-full max-w-md bg-surface border border-primary/15 rounded-[24px] p-6 sm:p-10 shadow-[0_10px_28px_rgba(49,85,217,0.08)] relative z-10"
      >
        {step === 2 ? (
          <div>
            <div className="text-center mb-8">
              <div className="size-16 mx-auto bg-primary/10 text-primary rounded-2xl flex items-center justify-center mb-6 shadow-sm">
                <UserCircle size={32} weight="duotone" />
              </div>
              <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-primary mb-2 tracking-tight">
                What&apos;s your nickname?
              </h1>
              <p className="text-foreground/75 text-base">
                The name for class <strong className="uppercase text-primary tracking-wide font-mono">{code}</strong>.
                <span className="mx-2 text-foreground/30">•</span>
                <Link href="/join" className="text-primary font-bold hover:underline">Change</Link>
              </p>
            </div>

            {error && (
              <div role="alert" className="mb-5 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm font-bold">
                {error}
              </div>
            )}

            <form onSubmit={advanceToPassword} className="flex flex-col gap-5">
              <div>
                <label htmlFor="nickname" className="block text-sm font-bold mb-1.5 text-foreground">
                  Nickname
                </label>
                <input
                  id="nickname"
                  autoFocus
                  type="text"
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  placeholder="e.g. Maya"
                  required
                  className="w-full min-h-[48px] px-4 py-3 rounded-xl border border-primary/20 bg-background text-foreground placeholder-foreground/40 transition-colors focus:outline-none focus:border-primary focus-visible:ring-[3px] focus-visible:ring-secondary text-lg"
                />
              </div>

              {nickname && nicknamePreview && (
                <p className="text-xs text-foreground/70 bg-background px-3 py-2 rounded-lg border border-primary/10">
                  we&apos;ll look for: <strong className="font-mono text-primary">{nicknamePreview}</strong>
                </p>
              )}

              <button
                type="submit"
                disabled={!nickname.trim()}
                className="w-full min-h-[52px] mt-2 rounded-xl bg-primary text-on-primary text-lg font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed disabled:transform-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
              >
                Next
              </button>
            </form>
          </div>
        ) : (
          <div>
            <div className="text-center mb-8">
              <div className="size-16 mx-auto bg-secondary/30 text-foreground rounded-2xl flex items-center justify-center mb-6 shadow-sm">
                <Key size={32} weight="duotone" />
              </div>
              <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-primary mb-2 tracking-tight">
                Enter your secret word
              </h1>
              <p className="text-foreground/75 text-base font-kid">
                Type the secret word from your login slip for class <strong className="uppercase text-primary font-mono tracking-wide">{code}</strong>.
              </p>
            </div>

            {error && (
              <div role="alert" className="mb-5 p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm font-bold">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="flex flex-col gap-5">
              <div>
                <label htmlFor="password" className="block text-sm font-bold mb-1.5 text-foreground">
                  Secret Word
                </label>
                <div className="relative">
                  <input
                    id="password"
                    autoFocus
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    placeholder="e.g. dragon"
                    className="w-full min-h-[48px] px-4 py-3 rounded-xl border border-primary/20 bg-background text-foreground placeholder-foreground/40 transition-colors focus:outline-none focus:border-primary focus-visible:ring-[3px] focus-visible:ring-secondary pr-20 text-lg"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-sm font-bold text-primary min-h-10 px-2 flex items-center gap-1 hover:text-primary-deep cursor-pointer"
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
              </div>

              <button
                type="submit"
                disabled={loading || !password}
                className="w-full min-h-[52px] mt-2 rounded-xl bg-primary text-on-primary text-lg font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] transition-transform duration-150 hover:-translate-y-0.5 active:translate-y-0.5 disabled:opacity-50 disabled:shadow-none disabled:cursor-not-allowed disabled:transform-none focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-secondary"
              >
                {loading ? "Joining..." : "Join class"}
              </button>
            </form>
          </div>
        )}
      </motion.div>
    </main>
  );
}
