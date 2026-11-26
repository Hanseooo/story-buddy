import { useId } from "react";

// The keep-or-old choice in the reader and the reveal. Old and New sit side by side once the choice
// is 28rem wide (a viewport of about 560px and up), and stack on a phone (audit B3).
export default function OldNewPictures({ old, fresh }: { old: React.ReactNode; fresh: React.ReactNode }) {
  return (
    <div className="@container">
      <div className="grid grid-cols-1 gap-3 @md:grid-cols-2">
        <Labelled label="Old">{old}</Labelled>
        <Labelled label="New">{fresh}</Labelled>
      </div>
    </div>
  );
}

function Labelled({ label, children }: { label: string; children: React.ReactNode }) {
  const id = useId();
  return (
    <figure aria-labelledby={id} className="flex flex-col gap-1">
      <figcaption id={id} className="font-kid text-sm font-bold text-foreground">{label}</figcaption>
      {children}
    </figure>
  );
}
