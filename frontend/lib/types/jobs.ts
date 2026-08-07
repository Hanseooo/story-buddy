export type JobPage = {
  scene_id: string;
  caption: string;
  image_path: string; // relative Storage path, e.g. "{job_id}/{scene_id}.png"
};

export type Job = {
  id: string;
  status: string;
  failure_reason: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  created_at: string;
  input_text: string;
  pages: JobPage[] | null;
  profile_id: string;
  profiles: { display_nickname: string };
};

export type ReviewDecision = "approved" | "rejected" | "pending";

export function jobState(job: Job): ReviewDecision {
  if (job.approved_at !== null) return "approved";
  if (job.rejected_at !== null) return "rejected";
  return "pending";
}
