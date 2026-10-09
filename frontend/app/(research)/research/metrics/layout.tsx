import ResearchHeader from "../../_shared/components/ResearchHeader";
import { getResearchViewer } from "../../_shared/getResearchViewer";

export default async function MetricsLayout({ children }: { children: React.ReactNode }) {
  const viewer = await getResearchViewer();

  return (
    <div className="min-h-[100dvh] bg-background text-foreground">
      <ResearchHeader viewer={viewer} />
      {children}
    </div>
  );
}
