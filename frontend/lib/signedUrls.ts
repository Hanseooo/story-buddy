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

// ADR-086: one backend call per teacher-review job returns links it signed for exactly the authorized
// paths. Each link is a bearer grant for up to an hour, cached like an older book's link.
async function fetchLinks(byJob: Map<string, Map<string, Set<string>>>, out: Record<string, string>,
  cache: Record<string, Entry>, now: number, signal?: AbortSignal, onUrl?: OnUrl) {
  let session;
  try {
    ({ data: { session } } = await supabase.auth.getSession());
  } catch {
    return;
  }
  if (!session || signal?.aborted) return;
  const token = session.access_token;
  await Promise.all([...byJob].map(async ([jobId, assets]) => {
    try {
      const query = new URLSearchParams([...assets.keys()].map(a => ["asset", a]));
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/image-links?${query}`, {
        headers: {Authorization: `Bearer ${token}`}, signal,
      });
      if (!response.ok) return;
      const {links} = await response.json() as {links: Array<{asset_id: string; path: string; url: string}>};
      if (signal?.aborted) return;
      for (const {asset_id, path, url} of links) {
        // Accept only a path this call asked for under that asset.
        if (!url || !assets.get(asset_id)?.has(path)) continue;
        out[path] = url;
        cache[path] = { url, exp: now + TTL * 1000 - SKEW_MS };
        onUrl?.(path, url);
      }
      save(cache);
    } catch { /* Caller retains its established image error/retry state. */ }
  }));
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

  const byJob = new Map<string, Map<string, Set<string>>>();
  for (const p of new Set(paths)) {
    const selected = protectedPaths.get(p);
    // Other paths in a teacher-review job are never signed: only the backend signs there (ADR-080, ADR-086).
    if (!selected && jobs.some(j => j.moderation_mode === "teacher_review_v1" && p.startsWith(`${j.id}/`))) continue;
    const hit = cache[p];
    if (hit && hit.exp > now) {
      out[p] = hit.url;
      onUrl?.(p, hit.url);
    } else if (selected) {
      if (signal?.aborted) continue;
      const assets = byJob.get(selected.jobId) ?? new Map<string, Set<string>>();
      assets.set(selected.assetId, (assets.get(selected.assetId) ?? new Set()).add(p));
      byJob.set(selected.jobId, assets);
    } else missing.push(p);
  }

  // Baseline links do not wait for teacher-review links, so a mixed shelf fills in sooner.
  // allSettled: a signing error rejects only after every book's links have delivered or failed.
  const results = await Promise.allSettled([
    byJob.size > 0 ? fetchLinks(byJob, out, cache, now, signal, onUrl) : undefined,
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
