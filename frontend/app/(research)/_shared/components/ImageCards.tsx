import { MagnifyingGlassPlus } from "@phosphor-icons/react";
import { ResearchPair } from "../constants";

type ImageCardsProps = {
  pair: ResearchPair;
  onOpenLightbox: () => void;
  setActiveLightboxTab: (tab: "canonical" | "scene") => void;
};

export function ImageCards({ pair, onOpenLightbox, setActiveLightboxTab }: ImageCardsProps) {
  return (
    <div className="lg:col-span-7 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-display font-extrabold text-lg text-foreground tracking-tight">
            Visual Comparison
          </span>
        </div>

        <button
          onClick={onOpenLightbox}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold text-primary hover:bg-primary/10 transition-colors"
          title="Expand side-by-side view (Space)"
        >
          <MagnifyingGlassPlus weight="bold" className="size-3.5" />
          <span>Inspect (Space)</span>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-5">
        {/* Card 1: Canonical Reference */}
        <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-4 flex flex-col gap-3 group">
          <div className="flex items-center justify-between">
            <h3 className="font-display font-bold text-sm text-foreground">
              Canonical Reference
            </h3>
          </div>

          <div
            onClick={() => {
              setActiveLightboxTab("canonical");
              onOpenLightbox();
            }}
            className="aspect-square w-full bg-muted/30 rounded-xl overflow-hidden relative border border-primary/10 flex items-center justify-center cursor-zoom-in group/img"
            title="Click to inspect canonical reference"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pair.canonical_signed_url}
              alt="Canonical Reference"
              className="object-contain w-full h-full p-2 transition-transform duration-200 group-hover/img:scale-[1.02]"
            />
          </div>

          <p className="text-center text-xs text-foreground/60">
            Target character identity baseline
          </p>
        </div>

        {/* Card 2: Generated Scene */}
        <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-4 flex flex-col gap-3 group">
          <div className="flex items-center justify-between">
            <h3 className="font-display font-bold text-sm text-foreground">
              Generated Scene
            </h3>
          </div>

          <div
            onClick={() => {
              setActiveLightboxTab("scene");
              onOpenLightbox();
            }}
            className="aspect-square w-full bg-muted/30 rounded-xl overflow-hidden relative border border-primary/10 flex items-center justify-center cursor-zoom-in group/img"
            title="Click to inspect generated scene"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pair.scene_signed_url}
              alt="Generated Scene"
              className="object-contain w-full h-full p-2 transition-transform duration-200 group-hover/img:scale-[1.02]"
            />
          </div>

          <p className="text-center text-xs text-foreground/60">
            Model output to be evaluated
          </p>
        </div>
      </div>
    </div>
  );
}
