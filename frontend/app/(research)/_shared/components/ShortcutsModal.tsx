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
              Shortcuts &amp; Labelling Rulebook
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

          {/* Labelling rulebook: docs/specs/labelling-rulebook.md, frozen. Edit the rulebook, never only this text. */}
          <div className="space-y-3 pt-4 border-t border-primary/10">
            <span className="text-xs font-mono uppercase font-bold text-foreground/70 block">
              How to decide
            </span>
            <ul className="space-y-2 text-xs text-foreground/80 leading-relaxed list-disc pl-4">
              <li>
                <strong className="text-foreground">Judge only what the two images show.</strong> Image 1 is the
                reference, image 2 is the page. Never use what you know about the story, and never assume a page
                is right because it was drawn from that reference.
              </li>
              <li>
                <strong className="text-foreground">Different needs a difference you can name.</strong> If no
                listed reason fits, the answer is Same.
              </li>
              <li>
                <strong className="text-foreground">Step 1 · Find the character.</strong> Compare only the
                reference character; others on the page do not count. Not on the page: Different + Character
                Absent. Several could be them, or it is drawn twice: compare the best match. A duplicate is not
                an identity failure.
              </li>
              <li>
                <strong className="text-foreground">Step 2 · Identity.</strong>{" "}
                <strong className="text-foreground">Same</strong> when species, face, body colours and body
                features all match. <strong className="text-foreground">Different</strong> when any of them
                differs. Tick every reason that applies.
              </li>
              <li>
                <strong className="text-foreground">Step 3 · Not identity on their own, each is Same:</strong>{" "}
                clothing or accessories, art style, lighting, shadow, weather, dirt, wetness. Tick Clothing or
                Style only when the pair is already Different.
              </li>
            </ul>

            <span className="text-xs font-mono uppercase font-bold text-foreground/70 block pt-2">
              Step 4 · Hard cases
            </span>
            <ul className="space-y-2 text-xs text-foreground/80 leading-relaxed list-disc pl-4">
              <li>
                <strong className="text-foreground">Older or younger:</strong> Same if face, body colours and
                features still match. Different if they do not (grey hair is Wrong Color; a new face shape is
                Different Face). Being an adult is not a reason by itself.
              </li>
              <li>
                <strong className="text-foreground">Costume or disguise:</strong> clothing alone is Same. If it
                hides the face, use the next row.
              </li>
              <li>
                <strong className="text-foreground">Back view, hidden face, silhouette, very small:</strong> judge
                what is visible. Same when nothing visible contradicts the reference. Never mark Different only
                because the face cannot be seen.
              </li>
              <li>
                <strong className="text-foreground">Transformation</strong> (turned into an animal, a ghost): no
                special case, apply Step 2. A changed species is Wrong Species.
              </li>
              <li>
                <strong className="text-foreground">Partly cut off by the frame:</strong> judge what is visible, as
                above.
              </li>
            </ul>
          </div>

          <div className="space-y-3 pt-4 border-t border-primary/10">
            <span className="text-xs font-mono uppercase font-bold text-foreground/70 block">
              Step 2 · Drift reasons (frozen 7)
            </span>

            <div className="grid gap-3">
              {(Object.entries(TAXONOMY_LABELS) as [string, { label: string; shortcut: string; doesNotCount: string; description: string }][]).map(([key, item]) => (
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
                    Does not count: {item.doesNotCount}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-2 pt-4 border-t border-primary/10">
            <span className="text-xs font-mono uppercase font-bold text-foreground/70 block">
              Step 5 · Artifact checkboxes (on either answer)
            </span>
            <ul className="space-y-2 text-xs text-foreground/80 leading-relaxed list-disc pl-4">
              <li>
                <strong className="text-foreground">Broken Anatomy:</strong> merged, missing or duplicated body
                parts on the character as drawn on the page, not on the reference.
              </li>
              <li>
                <strong className="text-foreground">Text Visible:</strong> any letters, numbers or writing
                anywhere on the page.
              </li>
            </ul>
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
