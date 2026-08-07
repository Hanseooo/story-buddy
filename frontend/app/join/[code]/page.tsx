"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";
import { normalizeNickname } from "@/lib/nickname";
import Link from "next/link";

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
      <main className="font-kid min-h-screen bg-background text-foreground flex items-center justify-center p-6">
        <div className="max-w-md w-full text-center">
          <p className="text-lg font-bold mb-2">This code doesn&apos;t look right:</p>
          <p className="font-mono text-2xl font-extrabold text-primary mb-6">{malformed}</p>
          <Link
            href="/join"
            className="inline-flex min-h-11 items-center justify-center px-6 py-2.5 rounded-xl bg-primary text-on-primary font-extrabold"
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

  if (step === 2) {
    return (
      <main className="font-kid min-h-screen bg-background text-foreground flex items-center justify-center p-6">
        <div className="max-w-md w-full">
          <h1 className="font-display text-3xl font-extrabold text-primary mb-2">
            What&apos;s your nickname?
          </h1>
          <p className="text-foreground/70 mb-6">The name your teacher gave you.</p>

          {error && (
            <div role="alert" className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
              {error}
            </div>
          )}

          <form onSubmit={advanceToPassword} className="flex flex-col gap-4">
            <div>
              <label htmlFor="nickname" className="block font-semibold mb-1">Nickname</label>
              <input
                id="nickname"
                autoFocus
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                required
                className="w-full min-h-11 px-3.5 py-2.5 rounded-xl border border-primary/20 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-secondary"
              />
            </div>
            {nickname && nicknamePreview && (
              <p className="text-sm text-foreground/70">
                we&apos;ll look for: <strong>{nicknamePreview}</strong>
              </p>
            )}
            <button
              type="submit"
              disabled={!nickname.trim()}
              className="w-full min-h-11 rounded-xl bg-primary text-on-primary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] disabled:opacity-50"
            >
              Next
            </button>
          </form>
        </div>
      </main>
    );
  }

  return (
    <main className="font-kid min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="max-w-md w-full">
        <h1 className="font-display text-3xl font-extrabold text-primary mb-2">
          Create your password
        </h1>
        <p className="text-foreground/70 mb-6">You&apos;ll use this every time you log in.</p>

        {error && (
          <div role="alert" className="mb-4 p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm font-medium">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label htmlFor="password" className="block font-semibold mb-1">Password</label>
            <div className="relative">
              <input
                id="password"
                autoFocus
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full min-h-11 px-3.5 py-2.5 rounded-xl border border-primary/20 bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-secondary pr-16"
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
          <button
            type="submit"
            disabled={loading || !password}
            className="w-full min-h-11 rounded-xl bg-primary text-on-primary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)] disabled:opacity-50"
          >
            {loading ? "Joining..." : "Join class"}
          </button>
        </form>
      </div>
    </main>
  );
}
