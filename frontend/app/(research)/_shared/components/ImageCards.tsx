import { MagnifyingGlassPlus, Sparkle, Target } from "@phosphor-icons/react";
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
          <span className="px-2 py-0.5 rounded-md bg-primary/10 text-primary text-[11px] font-mono font-semibold">
            Side-by-Side
          </span>
        </div>

        <button
          onClick={onOpenLightbox}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-primary/20 bg-surface text-xs font-semibold text-primary hover:bg-primary/10 hover:text-primary-deep active:scale-[0.98] transition-all neo-shadow-xs"
          title="Expand side-by-side view (Space)"
        >
          <MagnifyingGlassPlus weight="bold" className="size-3.5" />
          <span>Inspect High-Res</span>
          <kbd className="px-1 py-0.2 rounded bg-muted/60 text-[10px] font-mono border border-foreground/15">Space</kbd>
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-5">
        {/* Card 1: Canonical Reference */}
        <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-4 md:p-5 flex flex-col gap-3 group hover:border-primary/30 transition-all">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Target weight="bold" className="size-4 text-primary" />
              <h3 className="font-display font-bold text-sm text-foreground">
                Canonical Reference
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded bg-muted/60 text-foreground/60 text-[10px] font-mono font-medium">
              Baseline
            </span>
          </div>

          <div
            onClick={() => {
              setActiveLightboxTab("canonical");
              onOpenLightbox();
            }}
            className="aspect-square w-full bg-muted/20 rounded-xl overflow-hidden relative border border-primary/10 flex items-center justify-center cursor-zoom-in group/img hover:bg-muted/30 transition-colors"
            title="Click to inspect canonical reference"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pair.canonical_signed_url}
              alt="Canonical Reference"
              className="object-contain w-full h-full p-2 transition-transform duration-200 group-hover/img:scale-[1.03]"
            />
            <div className="absolute bottom-2 right-2 opacity-0 group-hover/img:opacity-100 transition-opacity bg-foreground/75 text-surface text-[10px] px-2 py-0.5 rounded-md backdrop-blur-xs font-sans">
              Click to Zoom
            </div>
          </div>

          <p className="text-center text-xs text-foreground/60 leading-relaxed">
            Target character identity baseline
          </p>
        </div>

        {/* Card 2: Generated Scene */}
        <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-4 md:p-5 flex flex-col gap-3 group hover:border-primary/30 transition-all">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <Sparkle weight="bold" className="size-4 text-secondary-deep" />
              <h3 className="font-display font-bold text-sm text-foreground">
                Generated Scene
              </h3>
            </div>
            <span className="px-2 py-0.5 rounded bg-muted/60 text-foreground/60 text-[10px] font-mono font-medium">
              Candidate
            </span>
          </div>

          <div
            onClick={() => {
              setActiveLightboxTab("scene");
              onOpenLightbox();
            }}
            className="aspect-square w-full bg-muted/20 rounded-xl overflow-hidden relative border border-primary/10 flex items-center justify-center cursor-zoom-in group/img hover:bg-muted/30 transition-colors"
            title="Click to inspect generated scene"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pair.scene_signed_url}
              alt="Generated Scene"
              className="object-contain w-full h-full p-2 transition-transform duration-200 group-hover/img:scale-[1.03]"
            />
            <div className="absolute bottom-2 right-2 opacity-0 group-hover/img:opacity-100 transition-opacity bg-foreground/75 text-surface text-[10px] px-2 py-0.5 rounded-md backdrop-blur-xs font-sans">
              Click to Zoom
            </div>
          </div>

          <p className="text-center text-xs text-foreground/60 leading-relaxed">
            Model output to be evaluated
          </p>
        </div>
      </div>
    </div>
  );
}
