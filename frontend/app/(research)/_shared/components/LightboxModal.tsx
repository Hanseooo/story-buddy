import { useEffect, useRef } from "react";
import { X } from "@phosphor-icons/react";
import { ResearchPair } from "../constants";

type LightboxModalProps = {
  isOpen: boolean;
  onClose: () => void;
  pair: ResearchPair;
  activeTab: "side-by-side" | "canonical" | "scene";
  setActiveTab: (tab: "side-by-side" | "canonical" | "scene") => void;
};

export function LightboxModal({ isOpen, onClose, pair, activeTab, setActiveTab }: LightboxModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    dialog?.showModal();
    dialog?.focus();
    return () => {
      if (dialog?.open) dialog.close();
      if (previouslyFocused?.isConnected) previouslyFocused.focus();
    };
  }, [isOpen]);

  if (!isOpen) return null;

  // Enter stays in the dialog so it cannot submit the form behind it. Every other key reaches the page shortcuts.
  const handleDialogKeyDown = (event: React.KeyboardEvent<HTMLDialogElement>) => {
    if (event.key === "Enter") event.stopPropagation();
  };

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="lightbox-dialog-title"
      tabIndex={-1}
      onKeyDown={handleDialogKeyDown}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      className="fixed inset-0 z-50 m-0 flex h-[100dvh] w-screen max-h-none max-w-none flex-col border-0 bg-foreground/80 p-4 text-surface backdrop-blur-md md:p-8 animate-in fade-in duration-200"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-surface/20 pb-4">
        <div className="flex min-w-0 flex-wrap items-center gap-3">
          <h3 id="lightbox-dialog-title" className="font-display font-extrabold text-base sm:text-lg">
            High-Resolution Image Inspector
          </h3>
          <div className="flex flex-wrap items-center rounded-lg bg-surface/10 p-1 border border-surface/20">
            <button
              onClick={() => setActiveTab("side-by-side")}
              aria-pressed={activeTab === "side-by-side"}
              className={`min-h-11 sm:min-h-0 px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                activeTab === "side-by-side"
                  ? "bg-surface text-foreground"
                  : "text-surface/80 hover:text-surface"
              }`}
            >
              Side-by-Side
            </button>
            <button
              onClick={() => setActiveTab("canonical")}
              aria-pressed={activeTab === "canonical"}
              className={`min-h-11 sm:min-h-0 px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                activeTab === "canonical"
                  ? "bg-surface text-foreground"
                  : "text-surface/80 hover:text-surface"
              }`}
            >
              Reference
            </button>
            <button
              onClick={() => setActiveTab("scene")}
              aria-pressed={activeTab === "scene"}
              className={`min-h-11 sm:min-h-0 px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                activeTab === "scene"
                  ? "bg-surface text-foreground"
                  : "text-surface/80 hover:text-surface"
              }`}
            >
              Scene
            </button>
          </div>
        </div>

        <button
          onClick={onClose}
          aria-label="Close image inspector"
          className="shrink-0 min-h-11 min-w-11 inline-flex items-center justify-center p-2 rounded-xl bg-surface/10 hover:bg-surface/20 text-surface transition-colors"
          title="Close (Esc)"
        >
          <X weight="bold" className="size-5" />
        </button>
      </div>

      <div className="flex-1 overflow-auto flex items-center justify-center p-4">
        {activeTab === "side-by-side" ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-6xl w-full h-full max-h-[80vh]">
            <div className="bg-surface rounded-2xl p-4 flex flex-col items-center justify-center gap-2 overflow-hidden">
              <span className="font-display font-bold text-xs text-primary uppercase">
                Canonical Reference
              </span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={pair.canonical_signed_url}
                alt="Canonical Reference"
                className="object-contain w-full h-full max-h-[70vh]"
              />
            </div>
            <div className="bg-surface rounded-2xl p-4 flex flex-col items-center justify-center gap-2 overflow-hidden">
              <span className="font-display font-bold text-xs text-primary uppercase">
                Generated Scene
              </span>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={pair.scene_signed_url}
                alt="Generated Scene"
                className="object-contain w-full h-full max-h-[70vh]"
              />
            </div>
          </div>
        ) : activeTab === "canonical" ? (
          <div className="bg-surface rounded-2xl p-6 max-w-3xl w-full max-h-[80vh] flex flex-col items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pair.canonical_signed_url}
              alt="Canonical Reference"
              className="object-contain w-full h-full max-h-[75vh]"
            />
          </div>
        ) : (
          <div className="bg-surface rounded-2xl p-6 max-w-3xl w-full max-h-[80vh] flex flex-col items-center justify-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pair.scene_signed_url}
              alt="Generated Scene"
              className="object-contain w-full h-full max-h-[75vh]"
            />
          </div>
        )}
      </div>
    </dialog>
  );
}
