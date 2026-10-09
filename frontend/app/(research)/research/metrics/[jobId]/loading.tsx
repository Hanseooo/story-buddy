export default function RunLoading() {
  return (
    <div aria-busy="true" aria-label="Loading run" className="mx-auto max-w-7xl animate-pulse space-y-8 p-5 sm:p-8 lg:p-12">
      <div className="space-y-3">
        <div className="h-11 w-28 rounded-xl bg-muted/60" />
        <div className="h-10 w-72 max-w-full rounded-xl bg-muted" />
        <div className="h-4 w-56 rounded-lg bg-muted/60" />
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-24 rounded-2xl bg-surface neo-border" />
        ))}
      </div>
      <div className="h-[420px] rounded-3xl bg-surface neo-border" />
      {[...Array(2)].map((_, i) => (
        <div key={i} className="h-72 rounded-3xl bg-surface neo-border" />
      ))}
    </div>
  );
}
