import Link from "next/link";
import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";
import ResearchHeader from "../../_shared/components/ResearchHeader";

// Static on purpose (ADR-065): no session read, so these pages work with Supabase down or paused.
export default function ReferenceLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[100dvh] bg-background text-foreground">
      <ResearchHeader viewer={null} showAccount={false} />
      <div className="mx-auto max-w-5xl p-4 font-sans sm:p-6 lg:p-10">
        <Link
          href="/research"
          className="inline-flex min-h-11 items-center gap-2 rounded-xl px-2 text-sm font-bold text-foreground/70 hover:text-foreground focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
        >
          <ArrowLeft weight="bold" className="size-4" aria-hidden />
          Back to Methodology
        </Link>
        {children}
      </div>
    </div>
  );
}
