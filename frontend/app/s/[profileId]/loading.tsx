export default function Loading() {
  return (
    <main className="font-kid p-6 sm:p-10 max-w-7xl mx-auto min-h-[calc(100vh-80px)] flex flex-col">
      <div className="flex items-center justify-between mb-8 sm:mb-12">
        <div className="h-10 w-48 sm:h-12 sm:w-64 animate-pulse rounded-xl bg-muted/50" />
        <div className="hidden sm:inline-flex min-h-[48px] w-40 animate-pulse rounded-xl bg-muted/50" />
      </div>
      <div className="grid grid-cols-2 gap-6 pb-20 sm:grid-cols-3 sm:gap-8 md:grid-cols-4 lg:grid-cols-5 lg:gap-10">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="relative">
            <div className="block overflow-hidden rounded-[20px] border-2 border-primary/10 bg-surface sm:rounded-[24px]">
              <div className="aspect-[4/5] w-full animate-pulse bg-muted/50" />
              <div className="border-t-2 border-primary/5 bg-surface p-4 sm:p-5">
                <div className="h-5 w-3/4 animate-pulse rounded-md bg-muted/50" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
