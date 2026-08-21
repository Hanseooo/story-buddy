"use client";

import { useEffect } from "react";
import Link from "next/link";
import * as Sentry from "@sentry/nextjs";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    if (process.env.NODE_ENV === "production") {
      Sentry.captureException(error);
    } else {
      console.error("GlobalError caught root layout exception:", error);
    }
  }, [error]);

  return (
    <html lang="en">
      <body className="min-h-screen bg-[#F8F4E9] text-[#18204A] font-sans antialiased flex flex-col justify-center items-center p-6 text-center">
        <div className="w-full max-w-md bg-[#FFFDF7] border border-[rgb(49_85_217/0.18)] rounded-3xl p-8 shadow-[0_10px_28px_rgb(49_85_217/0.12)]">
          <div className="w-14 h-14 bg-[#F2C85F]/20 text-[#18204A] rounded-2xl flex items-center justify-center mx-auto mb-4 font-bold text-2xl">
            !
          </div>
          
          <h1 className="text-2xl font-bold tracking-tight text-[#18204A] mb-3">
            StoryBuddy needs a quick refresh
          </h1>

          <p className="text-base text-[#18204A]/80 leading-relaxed mb-6">
            Something interrupted the storybook connection. Click below to reload the app.
          </p>

          <div className="flex flex-col gap-3">
            <button
              type="button"
              onClick={() => reset()}
              className="w-full min-h-[48px] px-6 py-3 rounded-2xl bg-[#3155D9] text-[#FFFDF7] font-extrabold text-base hover:bg-[#213C9A] active:scale-[0.98] transition-all cursor-pointer"
            >
              Refresh Page
            </button>

            <Link
              href="/"
              className="w-full min-h-[44px] inline-flex items-center justify-center px-4 py-2 rounded-2xl text-sm font-bold text-[#3155D9] hover:underline"
            >
              Return to StoryBuddy Home
            </Link>

            <form action="/auth/signout" method="post">
              <button
                type="submit"
                className="w-full min-h-[44px] px-4 py-2 rounded-2xl border border-[#3155D9]/20 text-sm font-bold text-[#3155D9] hover:bg-[#3155D9]/5 transition-colors"
              >
                Log out
              </button>
            </form>
          </div>
        </div>
      </body>
    </html>
  );
}
