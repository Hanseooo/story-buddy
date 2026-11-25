export default function Loading() {
  return (
    <ul className="grid grid-cols-2 gap-4 p-6 sm:grid-cols-3 md:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <li
          key={i}
          className="overflow-hidden rounded-2xl border border-primary/15 bg-surface"
        >
          {/* Matches the real card: a 4:3 cover, a title row and an avatar row. */}
          <div className="aspect-[4/3] w-full animate-pulse border-b border-primary/15 bg-muted/50" />
          <div className="p-3 flex flex-col gap-1">
            <div className="h-5 w-2/3 animate-pulse rounded-md bg-muted/50" />
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 shrink-0 animate-pulse rounded-full bg-muted/50" />
              <div className="h-6 w-1/2 animate-pulse rounded-md bg-muted/50" />
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}
