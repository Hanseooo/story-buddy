"use client";

import { useEffect } from "react";
import { supabase } from "@/lib/supabaseClient";

const PREFIX = "sb.stopped.";

export type SavedWriting = { text: string; title: string };
export const stoppedWritingKey = (profileId: string, jobId: string) => `${PREFIX}${profileId}.${jobId}`;

export function clearStoppedWriting() {
  try {
    for (const key of Object.keys(sessionStorage)) if (key.startsWith(PREFIX)) sessionStorage.removeItem(key);
  } catch { /* unavailable storage cannot retain a new handoff */ }
}

export function saveStoppedWriting(profileId: string, jobId: string, writing: SavedWriting) {
  sessionStorage.setItem(stoppedWritingKey(profileId, jobId), JSON.stringify(writing));
}
// Root-mounted so cleanup is restored after reload and remains on Profile/login pages.
export default function StoppedWritingCleanup() {
  useEffect(() => {
    let request: AbortController | null = null;
    async function checkAccess() {
      request?.abort();
      const controller = new AbortController();
      request = controller;
      try {
        const keys = Object.keys(sessionStorage).filter(key => key.startsWith(PREFIX));
        if (!keys.length) return;
        const { data: { session } } = await supabase.auth.getSession();
        if (controller.signal.aborted) return;
        if (!session) { clearStoppedWriting(); return; }
        for (const key of keys) {
          const ownerPrefix = `${PREFIX}${session.user.id}.`;
          if (!key.startsWith(ownerPrefix)) { sessionStorage.removeItem(key); continue; }
          const jobId = key.slice(ownerPrefix.length);
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${encodeURIComponent(jobId)}/state`, {
            headers: { Authorization: `Bearer ${session.access_token}` }, cache: "no-store", signal: controller.signal,
          });
          if ([401, 403, 404].includes(response.status)) sessionStorage.removeItem(key);
        }
      } catch { /* A transient read failure does not discard a recoverable draft. */ }
    }
    const visibility = () => { if (!document.hidden) void checkAccess(); };
    const signout = (event: Event) => {
      if (event.target instanceof HTMLFormElement && new URL(event.target.action).pathname === "/auth/signout") clearStoppedWriting();
    };
    document.addEventListener("submit", signout, true);
    document.addEventListener("visibilitychange", visibility);
    const { data: { subscription } } = supabase.auth.onAuthStateChange(event => {
      if (event === "SIGNED_OUT") { request?.abort(); clearStoppedWriting(); }
    });
    void checkAccess();
    return () => {
      request?.abort(); subscription.unsubscribe();
      document.removeEventListener("submit", signout, true);
      document.removeEventListener("visibilitychange", visibility);
    };
  }, []);
  return null;
}
