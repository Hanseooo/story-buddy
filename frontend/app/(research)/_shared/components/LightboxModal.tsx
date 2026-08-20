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
  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 bg-foreground/80 backdrop-blur-md flex flex-col p-4 md:p-8 animate-in fade-in duration-200"
    >
      <div className="flex items-center justify-between pb-4 text-surface border-b border-surface/20">
        <div className="flex items-center gap-3">
          <h3 className="font-display font-extrabold text-lg">
            High-Resolution Image Inspector
          </h3>
          <div className="flex items-center rounded-lg bg-surface/10 p-1 border border-surface/20">
            <button
              onClick={() => setActiveTab("side-by-side")}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                activeTab === "side-by-side"
                  ? "bg-surface text-foreground"
                  : "text-surface/80 hover:text-surface"
              }`}
            >
              Side-by-Side
            </button>
            <button
              onClick={() => setActiveTab("canonical")}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
                activeTab === "canonical"
                  ? "bg-surface text-foreground"
                  : "text-surface/80 hover:text-surface"
              }`}
            >
              Reference
            </button>
            <button
              onClick={() => setActiveTab("scene")}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${
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
          className="p-2 rounded-xl bg-surface/10 hover:bg-surface/20 text-surface transition-colors"
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
    </div>
  );
}
