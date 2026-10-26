import { NextRequest, NextResponse } from "next/server";
import { createSupabaseMiddlewareClient } from "@/utils/supabase/middleware";
import { safe } from "@/lib/safe-redirect";

export function guardOnboarding(pathname: string, userId: string, profile: {
  role: string; password_reset_version?: number; password_completed_version?: number;
} | null): string | null {
  if (profile?.role === "teacher" || profile?.role === "researcher") return null;
  const reset = profile?.password_reset_version;
  const completed = profile?.password_completed_version;
  const valid = profile?.role === "student" && Number.isSafeInteger(reset) && Number.isSafeInteger(completed)
    && completed! >= 0 && reset! >= completed!;
  const required = `/s/${userId}/change-password`;
  if ((!valid || completed! < reset!) && pathname !== required) return required;
  return null;
}

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
    (pathname.startsWith("/classroom") ||
      pathname === "/settings" ||
      pathname.startsWith("/annotate") ||
      pathname.startsWith("/adjudicate") ||
      pathname.startsWith("/research/metrics/")) &&
    !userId
  )
    return `/login?next=${safe(pathname) ?? ""}`;
  if (userId && pathname === "/") return "/classroom";
  if (userId && pathname.startsWith("/join")) return `/s/${userId}`;
  if (userId && (pathname === "/login" || pathname === "/signup"))
    return "/classroom";
  return null;
}

export async function middleware(request: NextRequest) {
  const client = await createSupabaseMiddlewareClient(request);
  const { supabase } = client;
  // ponytail: getUser() not getSession() — verifies token with GoTrue (spec §4)
  // upgrade path: getClaims() + asymmetric JWT signing keys removes this round-trip (spec §4, open)
  const {
    data: { user },
    error,
  } = await supabase.auth.getUser();
  // Fail closed: error or missing user → treat as unauthenticated (spec §4)
  const userId = error || !user ? null : user.id;
  let onboardingRedirect: string | null = null;
  if (userId) {
    const { data, error: profileError } = await supabase.from("profiles")
      .select("role, password_reset_version, password_completed_version").eq("id", userId).single();
    onboardingRedirect = guardOnboarding(request.nextUrl.pathname, userId, profileError ? null : data);
  }
  const redir = onboardingRedirect ?? guardRequest(request.nextUrl.pathname, userId);
  if (redir) {
    const response = NextResponse.redirect(new URL(redir, request.url));
    client.response.cookies.getAll().forEach((cookie) => response.cookies.set(cookie));
    return response;
  }
  return client.response;
}

export const config = {
  matcher: [
    "/",
    "/s/:path*",
    "/classroom/:path*",
    "/classroom",
    "/settings",
    "/login",
    "/signup",
    "/join",
    "/join/:path*",
    "/annotate",
    "/annotate/:path*",
    "/adjudicate",
    "/adjudicate/:path*",
    "/research/metrics",
    "/research/metrics/:path*",
  ],
};
