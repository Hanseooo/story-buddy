const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// Jump links to a page's sections. Each id must be an h2 on the page.
export default function OnThisPage({ sections }: { sections: readonly { id: string; label: string }[] }) {
  return (
    <nav aria-label="On this page">
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
    </nav>
  );
}
