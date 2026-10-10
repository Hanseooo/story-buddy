import ResearchHeader from "../_shared/components/ResearchHeader";
import { getResearchViewer } from "../_shared/getResearchViewer";

export default async function AdjudicateLayout({ children }: { children: React.ReactNode }) {
  const viewer = await getResearchViewer();

  if (viewer?.role !== "researcher") {
    throw new Error("Unauthorized");
  }

  return (
    <div className="min-h-[100dvh] bg-background text-foreground flex flex-col selection:bg-primary/20">
      <ResearchHeader viewer={viewer} />
      {children}
    </div>
  );
}
