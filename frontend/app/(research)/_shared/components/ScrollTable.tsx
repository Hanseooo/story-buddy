const FOCUS = "focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3";

// tabIndex: a table wider than the screen scrolls sideways, and a keyboard user needs to reach it.
export default function ScrollTable({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div role="region" aria-label={label} tabIndex={0} className={`overflow-x-auto rounded-2xl neo-border ${FOCUS}`}>
      <table className="w-full min-w-[36rem] border-collapse text-sm">
        <caption className="sr-only">{label}</caption>
        {children}
      </table>
    </div>
  );
}
