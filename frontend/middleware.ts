import { NextRequest, NextResponse } from "next/server";
import { createSupabaseMiddlewareClient } from "@/utils/supabase/middleware";
import { safe } from "@/lib/safe-redirect";

// ponytail: exported for unit tests — avoids Edge runtime in jsdom
export function guardRequest(
  pathname: string,
  userId: string | null
): string | null {
  if (pathname.startsWith("/s/")) {
    if (!userId) return `/join?next=${safe(pathname) ?? ""}`;
    const profileId = pathname.split("/")[2];
    if (profileId !== userId) return `/s/${userId}`;
  }
  if (
    (pathname.startsWith("/classroom") || pathname === "/settings") &&
    !userId
  )
    return `/login?next=${safe(pathname) ?? ""}`;
  if (userId && pathname.startsWith("/join")) return `/s/${userId}`;
  if (userId && (pathname === "/login" || pathname === "/signup"))
    return "/classroom";
  return null;
}

export async function middleware(request: NextRequest) {
  const { supabase, response } = await createSupabaseMiddlewareClient(request);
  // ponytail: getUser() not getSession() — verifies token with GoTrue (spec §4)
  // upgrade path: getClaims() + asymmetric JWT signing keys removes this round-trip (spec §4, open)
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  // Fail closed: error or missing user → treat as unauthenticated (spec §4)
  const userId = error || !user ? null : user.id;
  const redir = guardRequest(request.nextUrl.pathname, userId);
  if (redir) return NextResponse.redirect(new URL(redir, request.url));
  return response;
}

export const config = {
  matcher: [
    "/s/:path*",
    "/classroom/:path*",
    "/classroom",
    "/settings",
    "/login",
    "/signup",
    "/join",
    "/join/:path*",
  ],
};
