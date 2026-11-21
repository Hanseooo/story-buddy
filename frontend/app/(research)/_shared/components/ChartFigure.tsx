import { ArrowSquareOut, DownloadSimple } from "@phosphor-icons/react/dist/ssr";
import { githubUrl } from "../../research/(reference)/docs/entries";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";
const LINK = `inline-flex min-h-11 items-center gap-1.5 rounded-lg font-bold text-primary hover:text-primary-deep hover:underline sm:min-h-0 ${FOCUS}`;

// A research chart (SH-06): an id that ticket 11 screenshots, alt text, an "As of" caption, a download link that
// names its PNG, and a link to the data the chart is drawn from. The PNG is made by the export, not here.
export default function ChartFigure({
  id,
  alt,
  asOf,
  png,
  source,
  caption,
  sourceNoun = "the chart data",
  children,
}: {
  id: string;
  alt: string;
  asOf: string;
  png: string;
  source: string;
  caption: React.ReactNode;
  sourceNoun?: string;
  children: React.ReactNode;
}) {
  const file = png.slice(png.lastIndexOf("/") + 1);
  return (
    <figure
      id={id}
      data-chart-id={id}
      aria-label={alt}
      className="max-w-3xl space-y-5 rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6"
    >
      <figcaption className="space-y-2 text-sm text-foreground/80">
        {caption}
        <span className="block text-foreground/60">{`As of ${asOf}`}</span>
      </figcaption>
      {children}
      <p className="flex flex-wrap gap-x-5 gap-y-1 text-sm">
        <a href={png} download={file} className={LINK}>
          <DownloadSimple weight="bold" className="size-4 shrink-0" aria-hidden />
          {`Download ${file}`}
        </a>
        <a href={githubUrl(source)} target="_blank" rel="noopener noreferrer" className={LINK}>
          <span className="font-mono">{source.slice(source.lastIndexOf("/") + 1)}</span>
          <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
          <span className="sr-only">{`, ${sourceNoun} (opens on GitHub in a new tab)`}</span>
        </a>
      </p>
    </figure>
  );
}
