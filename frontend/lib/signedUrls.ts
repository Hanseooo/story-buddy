"use client";

import { supabase } from "@/lib/supabaseClient";

const BUCKET = "storybook-images";
const TTL = 3600;
// Re-sign 5 min early so a URL handed out here is never about to expire mid-render.
const SKEW_MS = 300_000;
const KEY = "sb:signed";

type Entry = { url: string; exp: number };

function load(): Record<string, Entry> {
  try {
    return JSON.parse(sessionStorage.getItem(KEY) ?? "{}") as Record<string, Entry>;
  } catch {
    return {};
  }
}

function save(cache: Record<string, Entry>) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(cache));
  } catch {
    // ponytail: quota or private-mode failure just means no cache, never a broken page
  }
}

/**
 * Sign `paths`, reusing any still-fresh URL from sessionStorage.
 *
 * Supabase mints a fresh token per call, so re-signing the same path yields a
 * *different* URL for byte-identical content — every navigation was a guaranteed
 * browser cache miss. Caching the URL is what makes the image cacheable.
 *
 * Returns a path -> url map. A path is absent if signing failed; callers decide
 * whether that is fatal.
 */
export async function signPaths(paths: string[]): Promise<Record<string, string>> {
  const cache = load();
  const now = Date.now();
  const out: Record<string, string> = {};
  const missing: string[] = [];

  for (const p of new Set(paths)) {
    const hit = cache[p];
    if (hit && hit.exp > now) out[p] = hit.url;
    else missing.push(p);
  }

  if (missing.length > 0) {
    const { data } = await supabase.storage.from(BUCKET).createSignedUrls(missing, TTL);
    (data ?? []).forEach((s, i) => {
      // Supabase echoes `path`, but results come back in request order either way.
      const path = s.path ?? missing[i];
      if (path && s.signedUrl && !s.error) {
        out[path] = s.signedUrl;
        cache[path] = { url: s.signedUrl, exp: now + TTL * 1000 - SKEW_MS };
      }
    });
    save(cache);
  }

  return out;
}
