// Who is looking at a research page. `null` means signed out. Pure: safe to import from client code.
export type ResearchViewer = {
  id: string;
  role: string | null;
  isAdjudicator: boolean;
  displayName: string | null;
};

// One rule for title visibility and the link. The backend independently enforces ADR-064 rule 2.
export function canOpenRun(viewer: ResearchViewer | null, job: { approved_at?: string | null }): boolean {
  return viewer?.role === "researcher" && (viewer.isAdjudicator || job.approved_at != null);
}

export function hideTitles<T extends { title?: string | null; approved_at?: string | null }>(
  viewer: ResearchViewer | null,
  jobs: T[]
): T[] {
  return jobs.map((job) => (canOpenRun(viewer, job) ? job : { ...job, title: null }));
}
