export default function WelcomeLoading() {
  return (
    <div className="font-sans min-h-[100dvh] bg-background text-foreground flex items-center justify-center p-6 sm:p-12">
      <div className="w-full max-w-4xl mx-auto flex flex-col items-center">
        {/* Logo and title placeholder */}
        <div className="mb-6 size-16 rounded-2xl bg-surface border border-primary/10 animate-pulse" />
        <div className="h-10 w-64 rounded-xl bg-primary/10 animate-pulse mb-3" />
        <div className="h-5 w-80 rounded-lg bg-foreground/10 animate-pulse mb-10" />

        {/* 2-card grid placeholder */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl">
          <div className="h-72 rounded-[24px] bg-surface border border-primary/10 p-7 animate-pulse flex flex-col justify-between">
            <div>
              <div className="size-14 rounded-2xl bg-primary/10 mb-6" />
              <div className="h-7 w-36 rounded-lg bg-primary/15 mb-3" />
              <div className="h-4 w-full rounded bg-foreground/10 mb-2" />
              <div className="h-4 w-4/5 rounded bg-foreground/10" />
            </div>
            <div className="h-12 w-full rounded-xl bg-primary/20" />
          </div>

          <div className="h-72 rounded-[24px] bg-surface border border-primary/10 p-7 animate-pulse flex flex-col justify-between">
            <div>
              <div className="size-14 rounded-2xl bg-secondary/20 mb-6" />
              <div className="h-7 w-44 rounded-lg bg-primary/15 mb-3" />
              <div className="h-4 w-full rounded bg-foreground/10 mb-2" />
              <div className="h-4 w-4/5 rounded bg-foreground/10" />
            </div>
            <div className="h-12 w-full rounded-xl bg-secondary/30" />
          </div>
        </div>
      </div>
    </div>
  );
}
