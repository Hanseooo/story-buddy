import { NextRequest, NextResponse } from "next/server";
import { createServerClient } from "@supabase/ssr";

// POST — the "Log out" button in TeacherShell.
// GET  — stale-session recovery: when middleware and the render disagree about
//        the session, the only fix is to drop the cookies. Server Components
//        cannot write cookies; Route Handlers can, so redirects land here.
async function signOut(request: NextRequest) {
  const response = NextResponse.redirect(new URL("/login", request.url), {
    status: 303, // force GET on the follow-up, even when we arrived via POST
  });

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co",
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key",
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            response.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  // Revokes the refresh token server-side. Ignore failures — a session too
  // broken to revoke is exactly the one we most need to clear locally.
  await supabase.auth.signOut().catch(() => {});

  // ponytail: signOut() only clears cookies it can parse, and @supabase/ssr
  // chunks large sessions into sb-<ref>-auth-token.0/.1. Sweep the prefix so a
  // wedged or half-written session cannot survive the round trip — otherwise
  // /login bounces back to /classroom (middleware.ts:21) and we loop again.
  for (const cookie of request.cookies.getAll()) {
    if (cookie.name.startsWith("sb-")) response.cookies.delete(cookie.name);
  }

  return response;
}

export async function POST(request: NextRequest) {
  return signOut(request);
}

export async function GET(request: NextRequest) {
  return signOut(request);
}
