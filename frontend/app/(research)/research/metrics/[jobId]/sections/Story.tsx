import type { RunDetail } from "../types";

export default function Story({ story }: { story: RunDetail["story"] }) {
  return (
    <section id="story" aria-labelledby="story-heading" className="scroll-mt-6 space-y-3">
      <h2 id="story-heading" className="font-display text-2xl font-bold">Story</h2>
      {story?.redacted_text ? (
        <div className="rounded-3xl bg-surface p-5 neo-border neo-shadow-sm">
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-foreground/50">
            Redacted · {story.word_count} words{story.truncated ? " · cut to the word limit" : ""}
          </p>
          <p className="max-w-[60ch] whitespace-pre-line text-base leading-relaxed">{story.redacted_text}</p>
        </div>
      ) : (
        <p className="text-sm text-foreground/60">No story text recorded for this run.</p>
      )}
    </section>
  );
}
