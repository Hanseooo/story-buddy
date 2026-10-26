"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";

export default function Introduction({ profileId }: { profileId: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const busy = useRef(false);
  const feedback = useRef<HTMLParagraphElement>(null);
  useEffect(() => { if (failed) feedback.current?.focus(); }, [failed]);
  async function dismiss() {
    if (busy.current) return;
    busy.current = true; setPending(true);
    try {
      const { error } = await supabase.rpc("dismiss_student_introduction");
      if (error) throw error;
      router.replace(`/s/${profileId}`); router.refresh();
    } catch { setFailed(true); }
    finally { busy.current = false; setPending(false); }
  }
  return <section className="font-kid mx-auto w-full max-w-2xl px-6 py-10 sm:py-16">
    <h1 className="font-display text-4xl sm:text-5xl font-extrabold mb-8">Find your way around</h1>
    <dl className="space-y-6 mb-10">
      <div><dt className="text-xl font-extrabold text-primary">Bookshelf</dt><dd>Your stories live here.</dd></div>
      <div><dt className="text-xl font-extrabold text-primary">Gallery</dt><dd>Find stories your teacher has shared with your class.</dd></div>
      <div><dt className="text-xl font-extrabold text-primary">Profile</dt><dd>Change your password or log out here.</dd></div>
    </dl>
    {failed && <div className="mb-6 rounded-xl border border-primary/20 bg-surface p-4">
      <p ref={feedback} role="alert" tabIndex={-1}>You can keep going. We couldn&apos;t save that you&apos;ve seen this.</p>
      <Link href={`/s/${profileId}`} className="inline-flex min-h-11 items-center font-bold text-primary underline rounded-lg focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">Continue to my bookshelf</Link>
    </div>}
    <button disabled={pending} onClick={dismiss} className="w-full min-h-12 rounded-xl bg-primary text-on-primary font-extrabold disabled:opacity-60 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">{pending ? "Saving…" : "Go to my bookshelf"}</button>
    <button disabled={pending} onClick={dismiss} className="w-full min-h-11 mt-3 rounded-xl text-primary font-bold disabled:opacity-60 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">Skip for now</button>
    <form action="/auth/signout" method="post" className="mt-5 text-center"><button className="min-h-11 px-5 font-bold text-primary rounded-lg focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">Log out</button></form>
  </section>;
}
