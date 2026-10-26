import { redirect } from "next/navigation";
import { getStudentProfile } from "@/utils/supabase/student";
import PasswordForm from "./PasswordForm";

export default async function ChangePasswordPage({ params }: { params: Promise<{ profileId: string }> }) {
  const { profileId } = await params;
  const profile = await getStudentProfile(profileId);
  if (!profile || profile.role !== "student" || profile.removed_at || !profile.classroom_id) throw new Error("Account unavailable");
  const reset = profile.password_reset_version, completed = profile.password_completed_version;
  if (!Number.isSafeInteger(reset) || !Number.isSafeInteger(completed) || completed < 0 || reset < completed) throw new Error("Account state unavailable");
  if (reset === completed) redirect(`/s/${profileId}${completed > 0 && !profile.introduction_dismissed_at ? "/introduction" : ""}`);
  return <PasswordForm profileId={profileId} displayNickname={profile.display_nickname} />;
}
