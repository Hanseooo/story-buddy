export default function Loading() {
  return (
    <div className="w-full flex flex-col flex-1">
      {/* Header Skeleton */}
      <header className="sticky top-0 z-30 bg-surface/90 backdrop-blur-md border-b border-admin/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="h-8 w-28 rounded-xl bg-muted/60 animate-pulse" />
            <div className="h-4 w-px bg-admin/20 hidden sm:block" />
            <div className="h-6 w-40 rounded-md bg-muted/60 animate-pulse" />
          </div>
          <div className="flex items-center gap-3">
            <div className="h-8 w-32 rounded-xl bg-muted/60 animate-pulse" />
            <div className="h-8 w-24 rounded-xl bg-muted/60 animate-pulse" />
          </div>
        </div>
      </header>

      {/* Main Content Skeleton */}
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8 flex-1 flex flex-col gap-6">
        {/* Conflict Summary Skeleton */}
        <div className="bg-surface rounded-2xl neo-border p-4 md:p-5 flex flex-col gap-3">
          <div className="flex items-center justify-between border-b border-primary/10 pb-2.5">
            <div className="h-5 w-40 rounded bg-muted/60 animate-pulse" />
            <div className="h-4 w-48 rounded bg-muted/40 animate-pulse" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="h-16 rounded-xl bg-muted/40 animate-pulse" />
            <div className="h-16 rounded-xl bg-muted/40 animate-pulse" />
            <div className="h-16 rounded-xl bg-muted/40 animate-pulse" />
            <div className="h-16 rounded-xl bg-muted/40 animate-pulse" />
          </div>
        </div>

        {/* Visual Inspection + Decision Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start flex-1">
          {/* Image Cards Skeleton (7 cols) */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="h-6 w-44 rounded-md bg-muted/60 animate-pulse" />
              <div className="h-6 w-24 rounded-md bg-muted/60 animate-pulse" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-5">
              <div className="bg-surface rounded-2xl neo-border p-4 flex flex-col gap-3">
                <div className="h-5 w-36 rounded bg-muted/60 animate-pulse" />
                <div className="aspect-square w-full bg-muted/40 rounded-xl animate-shimmer" />
                <div className="h-4 w-48 rounded bg-muted/40 animate-pulse mx-auto" />
              </div>
              <div className="bg-surface rounded-2xl neo-border p-4 flex flex-col gap-3">
                <div className="h-5 w-36 rounded bg-muted/60 animate-pulse" />
                <div className="aspect-square w-full bg-muted/40 rounded-xl animate-shimmer" />
                <div className="h-4 w-48 rounded bg-muted/40 animate-pulse mx-auto" />
              </div>
            </div>
          </div>

          {/* Control Panel Skeleton (5 cols) */}
          <div className="lg:col-span-5 flex flex-col h-full">
            <div className="bg-surface rounded-2xl neo-border p-5 md:p-6 flex flex-col gap-6 min-h-[500px]">
              <div className="space-y-2 border-b border-primary/10 pb-3">
                <div className="h-6 w-44 rounded bg-muted/60 animate-pulse" />
                <div className="h-4 w-64 rounded bg-muted/40 animate-pulse" />
              </div>
              <div className="space-y-3">
                <div className="h-14 w-full rounded-xl bg-muted/40 animate-pulse" />
                <div className="h-14 w-full rounded-xl bg-muted/40 animate-pulse" />
              </div>
              <div className="space-y-2 mt-auto pt-3 border-t border-primary/10">
                <div className="h-10 w-full rounded-xl bg-muted/40 animate-pulse" />
                <div className="h-12 w-full rounded-xl bg-muted/60 animate-pulse" />
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
