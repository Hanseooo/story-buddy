"use client";

import { supabase } from "@/lib/supabaseClient";

const BUCKET = "storybook-images";
const TTL = 3600;
// Re-sign 5 min early so a URL handed out here is never about to expire mid-render.
const SKEW_MS = 300_000;
const KEY = "sb:signed";

type Entry = { url: string; exp: number };
type ProtectedAsset = {jobId: string; assetId: string};
type OnUrl = (path: string, url: string) => void;
export type ImageJob = {
  id: string;
  moderation_mode?: string;
  pages?: Array<{scene_id: string; image_path: string}> | null;
  reveal?: {characters?: Array<{char_id: string; image_path: string; versions?: Array<{version_id: string; image_path: string}>}>} | null;
  page_versions?: Array<{version_id: string; image_path: string}>;
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

// Per call, never shared across calls (image-loading spec §5.6, an assumed value).
const CONCURRENCY = 4;

async function fetchProtected(work: Array<[string, ProtectedAsset]>, out: Record<string, string>, signal: AbortSignal, onUrl?: OnUrl) {
  let session;
  try {
    ({ data: { session } } = await supabase.auth.getSession());
  } catch {
    return;
  }
  if (!session || signal.aborted) return;
  const token = session.access_token;
  let next = 0;
  const worker = async () => {
    // Each worker takes the next item synchronously, so requests start in path order.
    while (next < work.length) {
      const [p, selected] = work[next++];
      if (signal.aborted) return;
      try {
        // ADR-085: `v` names the exact picture, so the browser may keep it for an hour (the
        // backend sends max-age=3600). A withdrawn book stays visible here until it expires.
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${selected.jobId}/images/${encodeURIComponent(selected.assetId)}?v=${encodeURIComponent(p)}`, {
          headers: {Authorization: `Bearer ${token}`}, cache: "default", signal,
        });
        if (!response.ok) continue;
        const bytes = await response.blob();
        // A listener added after the abort never fires, so a late blob gets no URL at all (SH-02).
        if (signal.aborted) continue;
        const url = URL.createObjectURL(bytes);
        signal.addEventListener("abort", () => URL.revokeObjectURL(url), {once: true});
        out[p] = url;
        onUrl?.(p, url);
      } catch { /* Caller retains its established image error/retry state. */ }
    }
  };
  await Promise.all(Array.from({length: Math.min(CONCURRENCY, work.length)}, worker));
}

/**
 * Sign `paths`, reusing any still-fresh URL from sessionStorage.
 *
 * Supabase mints a fresh token per call, so re-signing the same path yields a
 * *different* URL for byte-identical content — every navigation was a guaranteed
 * browser cache miss. Caching the URL is what makes the image cacheable.
 *
 * Returns a path -> url map. A path is absent if signing failed; callers decide
 * whether that is fatal. `onUrl` receives each URL as soon as it is available,
 * before the call resolves, so callers can show pictures one by one.
 */
export async function signPaths(paths: string[], jobs: ImageJob[] = [], signal?: AbortSignal, onUrl?: OnUrl): Promise<Record<string, string>> {
  const cache = load();
  const now = Date.now();
  const out: Record<string, string> = {};
  const missing: string[] = [];
  const protectedPaths = new Map<string, ProtectedAsset>();
  for (const job of jobs) {
    if (job.moderation_mode !== "teacher_review_v1") continue;
    for (const page of job.pages ?? []) protectedPaths.set(page.image_path, {jobId: job.id, assetId: `scene-${page.scene_id}`});
    for (const char of job.reveal?.characters ?? []) {
      protectedPaths.set(char.image_path, {jobId: job.id, assetId: `ref-${char.char_id}`});
      for (const v of char.versions ?? []) protectedPaths.set(v.image_path, {jobId: job.id, assetId: `version-${v.version_id}`});
    }
    for (const v of job.page_versions ?? []) protectedPaths.set(v.image_path, {jobId: job.id, assetId: `page-version-${v.version_id}`});
  }

  const work: Array<[string, ProtectedAsset]> = [];
  for (const p of new Set(paths)) {
    // No cached Storage link, signing request or sessionStorage blob for feature jobs.
    const selected = protectedPaths.get(p);
    if (selected) {
      delete cache[p];
      if (signal && !signal.aborted) work.push([p, selected]);
      continue;
    }
    if (jobs.some(j => j.moderation_mode === "teacher_review_v1" && p.startsWith(`${j.id}/`))) continue;
    const hit = cache[p];
    if (hit && hit.exp > now) {
      out[p] = hit.url;
      onUrl?.(p, hit.url);
    } else missing.push(p);
  }

  // Protected paths only delete cache entries, so the cache can be saved before they download.
  save(cache);

  // Baseline links do not wait for protected downloads, so a mixed shelf fills in sooner.
  // allSettled: a signing error rejects only after every download has delivered or failed.
  const results = await Promise.allSettled([
    work.length > 0 && signal ? fetchProtected(work, out, signal, onUrl) : undefined,
    signMissing(),
  ]);
  for (const r of results) if (r.status === "rejected") throw r.reason;
  return out;

  async function signMissing() {
    if (missing.length === 0) return;
    const { data } = await supabase.storage.from(BUCKET).createSignedUrls(missing, TTL);
    (data ?? []).forEach((s, i) => {
      // Supabase echoes `path`, but results come back in request order either way.
      const path = s.path ?? missing[i];
      if (path && s.signedUrl && !s.error) {
        out[path] = s.signedUrl;
        onUrl?.(path, s.signedUrl);
        cache[path] = { url: s.signedUrl, exp: now + TTL * 1000 - SKEW_MS };
      }
    });
    save(cache);
  }
}
