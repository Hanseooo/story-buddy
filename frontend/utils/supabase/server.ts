import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";

export async function createSupabaseServerClient() {
  const cookieStore = await cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          // ponytail: Server Components cannot write cookies — next/headers
          // throws ReadonlyRequestCookiesError unless the request phase is
          // "action". Middleware owns token refresh and writes the rotated
          // cookies onto its own response, so dropping them here is correct,
          // not a swallowed bug. Letting this throw makes getUser() return no
          // user mid-render, which used to bounce /classroom into an infinite
          // 307 loop against the middleware guard.
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            );
          } catch {
            // Route Handlers and Server Actions reach the same code path and
            // *can* write; only the read-only render phase lands here.
          }
        },
      },
    }
  );
}
