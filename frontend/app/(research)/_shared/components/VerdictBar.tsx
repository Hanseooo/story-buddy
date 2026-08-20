import { CheckCircle, XCircle, Info } from "@phosphor-icons/react";

type VerdictBarProps = {
  sameCharacter: boolean;
  failureReasonsCount: number;
  error: string | null;
  isPending: boolean;
  isSubmissionValid: boolean;
  onSubmit: () => void;
  submitLabel?: string;
};

export function VerdictBar({
  sameCharacter,
  failureReasonsCount,
  error,
  isPending,
  isSubmissionValid,
  onSubmit,
  submitLabel = "Submit Annotation",
}: VerdictBarProps) {
  return (
    <div className="pt-3 border-t border-primary/10 flex flex-col gap-3 mt-auto">
      {/* Clean status indicator */}
      {sameCharacter ? (
        <div className="p-3 rounded-xl bg-success/15 border border-success/30 flex items-center gap-2 text-success font-display font-bold text-sm">
          <CheckCircle weight="fill" className="size-5 shrink-0" />
          <span>Verdict: Same Character</span>
        </div>
      ) : failureReasonsCount > 0 ? (
        <div className="p-3 rounded-xl bg-destructive/15 border border-destructive/30 flex items-center gap-2 text-destructive font-display font-bold text-sm">
          <XCircle weight="fill" className="size-5 shrink-0" />
          <span>
            Verdict: Different Character ({failureReasonsCount} issue
            {failureReasonsCount > 1 ? "s" : ""})
          </span>
        </div>
      ) : (
        <div className="p-3 rounded-xl bg-muted/40 border border-muted flex items-center gap-2 text-foreground/60 text-xs">
          <Info weight="duotone" className="size-4 text-primary shrink-0" />
          <span>
            Select <strong>Same Character</strong> or <strong>Different Character</strong> failure reasons to submit.
          </span>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="p-3 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-xs font-medium flex items-center gap-2 animate-in fade-in slide-in-from-top-1 duration-200"
        >
          <XCircle weight="bold" className="size-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Main Submit Button */}
      <button
        onClick={onSubmit}
        disabled={isPending || !isSubmissionValid}
        className={`w-full py-3.5 px-4 rounded-xl font-display font-bold text-sm sm:text-base transition-all flex items-center justify-center gap-2.5 active:scale-[0.98] ${
          isPending
            ? "bg-muted text-foreground/40 border border-muted cursor-not-allowed"
            : !isSubmissionValid
            ? "bg-surface text-foreground/40 border border-muted cursor-not-allowed"
            : "bg-secondary text-foreground hover:brightness-95 cursor-pointer neo-shadow-sm shadow-secondary/20"
        }`}
      >
        <span>{isPending ? "Submitting..." : submitLabel}</span>
        <kbd
          className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${
            isSubmissionValid && !isPending
              ? "bg-foreground/10 text-foreground"
              : "bg-foreground/5 text-foreground/40"
          }`}
        >
          Enter ↵
        </kbd>
      </button>
    </div>
  );
}
