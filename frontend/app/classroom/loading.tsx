// Without this file /classroom has no Suspense boundary, so the browser holds
// the previous page (or blank on a fresh load) for the whole server render —
// ~750ms against hosted Supabase. This is the boundary that lets Next stream.
export default function Loading() {
  return (
    <div className="p-6 sm:p-10 max-w-7xl mx-auto w-full min-h-[calc(100vh-80px)]">
      <div className="mb-10">
        <div className="h-10 w-48 sm:h-12 sm:w-64 animate-pulse rounded-xl bg-muted/50" />
        <div className="mt-4 h-6 w-64 animate-pulse rounded-md bg-muted/50" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-[minmax(200px,auto)] pb-20">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex min-h-[200px] flex-col justify-between rounded-[28px] border-2 border-primary/10 bg-surface p-6 sm:p-10">
            <div>
              <div className="mb-5 h-12 w-12 animate-pulse rounded-2xl bg-muted/50" />
              <div className="mb-2 h-8 w-3/4 animate-pulse rounded-lg bg-muted/50" />
              <div className="h-6 w-1/3 animate-pulse rounded-md bg-muted/50" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
