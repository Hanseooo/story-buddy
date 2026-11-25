import { Job, jobState } from "@/lib/types/jobs";
import { Avatar } from "@/components/Avatar";
import { displayTitle } from "@/lib/displayTitle";
import PictureBox from "@/components/PictureBox";

type Props = {
  job: Job;
  /** undefined while signing, null when signing found no link. */
  thumbnailUrl: string | null | undefined;
  /** Absent when the book has no picture to sign. */
  onRetryThumbnail?: () => void;
  onOpen: () => void;
};

export default function BookCard({ job, thumbnailUrl, onRetryThumbnail, onOpen }: Props) {
  const state = jobState(job);
  const name = job.profiles?.display_nickname ?? "Unknown";
  const bookTitle = displayTitle(job.title, job.input_text);
  const date = new Date(job.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  // The picture's Try again cannot sit inside the card button, so the button's ::after covers the
  // card instead and Try again sits above it. The globals.css focus ring matches only the focused
  // element itself, which here would be clipped by the card, so the card draws the same ring
  // (3px yellow outline, 3px offset, navy band) while its button has focus.
  return (
    <div className="relative bg-surface border border-primary/15 rounded-2xl overflow-hidden shadow-[0_6px_18px_rgb(49_85_217/10%)] hover:border-primary/40 transition-colors has-[>button:focus-visible]:outline-3 has-[>button:focus-visible]:outline-offset-3 has-[>button:focus-visible]:outline-secondary has-[>button:focus-visible]:shadow-[0_0_0_3px_var(--foreground)]">
      {/* Thumbnail */}
      <PictureBox src={thumbnailUrl} alt="" onRetry={onRetryThumbnail} />

      {/* Meta */}
      <button
        onClick={onOpen}
        className="w-full text-left px-4 py-3 flex items-center gap-3 focus:outline-none focus-visible:shadow-none! after:absolute after:inset-0"
        aria-label={`Review story by ${name}: ${bookTitle}`}
      >
        <StateBadge state={state} className="absolute top-3 right-3" />
        <Avatar avatarId={job.profiles?.avatar_id ?? null} displayNickname={name} size={32} />
        <div className="min-w-0">
          <p className="font-bold text-foreground text-sm truncate">{name}</p>
          <p className="text-xs text-foreground/60 truncate">{bookTitle}</p>
          <p className="text-xs text-foreground/50 mt-0.5">{date}</p>
        </div>
      </button>
    </div>
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
        Shared with class
      </span>
    );
  if (state === "rejected")
    return (
      <span
        className={`bg-destructive/90 text-on-destructive text-xs font-bold px-2 py-1 rounded-lg ${className}`}
      >
        Not ready yet
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
