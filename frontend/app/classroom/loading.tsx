// Without this file /classroom has no Suspense boundary, so the browser holds
// the previous page (or blank on a fresh load) for the whole server render —
// ~750ms against hosted Supabase. This is the boundary that lets Next stream.
export default function Loading() {
  return (
    <div className="flex items-center justify-center min-h-[60vh] p-6">
      <div
        role="status"
        aria-label="Loading classrooms"
        className="w-10 h-10 rounded-full border-4 border-primary/20 border-t-primary animate-spin"
      />
    </div>
  );
}
