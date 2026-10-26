// Who is looking at a research page. `null` means signed out. Pure: safe to import from client code.
export type ResearchViewer = {
  id: string;
  role: string | null;
  isAdjudicator: boolean;
  displayName: string | null;
};

// One rule for title visibility and the link. The backend independently enforces ADR-079.
export function canOpenRun(viewer: ResearchViewer | null): boolean {
  return viewer?.role === "researcher";
}

export function hideTitles<T extends { title?: string | null }>(
  viewer: ResearchViewer | null,
  jobs: T[]
): T[] {
  return jobs.map((job) => (canOpenRun(viewer) ? job : { ...job, title: null }));
}
