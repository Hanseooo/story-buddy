import { ArrowLeft } from "@phosphor-icons/react/dist/ssr";

export default function MetricsLoading() {
  return (
    <div className="min-h-[100dvh] bg-background p-4 sm:p-6 lg:p-10 font-sans">
      <div className="mx-auto max-w-7xl space-y-8 lg:space-y-12 animate-pulse">
        
        {/* Header Skeleton */}
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between border-b border-primary/10 pb-4">
            <div className="inline-flex items-center gap-1.5 w-fit">
              <ArrowLeft weight="bold" className="w-4 h-4 text-muted" />
              <div className="h-4 w-32 bg-muted rounded-full" />
            </div>
            
            <div className="flex items-center gap-2">
              <div className="size-7 sm:size-8 rounded-[9px_9px_9px_3px] bg-muted shrink-0" />
              <div className="hidden sm:block h-5 w-24 bg-muted rounded-full" />
            </div>
          </div>

          <div className="flex flex-col gap-3">
            <div className="h-10 md:h-12 w-64 bg-muted rounded-xl" />
            <div className="h-5 w-full max-w-[65ch] bg-muted/60 rounded-lg" />
            <div className="h-10 w-48 mt-2 bg-muted rounded-xl" />
          </div>
        </div>

        {/* Stats Grid Skeleton */}
        <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <div className="rounded-3xl neo-border bg-surface p-5 sm:p-6 flex flex-col justify-between gap-4 min-h-[120px]">
            <div className="h-3 w-16 bg-muted rounded-full" />
            <div className="h-8 w-20 bg-muted rounded-xl" />
          </div>
          <div className="rounded-3xl neo-border bg-surface p-5 sm:p-6 flex flex-col justify-between gap-4 min-h-[120px]">
            <div className="h-3 w-20 bg-muted rounded-full" />
            <div className="h-8 w-24 bg-muted rounded-xl" />
          </div>
          <div className="rounded-3xl neo-border bg-surface p-5 sm:p-6 flex flex-col justify-between gap-4 min-h-[120px]">
            <div className="h-3 w-24 bg-muted rounded-full" />
            <div className="h-8 w-32 bg-muted rounded-xl" />
          </div>
          
          <div className="grid grid-rows-2 gap-3 sm:gap-4">
            <div className="rounded-2xl neo-border bg-surface p-4 flex items-center justify-between h-[56px]">
              <div className="h-3 w-16 bg-muted rounded-full" />
              <div className="h-5 w-8 bg-muted rounded-md" />
            </div>
            <div className="rounded-2xl neo-border bg-surface p-4 flex items-center justify-between h-[56px]">
              <div className="h-3 w-16 bg-muted rounded-full" />
              <div className="h-5 w-8 bg-muted rounded-md" />
            </div>
          </div>
        </div>

        {/* History Skeleton */}
        <div className="space-y-4">
          <div className="h-7 w-40 bg-muted rounded-lg" />

          {/* Desktop Table Skeleton */}
          <div className="hidden md:block overflow-hidden rounded-3xl neo-border bg-surface">
            <div className="h-12 border-b border-muted bg-muted/20" />
            <div className="divide-y divide-muted/40">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="h-[72px] px-6 py-4 flex items-center gap-6">
                  <div className="h-4 w-20 bg-muted/60 rounded flex-1" />
                  <div className="h-6 w-16 bg-muted/60 rounded-full flex-1" />
                  <div className="h-4 w-24 bg-muted/60 rounded flex-1" />
                  <div className="h-4 w-16 bg-muted/60 rounded flex-1" />
                  <div className="h-4 w-12 bg-muted/60 rounded flex-1" />
                  <div className="h-4 w-12 bg-muted/60 rounded flex-1" />
                  <div className="h-4 w-16 bg-muted/60 rounded flex-1" />
                  <div className="h-4 w-12 bg-muted/60 rounded flex-1" />
                </div>
              ))}
            </div>
          </div>

          {/* Mobile Cards Skeleton */}
          <div className="grid grid-cols-1 gap-4 md:hidden">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="rounded-2xl neo-border bg-surface p-5 h-40 bg-muted/30" />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
