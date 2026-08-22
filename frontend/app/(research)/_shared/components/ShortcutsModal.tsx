import { X, BookOpen } from "@phosphor-icons/react";
import { TAXONOMY_LABELS } from "../constants";

type ShortcutsModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

export function ShortcutsModal({ isOpen, onClose }: ShortcutsModalProps) {
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 bg-foreground/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150"
    >
      <div className="bg-surface rounded-2xl neo-border neo-shadow-lg max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        <div className="p-6 border-b border-primary/10 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <BookOpen className="size-5 text-primary" weight="duotone" />
            <h3 className="font-display font-extrabold text-lg text-foreground">
              Shortcuts &amp; Research Scoring Rubric
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-foreground/50 hover:text-foreground hover:bg-muted/60 transition-colors"
            title="Close (Esc)"
          >
            <X weight="bold" className="size-4" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-6 text-sm">
          {/* Keyboard Shortcuts Section */}
          <div className="space-y-2.5">
            <span className="text-xs font-mono uppercase font-bold text-foreground/70">
              Keyboard Shortcuts
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                <span className="font-medium text-foreground text-xs">Different Character</span>
                <kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">
                  Shift+D
                </kbd>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                <span className="font-medium text-foreground text-xs">Same Character</span>
                <kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">
                  0
                </kbd>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                <span className="font-medium text-foreground text-xs">Drift Reasons (1–7)</span>
                <kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">
                  1 – 7
                </kbd>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                <span className="font-medium text-foreground text-xs">Broken Anatomy</span>
                <kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">
                  A
                </kbd>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                <span className="font-medium text-foreground text-xs">Text Visible</span>
                <kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">
                  T
                </kbd>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                <span className="font-medium text-foreground text-xs">Submit Annotation</span>
                <kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">
                  Enter
                </kbd>
              </div>
              <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                <span className="font-medium text-foreground text-xs">Image Lightbox</span>
                <kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">
                  Space
                </kbd>
              </div>
            </div>
          </div>

          {/* Research Scoring Rubric Section */}
          <div className="space-y-3 pt-4 border-t border-primary/10">
            <div>
              <span className="text-xs font-mono uppercase font-bold text-foreground/70 block">
                Character Drift Taxonomy (Frozen 7 Reasons)
              </span>
              <p className="text-xs text-foreground/60 mt-0.5">
                Definitions &amp; examples aligned to the pre-registered Objective 4 study protocol:
              </p>
            </div>
            
            <div className="grid gap-3">
              {(Object.entries(TAXONOMY_LABELS) as [string, { label: string; shortcut: string; example: string; description: string }][]).map(([key, item]) => (
                <div key={key} className="p-3 rounded-xl bg-surface border border-muted text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-foreground flex items-center gap-2">
                      <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono border border-foreground/10">{item.shortcut}</kbd>
                      {item.label}
                    </span>
                  </div>
                  <div className="text-foreground/70 mb-1 leading-relaxed">
                    {item.description}
                  </div>
                  <div className="text-primary-deep/80 bg-primary/5 px-2 py-1 rounded-md italic">
                    Ex: {item.example}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-primary/10 bg-muted/20 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-xl bg-primary text-surface font-semibold text-sm hover:bg-primary-deep transition-all"
          >
            Close Guide
          </button>
        </div>
      </div>
    </div>
  );
}
