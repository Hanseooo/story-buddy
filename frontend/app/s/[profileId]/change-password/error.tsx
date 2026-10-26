"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

export default function AccountError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") Sentry.captureException(error);
    else console.error("Account onboarding error caught:", error);
  }, [error]);

  return <section className="font-kid mx-auto max-w-xl p-8 text-center">
    <h1 className="font-display text-2xl font-extrabold mb-4">We couldn&apos;t load your account</h1>
    <p className="mb-6">Check your connection and try again. If this keeps happening, ask your teacher.</p>
    <button onClick={reset} className="min-h-11 rounded-xl bg-primary px-6 font-bold text-on-primary focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">Try again</button>
    <form action="/auth/signout" method="post" className="mt-4"><button className="min-h-11 px-6 font-bold text-primary rounded-lg focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">Log out</button></form>
  </section>;
}
