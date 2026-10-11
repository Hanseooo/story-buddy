import { MagnifyingGlassPlus, Sparkle, Target } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { ResearchPair } from "../constants";

type ImageCardsProps = {
  pair: ResearchPair;
  onOpenLightbox: () => void;
  setActiveLightboxTab: (tab: "side-by-side" | "canonical" | "scene") => void;
  onImageStateChange?: (state: "loading" | "ready" | "error") => void;
};

export function ImageCards({ pair, onOpenLightbox, setActiveLightboxTab, onImageStateChange }: ImageCardsProps) {
  const [imageStates, setImageStates] = useState<{
    canonical: "loading" | "ready" | "error";
    scene: "loading" | "ready" | "error";
  }>({ canonical: "loading", scene: "loading" });
  const [retryNumber, setRetryNumber] = useState(0);
  const canonicalImageRef = useRef<HTMLImageElement>(null);
  const sceneImageRef = useRef<HTMLImageElement>(null);
  const demoImageState = imageStates.canonical === "error" || imageStates.scene === "error"
    ? "error"
    : imageStates.canonical === "ready" && imageStates.scene === "ready"
      ? "ready"
      : "loading";

  useEffect(() => {
    if (onImageStateChange) onImageStateChange(demoImageState);
  }, [demoImageState, onImageStateChange]);

  useEffect(() => {
    if (!onImageStateChange) return;
    // An image that settled before this ran fires no load or error event here. A finished image with no
    // width is a failed one.
    const settled = (image: HTMLImageElement | null) =>
      image?.complete ? (image.naturalWidth > 0 ? "ready" : "error") : null;
    const canonical = settled(canonicalImageRef.current);
    const scene = settled(sceneImageRef.current);
    if (canonical) setImageStates((current) => ({ ...current, canonical }));
    if (scene) setImageStates((current) => ({ ...current, scene }));
  }, [onImageStateChange, pair.canonical_signed_url, pair.scene_signed_url, retryNumber]);

  const openImage = (tab: "canonical" | "scene") => {
    setActiveLightboxTab(tab);
    onOpenLightbox();
  };

  const setImageState = (image: "canonical" | "scene", state: "ready" | "error") => {
    if (!onImageStateChange) return;
    setImageStates((current) => ({ ...current, [image]: state }));
  };

  const retryImages = () => {
    setImageStates({ canonical: "loading", scene: "loading" });
    setRetryNumber((number) => number + 1);
  };

  return (
    <div className="lg:col-span-7 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-display font-extrabold text-lg text-foreground tracking-tight">
            Visual Comparison
          </span>
          <span className="px-2 py-0.5 rounded-md bg-primary/10 text-primary text-[11px] font-mono font-semibold">
            Side-by-Side
          </span>
        </div>

        <button
          onClick={() => {
            setActiveLightboxTab("side-by-side");
            onOpenLightbox();
          }}
          className="inline-flex min-h-11 items-center gap-1.5 px-3 py-1.5 rounded-xl border border-primary/20 bg-surface text-xs font-semibold text-primary hover:bg-primary/10 hover:text-primary-deep active:scale-[0.98] transition-all neo-shadow-xs"
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

          <button
            type="button"
            onClick={() => openImage("canonical")}
            className="aspect-square w-full bg-muted/20 rounded-xl overflow-hidden relative border border-primary/10 flex items-center justify-center cursor-zoom-in group/img hover:bg-muted/30 transition-colors "
            aria-label="Inspect canonical reference image"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={canonicalImageRef}
              key={`canonical-${retryNumber}`}
              src={pair.canonical_signed_url}
              alt="Canonical Reference"
              className="object-contain w-full h-full p-2 transition-transform duration-200 group-hover/img:scale-[1.03]"
              onLoad={onImageStateChange ? () => setImageState("canonical", "ready") : undefined}
              onError={onImageStateChange ? () => setImageState("canonical", "error") : undefined}
            />
            <div className="absolute bottom-2 right-2 opacity-0 group-hover/img:opacity-100 transition-opacity bg-foreground/75 text-surface text-[10px] px-2 py-0.5 rounded-md backdrop-blur-xs font-sans">
              Click to Zoom
            </div>
          </button>

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

          <button
            type="button"
            onClick={() => openImage("scene")}
            className="aspect-square w-full bg-muted/20 rounded-xl overflow-hidden relative border border-primary/10 flex items-center justify-center cursor-zoom-in group/img hover:bg-muted/30 transition-colors "
            aria-label="Inspect generated scene image"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              ref={sceneImageRef}
              key={`scene-${retryNumber}`}
              src={pair.scene_signed_url}
              alt="Generated Scene"
              className="object-contain w-full h-full p-2 transition-transform duration-200 group-hover/img:scale-[1.03]"
              onLoad={onImageStateChange ? () => setImageState("scene", "ready") : undefined}
              onError={onImageStateChange ? () => setImageState("scene", "error") : undefined}
            />
            <div className="absolute bottom-2 right-2 opacity-0 group-hover/img:opacity-100 transition-opacity bg-foreground/75 text-surface text-[10px] px-2 py-0.5 rounded-md backdrop-blur-xs font-sans">
              Click to Zoom
            </div>
          </button>

          <p className="text-center text-xs text-foreground/60 leading-relaxed">
            Model output to be evaluated
          </p>
        </div>
      </div>
      {onImageStateChange && demoImageState === "loading" && (
        <p role="status" className="text-center text-xs text-foreground/70" aria-live="polite">
          Loading synthetic sample images…
        </p>
      )}
      {onImageStateChange && demoImageState === "error" && (
        <div role="alert" className="flex flex-col items-center gap-2 rounded-xl border border-warning/30 bg-warning/5 p-3 text-center text-sm text-foreground">
          <span>A sample image could not be loaded.</span>
          <button
            type="button"
            onClick={retryImages}
            className="min-h-11 rounded-lg border border-primary/20 bg-surface px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary/10 "
          >
            Retry sample images
          </button>
        </div>
      )}
    </div>
  );
}
