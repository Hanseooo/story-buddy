"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="font-kid min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center">
        <p className="text-lg font-bold mb-4">Something went wrong.</p>
        <p className="text-sm text-foreground/70 mb-6">{error.message}</p>
        <button
          onClick={reset}
          className="min-h-11 px-6 py-2.5 rounded-xl bg-primary text-on-primary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)]"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
