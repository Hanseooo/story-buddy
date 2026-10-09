import { createSupabaseServerClient } from "@/utils/supabase/server";
import type { RunDetail } from "./types";

export type RunLoad =
  | { kind: "ok"; run: RunDetail }
  | { kind: "signed_out" }
  | { kind: "forbidden"; reason: "not_approved" | "researchers_only" }
  | { kind: "not_found" };

// The backend decides access (ADR-064 rule 2). This only turns its answer into a page state.
export async function loadRun(jobId: string): Promise<RunLoad> {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (!session) return { kind: "signed_out" };

  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/research/runs/${encodeURIComponent(jobId)}`, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: "no-store",
  });
  if (res.ok) return { kind: "ok", run: (await res.json()) as RunDetail };
  if (res.status === 401) return { kind: "signed_out" };
  if (res.status === 403) {
    const body = await res.json().catch(() => null);
    return { kind: "forbidden", reason: body?.detail === "not_approved" ? "not_approved" : "researchers_only" };
  }
  // 422 is a malformed id in the URL. To a reader that is a run that does not exist.
  if (res.status === 404 || res.status === 422) return { kind: "not_found" };
  throw new Error(`Run viewer backend answered ${res.status}`);
}
