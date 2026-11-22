const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// Past this many links the list folds behind a tap: 14 chips fill most of a phone's first screen.
const FOLD_AFTER = 8;

// Jump links to a page's sections. Each id must be an h2 on the page.
export default function OnThisPage({ sections }: { sections: readonly { id: string; label: string }[] }) {
  const list = (
    <ul className="flex flex-wrap gap-2">
      {sections.map((section) => (
        <li key={section.id}>
          <a
            href={`#${section.id}`}
            className={`inline-flex min-h-11 items-center rounded-xl border border-primary/20 bg-surface px-3 text-sm font-bold text-primary hover:bg-primary/5 ${FOCUS}`}
          >
            {section.label}
          </a>
        </li>
      ))}
    </ul>
  );
  return (
    <nav aria-label="On this page">
      {sections.length > FOLD_AFTER ? (
        <details className="group rounded-2xl border border-primary/20 bg-surface">
          <summary
            className={`flex min-h-11 cursor-pointer list-none items-center justify-between gap-2 rounded-2xl px-4 text-sm font-bold text-primary hover:bg-primary/5 [&::-webkit-details-marker]:hidden ${FOCUS}`}
          >
            {`On this page: ${sections.length} sections`}
            <span aria-hidden className="transition-transform group-open:rotate-180">
              ▾
            </span>
          </summary>
          <div className="px-3 pb-3">{list}</div>
        </details>
      ) : (
        list
      )}
    </nav>
  );
}
