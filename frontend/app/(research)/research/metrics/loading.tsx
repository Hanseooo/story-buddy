export default function MetricsLoading() {
  return (
    <div aria-busy="true" aria-label="Loading runs" className="mx-auto max-w-7xl animate-pulse space-y-8 p-4 sm:p-6 lg:space-y-10 lg:p-10">
      <div className="flex flex-col gap-3">
        <div className="h-10 w-40 rounded-xl bg-muted md:h-12" />
        <div className="h-5 w-full max-w-[65ch] rounded-lg bg-muted/60" />
      </div>
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-3">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="min-h-[132px] rounded-3xl bg-surface p-5 neo-border">
            <div className="h-3 w-20 rounded-full bg-muted" />
            <div className="mt-4 h-8 w-24 rounded-xl bg-muted" />
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-2">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-11 w-24 rounded-full bg-muted" />
        ))}
      </div>
      <div className="hidden overflow-hidden rounded-3xl bg-surface neo-border md:block">
        <div className="h-12 border-b border-muted bg-muted/20" />
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-[72px] border-b border-muted/40 last:border-0" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 md:hidden">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-40 rounded-2xl bg-muted/30 neo-border" />
        ))}
      </div>
    </div>
  );
}
