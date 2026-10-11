import { ArrowSquareOut } from "@phosphor-icons/react/dist/ssr";
import { githubUrl } from "../../research/(reference)/docs/entries";

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// The file a section's numbers come from, opened on GitHub. Used by the static research pages (ADR-065).
export default function Source({ path, where }: { path: string; where: string }) {
  return (
    <p className="text-sm text-foreground/60">
      Source:{" "}
      <a
        href={githubUrl(path)}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex min-h-11 items-center gap-1 rounded-lg font-mono font-bold text-primary hover:text-primary-deep hover:underline sm:min-h-0 ${FOCUS}`}
      >
        <span className="break-all">{path}</span>
        <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
        <span className="sr-only"> (opens on GitHub in a new tab)</span>
      </a>
      , {where}
    </p>
  );
}
