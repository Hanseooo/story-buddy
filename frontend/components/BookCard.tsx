import { Job, jobState } from "@/lib/types/jobs";
import { Avatar } from "@/components/Avatar";

type Props = {
  job: Job;
  thumbnailUrl: string | null;
  onOpen: () => void;
};

export default function BookCard({ job, thumbnailUrl, onOpen }: Props) {
  const state = jobState(job);
  const name = job.profiles?.display_nickname ?? "Unknown";
  const date = new Date(job.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  return (
    <button
      onClick={onOpen}
      className="w-full text-left bg-surface border border-primary/15 rounded-2xl overflow-hidden shadow-[0_6px_18px_rgb(49_85_217/10%)] hover:border-primary/40 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-secondary focus-visible:ring-offset-2"
      aria-label={`Review story by ${name}`}
    >
      {/* Thumbnail */}
      <div className="aspect-[3/2] bg-muted relative">
        {thumbnailUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={thumbnailUrl}
            alt=""
            aria-hidden="true"
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full animate-pulse bg-muted" />
        )}
        <StateBadge state={state} className="absolute top-3 right-3" />
      </div>

      {/* Meta */}
      <div className="px-4 py-3 flex items-center gap-3">
        <Avatar avatarId={job.profiles?.avatar_id ?? null} displayNickname={name} size={32} />
        <div>
          <p className="font-bold text-foreground text-sm truncate">{name}</p>
          <p className="text-xs text-foreground/50 mt-0.5">{date}</p>
        </div>
      </div>
    </button>
  );
}

export function StateBadge({
  state,
  className = "",
}: {
  state: "pending" | "approved" | "rejected";
  className?: string;
}) {
  if (state === "approved")
    return (
      <span
        className={`bg-success/90 text-on-success text-xs font-bold px-2 py-1 rounded-lg ${className}`}
      >
        Approved
      </span>
    );
  if (state === "rejected")
    return (
      <span
        className={`bg-destructive/90 text-on-destructive text-xs font-bold px-2 py-1 rounded-lg ${className}`}
      >
        Rejected
      </span>
    );
  return (
    <span
      className={`bg-foreground/70 text-background text-xs font-bold px-2 py-1 rounded-lg ${className}`}
    >
      Needs review
    </span>
  );
}
