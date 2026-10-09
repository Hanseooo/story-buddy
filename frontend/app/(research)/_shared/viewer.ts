// Who is looking at a research page. `null` means signed out. Pure: safe to import from client code.
export type ResearchViewer = {
  id: string;
  role: string | null;
  isAdjudicator: boolean;
  displayName: string | null;
};
