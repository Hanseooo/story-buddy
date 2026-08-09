export default function Loading() {
  return (
    <ul className="grid grid-cols-2 gap-4 p-6 sm:grid-cols-3 md:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <li
          key={i}
          className="overflow-hidden rounded-2xl border border-primary/15 bg-surface"
        >
          <div className="aspect-[3/4] w-full animate-pulse bg-muted/50" />
          <div className="p-3">
            <div className="h-6 w-2/3 animate-pulse rounded-md bg-muted/50" />
          </div>
        </li>
      ))}
    </ul>
  );
}
