"use client";

export default function GalleryError({
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="flex min-h-[50vh] items-center justify-center px-6">
      <div className="text-center">
        <p className="text-lg font-bold mb-4">Couldn&apos;t load the gallery.</p>
        <button
          onClick={reset}
          className="min-h-11 px-6 py-2.5 rounded-xl bg-primary text-on-primary font-extrabold shadow-[0_4px_0_var(--color-primary-deep)]"
        >
          Try again
        </button>
        <form action="/auth/signout" method="post" className="mt-3">
          <button
            type="submit"
            className="min-h-11 rounded-xl border border-primary/20 px-6 py-2.5 font-bold text-primary hover:bg-muted/40 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
          >
            Log out
          </button>
        </form>
      </div>
    </div>
  );
}
