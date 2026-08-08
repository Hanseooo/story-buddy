"use client";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <div className="flex items-center justify-center min-h-[60vh] p-6">
      <div className="max-w-md w-full text-center bg-surface border-2 border-primary/10 rounded-[28px] p-8">
        <h1 className="font-display text-2xl font-extrabold text-primary mb-2">
          Something went wrong
        </h1>
        <p className="text-sm text-foreground/70 mb-6">
          We couldn&apos;t load your classrooms. Try again, or log out and back
          in.
        </p>
        <button
          onClick={reset}
          className="min-h-11 px-5 py-2 rounded-xl bg-primary text-on-primary font-bold shadow-[0_4px_0_var(--color-primary-deep)]"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
