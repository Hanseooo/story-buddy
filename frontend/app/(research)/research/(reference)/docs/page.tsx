import { ArrowSquareOut, FileText, FolderOpen } from "@phosphor-icons/react/dist/ssr";
import { DOC_FOLDERS, githubUrl } from "./entries";

export const metadata = {
  title: "StoryBuddy Research Documents",
};

const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

export default function DocsPage() {
  return (
    <main className="space-y-8 pt-4 lg:space-y-10">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-4xl font-extrabold tracking-tight md:text-5xl">Research documents</h1>
        <p className="max-w-[65ch] text-base text-foreground/70">
          The files behind the study, laid out as they sit in the repository. Each one opens on GitHub in a new
          tab, always at its latest version.
        </p>
      </div>

      <ul className="space-y-6">
        {DOC_FOLDERS.map((folder) => (
          <li key={folder.path} className="rounded-3xl bg-surface p-5 neo-border neo-shadow-sm sm:p-6">
            <h2 className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className="inline-flex items-center gap-2 font-mono text-base font-bold text-foreground">
                <FolderOpen weight="duotone" className="size-5 shrink-0 text-primary" aria-hidden />
                {folder.path}/
              </span>
              <span className="font-sans text-sm font-medium text-foreground/60">{folder.holds}</span>
            </h2>

            <ul className="mt-3 ml-2.5 space-y-1 border-l-2 border-primary/15 pl-4 sm:pl-6">
              {folder.entries.map((entry) => (
                <li key={entry.file} className="py-1">
                  <a
                    href={githubUrl(`${folder.path}/${entry.file}`)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`inline-flex min-h-11 max-w-full items-center gap-2 rounded-lg font-mono text-sm font-bold text-primary hover:text-primary-deep hover:underline ${FOCUS}`}
                  >
                    <FileText weight="bold" className="size-4 shrink-0" aria-hidden />
                    <span className="min-w-0 [overflow-wrap:anywhere]">{entry.file}</span>
                    {entry.startHere && (
                      <span className="shrink-0 rounded-full bg-secondary/30 px-2 py-0.5 font-sans text-xs font-bold text-foreground">
                        Start here
                      </span>
                    )}
                    <ArrowSquareOut weight="bold" className="size-3.5 shrink-0" aria-hidden />
                    <span className="sr-only"> (opens on GitHub in a new tab)</span>
                  </a>
                  <p className="max-w-[70ch] text-sm text-foreground/70">{entry.answers}</p>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </main>
  );
}
