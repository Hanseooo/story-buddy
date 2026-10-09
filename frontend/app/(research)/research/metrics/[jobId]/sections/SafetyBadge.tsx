import { Hourglass, ShieldCheck, ShieldWarning } from "@phosphor-icons/react/dist/ssr";

export default function SafetyBadge({ status, label }: { status: string | null; label: string }) {
  if (status === "passed") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-success/15 px-2.5 py-1 text-xs font-bold text-success">
        <ShieldCheck weight="fill" className="size-4" aria-hidden />
        {label} passed
      </span>
    );
  }
  if (status == null) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-xs font-bold text-foreground/70">
        <Hourglass weight="bold" className="size-4" aria-hidden />
        {label} not checked
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-destructive/15 px-2.5 py-1 text-xs font-bold text-destructive">
      <ShieldWarning weight="fill" className="size-4" aria-hidden />
      {label} {status}
    </span>
  );
}
