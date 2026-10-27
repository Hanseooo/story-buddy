"use client";

import { supabase } from "@/lib/supabaseClient";

const BUCKET = "storybook-images";
const TTL = 3600;
// Re-sign 5 min early so a URL handed out here is never about to expire mid-render.
const SKEW_MS = 300_000;
const KEY = "sb:signed";

type Entry = { url: string; exp: number };
export type ImageJob = {
  id: string;
  moderation_mode?: string;
  pages?: Array<{scene_id: string; image_path: string}> | null;
  reveal?: {characters?: Array<{char_id: string; image_path: string}>} | null;
};

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
export async function signPaths(paths: string[], jobs: ImageJob[] = [], signal?: AbortSignal): Promise<Record<string, string>> {
  const cache = load();
  const now = Date.now();
  const out: Record<string, string> = {};
  const missing: string[] = [];
  const protectedPaths = new Map<string, {jobId: string; assetId: string}>();
  for (const job of jobs) {
    if (job.moderation_mode !== "teacher_review_v1") continue;
    for (const page of job.pages ?? []) protectedPaths.set(page.image_path, {jobId: job.id, assetId: `scene-${page.scene_id}`});
    for (const char of job.reveal?.characters ?? []) protectedPaths.set(char.image_path, {jobId: job.id, assetId: `ref-${char.char_id}`});
  }

  for (const p of new Set(paths)) {
    // No cached Storage link, signing request or sessionStorage blob for feature jobs.
    const selected = protectedPaths.get(p);
    if (selected) {
      delete cache[p];
      if (!signal || signal.aborted) continue;
      try {
        const { data: { session } } = await supabase.auth.getSession();
        if (!session || signal.aborted) continue;
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${selected.jobId}/images/${encodeURIComponent(selected.assetId)}`, {
          headers: {Authorization: `Bearer ${session.access_token}`}, cache: "no-store", signal,
        });
        if (!response.ok) continue;
        const bytes = await response.blob();
        if (signal.aborted) continue;
        const url = URL.createObjectURL(bytes);
        signal.addEventListener("abort", () => URL.revokeObjectURL(url), {once: true});
        out[p] = url;
      } catch { /* Caller retains its established image error/retry state. */ }
      continue;
    }
    if (jobs.some(j => j.moderation_mode === "teacher_review_v1" && p.startsWith(`${j.id}/`))) continue;
    const hit = cache[p];
    if (hit && hit.exp > now) out[p] = hit.url;
    else missing.push(p);
  }

  save(cache);

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
