"use client";

export default function Error({}: { error: Error }) {
  return (
    <div role="alert" className="p-8 text-center text-foreground">
      <p className="mb-4 font-bold">We couldn&apos;t load the research metrics right now.</p>
      <form action="/auth/signout" method="post">
        <button
          type="submit"
          className="min-h-11 rounded-xl border border-primary/20 px-6 py-2.5 font-bold text-primary hover:bg-muted/40 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
        >
          Log out
        </button>
      </form>
    </div>
  );
}
