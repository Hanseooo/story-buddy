import { cache } from "react";
import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "./server";

export type Classroom = { id: string; name: string; code: string };

export type TeacherContext = {
  profile: { id: string; role: string; display_name: string | null; is_adjudicator?: boolean | null };
  classrooms: Classroom[];
};

// ponytail: cache() dedupes this across the layout and the page in one request —
// three remote round trips total, not six. Client pages under /classroom must
// receive this as props rather than refetching it.
export const getTeacherContext = cache(async (): Promise<TeacherContext> => {
  const supabase = await createSupabaseServerClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();
  // Middleware (middleware.ts:16) already sent anonymous traffic to /login, so
  // reaching here without a user means the guard and the render disagree — the
  // cookies are wedged. /login would bounce straight back (middleware.ts:21)
  // and spin forever; the signout handler clears the cookies first, so the
  // /login it lands on sees an anonymous user and stays put.
  if (!user) redirect("/auth/signout");

  const [profileRes, classroomsRes] = await Promise.all([
    supabase
      .from("profiles")
      .select("id, role, display_name, is_adjudicator")
      .eq("id", user.id)
      .single(),
    supabase
      .from("classrooms")
      .select("id, name, code")
      .eq("owner_id", user.id)
      .order("created_at"),
  ]);

  const profile = profileRes.data;
  // A signed-in user with no profiles row is a server-side data fault (missing
  // signup trigger, RLS denial, absent table), not a wedged session — signing
  // them out would just loop them back here. Surface the Postgres error:
  // without it "row absent", "RLS denied" and "no such table" look identical.
  if (!profile)
    throw new Error(
      `no profiles row for authenticated user ${user.id} — ` +
        (profileRes.error
          ? `${profileRes.error.code}: ${profileRes.error.message}`
          : "query returned no row and no error")
    );

  if (profile.role !== "teacher") redirect(`/s/${profile.id}`);

  return { profile, classrooms: classroomsRes.data ?? [] };
});
