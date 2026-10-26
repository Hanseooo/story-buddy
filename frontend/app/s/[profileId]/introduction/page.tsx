import { redirect } from "next/navigation";
import { getStudentProfile } from "@/utils/supabase/student";
import Introduction from "./Introduction";

export default async function IntroductionPage({ params }: { params: Promise<{ profileId: string }> }) {
  const { profileId } = await params;
  const profile = await getStudentProfile(profileId);
  if (!profile || profile.role !== "student" || profile.removed_at || !profile.classroom_id) throw new Error("Account unavailable");
  const reset = profile.password_reset_version, completed = profile.password_completed_version;
  if (!Number.isSafeInteger(reset) || !Number.isSafeInteger(completed) || completed < 0 || reset < completed) throw new Error("Account state unavailable");
  if (completed < reset) redirect(`/s/${profileId}/change-password`);
  if (completed === 0 || profile.introduction_dismissed_at) redirect(`/s/${profileId}`);
  return <Introduction profileId={profileId} />;
}
