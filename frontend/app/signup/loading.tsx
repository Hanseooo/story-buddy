export default function Loading() {
  return (
    <div className="font-sans min-h-[100dvh] flex flex-col lg:flex-row bg-background text-foreground relative">
      <div className="w-full lg:w-5/12 xl:w-1/2 bg-primary relative flex flex-col p-8 lg:p-16 justify-center overflow-hidden">
        <div className="absolute inset-0 pointer-events-none opacity-20" aria-hidden="true">
          <div className="absolute top-[-10%] right-[-10%] w-64 h-64 rounded-full bg-secondary/30 blur-3xl"></div>
          <div className="absolute bottom-[-10%] left-[-10%] w-80 h-80 rounded-full bg-surface/20 blur-2xl"></div>
        </div>
      </div>
      <div className="w-full lg:w-7/12 xl:w-1/2 flex-1 flex items-center justify-center p-6 lg:p-12 border-t lg:border-t-0 lg:border-l border-primary/10">
        <div className="w-full max-w-md space-y-6">
          <div className="h-10 w-32 animate-pulse rounded-xl bg-muted/50" />
          <div className="h-4 w-64 animate-pulse rounded-md bg-muted/50" />
          <div className="mt-8 space-y-5">
            <div className="space-y-2">
              <div className="h-4 w-24 animate-pulse rounded-md bg-muted/50" />
              <div className="h-11 w-full animate-pulse rounded-xl bg-muted/50" />
            </div>
            <div className="space-y-2">
              <div className="h-4 w-16 animate-pulse rounded-md bg-muted/50" />
              <div className="h-11 w-full animate-pulse rounded-xl bg-muted/50" />
            </div>
            <div className="space-y-2">
              <div className="h-4 w-16 animate-pulse rounded-md bg-muted/50" />
              <div className="h-11 w-full animate-pulse rounded-xl bg-muted/50" />
            </div>
            <div className="mt-4 h-11 w-full animate-pulse rounded-xl bg-primary/20" />
          </div>
        </div>
      </div>
    </div>
  );
}
