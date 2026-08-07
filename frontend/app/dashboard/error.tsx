"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="font-sans min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center">
        <h1 className="font-display text-2xl font-extrabold text-primary mb-2">
          Something went wrong
        </h1>
        <p className="text-sm text-foreground/70 mb-6">{error.message}</p>
        <button
          onClick={reset}
          className="min-h-11 px-6 py-2.5 rounded-xl border border-primary/20 font-bold hover:bg-muted transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
