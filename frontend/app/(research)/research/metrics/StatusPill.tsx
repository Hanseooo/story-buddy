import { statusLabel } from "@/utils/metrics";

const TONE: Record<string, string> = {
  complete: "bg-success/15 text-success",
  failed: "bg-destructive/15 text-destructive",
  awaiting_confirm: "bg-warning/20 text-foreground",
};

export default function StatusPill({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider ${
        TONE[status] ?? "bg-muted text-foreground/70"
      }`}
    >
      {statusLabel(status)}
    </span>
  );
}
