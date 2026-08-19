"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Info,
  Keyboard,
  MagnifyingGlassPlus,
  X,
  BookOpen,
  WarningCircle,
  SignOut,
} from "@phosphor-icons/react";
import { submitAdjudication, type BlindAnnotation } from "./actions";

export type ResearchPair = {
  id: string;
  canonical_signed_url: string;
  scene_signed_url: string;
};

type TaxonomyState = {
  wrong_colour: boolean;
  wrong_species: boolean;
  wrong_body_feature: boolean;
  wrong_clothing: boolean;
  wrong_style: boolean;
  different_face: boolean;
  character_absent: boolean;
};

const INITIAL_TAXONOMY: TaxonomyState = {
  wrong_colour: false,
  wrong_species: false,
  wrong_body_feature: false,
  wrong_clothing: false,
  wrong_style: false,
  different_face: false,
  character_absent: false,
};

const TAXONOMY_LABELS: Record<
  keyof TaxonomyState,
  { label: string; shortcut: string; example: string; description: string }
> = {
  wrong_colour: {
    label: "Wrong Color",
    shortcut: "1",
    example: "Cream chest patch is rendered brown; fur hue shifted",
    description: "Fur, hair, skin, or dominant color differs from reference",
  },
  wrong_species: {
    label: "Wrong Species",
    shortcut: "2",
    example: "Fox cub rendered as a dog; animal silhouette altered",
    description: "Species, animal type, or defining core silhouette is altered",
  },
  wrong_body_feature: {
    label: "Wrong Body Feature",
    shortcut: "3",
    example: "Two eyes instead of three; tail or wings missing/added",
    description: "Countable or structural body parts (ears, tail, horns, snout, wings, limbs)",
  },
  wrong_clothing: {
    label: "Wrong Clothing/Accessories",
    shortcut: "4",
    example: "Striped scarf absent, recolored, or hat missing",
    description: "Attire, hat, collar, glasses, or signature accessories missing or altered",
  },
  wrong_style: {
    label: "Wrong Style",
    shortcut: "5",
    example: "Photorealistic rendering rather than flat storybook gouache",
    description: "Art style, rendering medium, line weight, or texture differs from reference",
  },
  different_face: {
    label: "Different Face",
    shortcut: "6",
    example: "Same species, but facial expression identity or eyes belong to an unrelated individual",
    description: "Facial structure, muzzle shape, eye style, or facial markings mismatch",
  },
  character_absent: {
    label: "Character Absent",
    shortcut: "7",
    example: "Main character does not appear in the scene at all",
    description: "Main character is completely absent from the composition",
  },
};

function hasConflict(a: BlindAnnotation, b: BlindAnnotation, field: keyof BlindAnnotation) {
  if (field === "failure_reasons") {
    const aSorted = Array.from(new Set(a.failure_reasons || [])).sort();
    const bSorted = Array.from(new Set(b.failure_reasons || [])).sort();
    return JSON.stringify(aSorted) !== JSON.stringify(bSorted);
  }
  return a[field] !== b[field];
}

function formatReasons(reasons: string[] | undefined) {
  const set = Array.from(new Set(reasons || []));
  if (set.length === 0) return "None";
  return set
    .map((k) => TAXONOMY_LABELS[k as keyof TaxonomyState]?.label || k)
    .join(", ");
}

export default function AdjudicateClient({
  pair,
  annotationA,
  annotationB,
}: {
  pair: ResearchPair;
  annotationA: BlindAnnotation;
  annotationB: BlindAnnotation;
}) {
  const router = useRouter();
  const [explicitSameCharacter, setExplicitSameCharacter] = useState(false);
  const [taxonomy, setTaxonomy] = useState<TaxonomyState>(INITIAL_TAXONOMY);
  const [brokenAnatomy, setBrokenAnatomy] = useState(false);
  const [textVisible, setTextVisible] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const [showShortcutsModal, setShowShortcutsModal] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [activeLightboxTab, setActiveLightboxTab] = useState<"side-by-side" | "canonical" | "scene">("side-by-side");

  const failureReasons = (Object.keys(taxonomy) as Array<keyof TaxonomyState>).filter(
    (k) => taxonomy[k]
  );
  const sameCharacter = explicitSameCharacter;
  const isSubmissionValid = sameCharacter || failureReasons.length > 0;

  const toggleSameCharacter = useCallback(() => {
    setExplicitSameCharacter((prev) => {
      if (!prev) {
        setTaxonomy(INITIAL_TAXONOMY);
        return true;
      }
      return false;
    });
  }, []);

  const toggleTaxonomy = useCallback((key: keyof TaxonomyState) => {
    setExplicitSameCharacter(false);
    setTaxonomy((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  const handleSubmit = useCallback(async () => {
    if (isPending) return;
    setError(null);
    startTransition(async () => {
      const result = await submitAdjudication(
        pair.id,
        failureReasons,
        sameCharacter,
        !brokenAnatomy,
        !textVisible
      );
      if (result.error) {
        setError(result.error);
        return;
      }
      setTaxonomy(INITIAL_TAXONOMY);
      setExplicitSameCharacter(false);
      setBrokenAnatomy(false);
      setTextVisible(false);
      setLightboxOpen(false);
      router.refresh();
    });
  }, [isPending, pair.id, failureReasons, sameCharacter, brokenAnatomy, textVisible, router]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === "Escape") {
        if (showShortcutsModal) {
          setShowShortcutsModal(false);
          return;
        }
        if (lightboxOpen) {
          setLightboxOpen(false);
          return;
        }
      }

      if (e.key === "?" && !isPending) {
        e.preventDefault();
        setShowShortcutsModal((prev) => !prev);
        return;
      }

      if (e.key === " " && !isPending && !showShortcutsModal) {
        e.preventDefault();
        setLightboxOpen((prev) => !prev);
        return;
      }

      if (e.key === "Enter" && !isPending && isSubmissionValid) {
        e.preventDefault();
        handleSubmit();
        return;
      }

      if (e.key === "0" && !isPending) {
        e.preventDefault();
        toggleSameCharacter();
        return;
      }

      if (e.key.toLowerCase() === "a" && !isPending) {
        e.preventDefault();
        setBrokenAnatomy((p) => !p);
        return;
      }

      if (e.key.toLowerCase() === "t" && !isPending) {
        e.preventDefault();
        setTextVisible((p) => !p);
        return;
      }

      const entry = Object.entries(TAXONOMY_LABELS).find(([, v]) => v.shortcut === e.key);
      if (entry && !isPending) {
        e.preventDefault();
        toggleTaxonomy(entry[0] as keyof TaxonomyState);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSubmit, toggleSameCharacter, toggleTaxonomy, isPending, showShortcutsModal, lightboxOpen, isSubmissionValid]);

  return (
    <div className="w-full flex flex-col flex-1 pb-20">
      {/* Sticky Top Navigation */}
      <header className="sticky top-0 z-30 bg-surface/90 backdrop-blur-md border-b border-admin/10 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/research"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-semibold text-admin hover:bg-admin/10 transition-colors"
            >
              <ArrowLeft weight="bold" className="size-4" />
              <span className="hidden sm:inline">Research Lab</span>
            </Link>

            <div className="h-4 w-px bg-admin/20 hidden sm:block" />

            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-foreground text-sm md:text-base">
                Conflict Adjudication
              </span>
              <span className="px-2 py-0.5 rounded-md bg-warning/15 text-warning-deep text-xs font-mono font-semibold uppercase tracking-wider">
                Authoritative
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Keyboard Shortcuts trigger */}
            <button
              onClick={() => setShowShortcutsModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-admin/20 bg-surface text-foreground/80 hover:text-foreground hover:bg-admin/5 text-xs font-medium transition-all"
              title="View Keyboard Shortcuts & Guide (?)"
            >
              <Keyboard className="size-4 text-admin" weight="duotone" />
              <span className="hidden md:inline">Shortcuts &amp; Guide</span>
              <kbd className="px-1.5 py-0.5 rounded bg-muted/60 text-[10px] font-mono border border-foreground/15">
                ?
              </kbd>
            </button>

            {/* Logout trigger */}
            <form action="/auth/signout" method="post" className="inline-flex">
              <button
                type="submit"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-destructive/20 bg-surface text-destructive hover:bg-destructive/10 text-xs font-medium transition-all"
                title="Log Out"
              >
                <SignOut className="size-4" weight="bold" />
                <span className="hidden md:inline">Log Out</span>
              </button>
            </form>
          </div>
        </div>
      </header>

      {/* Main Workstation Stage */}
      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8 flex-1 flex flex-col gap-6">
        
        {/* Horizontal Conflict Summary Banner */}
        <div className="bg-warning/10 border border-warning/30 rounded-2xl p-4 flex flex-col gap-3 neo-shadow-sm">
          <div className="flex items-center gap-2 text-warning-deep border-b border-warning/20 pb-2">
            <WarningCircle weight="bold" className="size-5" />
            <h3 className="font-display font-extrabold text-sm tracking-wide uppercase">Conflicts Detected</h3>
          </div>
          
          <div className="flex flex-wrap gap-x-8 gap-y-3 text-xs md:text-sm">
            {hasConflict(annotationA, annotationB, "same_character") && (
              <div className="flex flex-col gap-1.5">
                <div className="text-warning-deep font-bold uppercase tracking-wider text-[10px]">Same Character</div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-bold text-foreground/50 text-xs">A1</span> <span className="text-foreground">{annotationA.same_character ? "Yes" : "No"}</span>
                  <span className="text-foreground/20">|</span>
                  <span className="font-bold text-foreground/50 text-xs">A2</span> <span className="text-foreground">{annotationB.same_character ? "Yes" : "No"}</span>
                </div>
              </div>
            )}
            {hasConflict(annotationA, annotationB, "failure_reasons") && (
              <div className="flex flex-col gap-1.5">
                <div className="text-warning-deep font-bold uppercase tracking-wider text-[10px]">Failure Reasons</div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-bold text-foreground/50 text-xs">A1</span> <span className="text-foreground truncate max-w-[200px]" title={formatReasons(annotationA.failure_reasons)}>{formatReasons(annotationA.failure_reasons)}</span>
                  <span className="text-foreground/20">|</span>
                  <span className="font-bold text-foreground/50 text-xs">A2</span> <span className="text-foreground truncate max-w-[200px]" title={formatReasons(annotationB.failure_reasons)}>{formatReasons(annotationB.failure_reasons)}</span>
                </div>
              </div>
            )}
            {hasConflict(annotationA, annotationB, "anatomy_intact") && (
              <div className="flex flex-col gap-1.5">
                <div className="text-warning-deep font-bold uppercase tracking-wider text-[10px]">Broken Anatomy</div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-bold text-foreground/50 text-xs">A1</span> <span className="text-foreground">{!annotationA.anatomy_intact ? "Broken" : "Intact"}</span>
                  <span className="text-foreground/20">|</span>
                  <span className="font-bold text-foreground/50 text-xs">A2</span> <span className="text-foreground">{!annotationB.anatomy_intact ? "Broken" : "Intact"}</span>
                </div>
              </div>
            )}
            {hasConflict(annotationA, annotationB, "text_free") && (
              <div className="flex flex-col gap-1.5">
                <div className="text-warning-deep font-bold uppercase tracking-wider text-[10px]">Text Visible</div>
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-bold text-foreground/50 text-xs">A1</span> <span className="text-foreground">{!annotationA.text_free ? "Visible" : "None"}</span>
                  <span className="text-foreground/20">|</span>
                  <span className="font-bold text-foreground/50 text-xs">A2</span> <span className="text-foreground">{!annotationB.text_free ? "Visible" : "None"}</span>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
          
          {/* Left Column: Image Comparison */}
          <div className="lg:col-span-7 flex flex-col gap-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-display font-extrabold text-lg text-foreground tracking-tight">
                  Visual Comparison
                </span>
              </div>
              <button
                onClick={() => setLightboxOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold text-primary hover:bg-primary/10 transition-colors"
                title="Expand side-by-side view (Space)"
              >
                <MagnifyingGlassPlus weight="bold" className="size-3.5" />
                <span>Inspect (Space)</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 md:gap-5">
              <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-4 flex flex-col gap-3 group">
                <div className="flex items-center justify-between">
                  <h3 className="font-display font-bold text-sm text-foreground">Canonical Reference</h3>
                </div>
                <div
                  onClick={() => {
                    setActiveLightboxTab("canonical");
                    setLightboxOpen(true);
                  }}
                  className="aspect-square w-full bg-muted/30 rounded-xl overflow-hidden relative border border-primary/10 flex items-center justify-center cursor-zoom-in group/img"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={pair.canonical_signed_url}
                    alt="Canonical Reference"
                    className="object-contain w-full h-full p-2 transition-transform duration-200 group-hover/img:scale-[1.02]"
                  />
                </div>
              </div>

              <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-4 flex flex-col gap-3 group">
                <div className="flex items-center justify-between">
                  <h3 className="font-display font-bold text-sm text-foreground">Generated Scene</h3>
                </div>
                <div
                  onClick={() => {
                    setActiveLightboxTab("scene");
                    setLightboxOpen(true);
                  }}
                  className="aspect-square w-full bg-muted/30 rounded-xl overflow-hidden relative border border-primary/10 flex items-center justify-center cursor-zoom-in group/img"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={pair.scene_signed_url}
                    alt="Generated Scene"
                    className="object-contain w-full h-full p-2 transition-transform duration-200 group-hover/img:scale-[1.02]"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Controls */}
          <div className="lg:col-span-5 flex flex-col font-sans">
            <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-5 md:p-6 flex flex-col gap-6 h-full">
              <div className="border-b border-primary/10 pb-3">
                <h2 className="font-display font-extrabold text-xl text-foreground tracking-tight">
                  Authoritative Label
                </h2>
                <p className="text-xs text-foreground/70 mt-1 leading-relaxed">
                  Resolve the conflict by selecting the final ground truth label.
                </p>
              </div>

              {/* TIER 1: Primary Identity Gate (Key 0) */}
              <div>
                <label
                  className={`relative flex items-center gap-3.5 p-3.5 rounded-xl border-2 transition-all cursor-pointer select-none ${
                    explicitSameCharacter
                      ? "bg-success/15 border-success text-foreground shadow-sm"
                      : "bg-surface border-muted hover:border-primary/40 hover:bg-primary/5 text-foreground"
                  } ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={explicitSameCharacter}
                    onChange={toggleSameCharacter}
                    disabled={isPending}
                    className="size-5 rounded border-muted text-success focus:ring-success accent-success"
                  />
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-bold text-foreground block">Same Character</span>
                  </div>
                  <kbd className="px-2.5 py-1 bg-surface border border-foreground/15 rounded-lg text-xs font-mono font-bold text-foreground/80 neo-shadow-xs">0</kbd>
                </label>
              </div>

              {/* TIER 2: Failure Reasons */}
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-foreground/70">Drift Reasons</span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {(Object.entries(TAXONOMY_LABELS) as [keyof TaxonomyState, { label: string; shortcut: string }][]).map(([key, { label, shortcut }]) => (
                    <label
                      key={key}
                      className={`flex items-center gap-3 px-3 py-2 rounded-xl border transition-all cursor-pointer select-none group ${
                        taxonomy[key]
                          ? "bg-primary/5 border-primary/40 text-foreground font-semibold shadow-sm"
                          : "bg-surface/60 border-muted hover:border-primary/30 hover:bg-primary/5 text-foreground/80"
                      } ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}
                    >
                      <input
                        type="checkbox"
                        checked={taxonomy[key]}
                        onChange={() => toggleTaxonomy(key)}
                        disabled={isPending}
                        className="size-4.5 rounded border-muted text-primary focus:ring-primary accent-primary"
                      />
                      <span className="flex-1 text-xs sm:text-sm font-medium text-foreground">{label}</span>
                      <kbd className="px-2 py-0.5 bg-surface border border-foreground/15 rounded text-xs text-foreground/70 font-mono">{shortcut}</kbd>
                    </label>
                  ))}
                </div>
              </div>

              {/* TIER 3: Quality Gates */}
              <div className="pt-2 border-t border-primary/10 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-bold uppercase tracking-wider text-foreground/70">Artifact Gates</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <label className={`flex items-center gap-2.5 p-2.5 rounded-xl border transition-all cursor-pointer select-none ${brokenAnatomy ? "bg-warning/15 border-warning/50 text-foreground font-medium" : "bg-surface/60 border-muted hover:border-primary/30 hover:bg-primary/5 text-foreground/80"} ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}>
                    <input type="checkbox" checked={brokenAnatomy} onChange={() => setBrokenAnatomy(p => !p)} disabled={isPending} className="size-4 rounded border-muted text-warning focus:ring-warning accent-warning" />
                    <span className="flex-1 text-xs font-medium text-foreground">Broken Anatomy</span>
                    <kbd className="px-1.5 py-0.5 bg-surface border border-foreground/15 rounded text-[11px] text-foreground/70 font-mono">A</kbd>
                  </label>
                  <label className={`flex items-center gap-2.5 p-2.5 rounded-xl border transition-all cursor-pointer select-none ${textVisible ? "bg-warning/15 border-warning/50 text-foreground font-medium" : "bg-surface/60 border-muted hover:border-primary/30 hover:bg-primary/5 text-foreground/80"} ${isPending ? "opacity-50 cursor-not-allowed" : ""}`}>
                    <input type="checkbox" checked={textVisible} onChange={() => setTextVisible(p => !p)} disabled={isPending} className="size-4 rounded border-muted text-warning focus:ring-warning accent-warning" />
                    <span className="flex-1 text-xs font-medium text-foreground">Text Visible</span>
                    <kbd className="px-1.5 py-0.5 bg-surface border border-foreground/15 rounded text-[11px] text-foreground/70 font-mono">T</kbd>
                  </label>
                </div>
              </div>

              {/* Verdict & Submit */}
              <div className="pt-4 border-t border-primary/10 flex flex-col gap-3">
                {sameCharacter ? (
                  <div className="p-3 rounded-xl bg-success/15 border border-success/30 flex items-center gap-2 text-success font-display font-bold text-sm">
                    <CheckCircle weight="fill" className="size-5 shrink-0" />
                    <span>Verdict: Same Character</span>
                  </div>
                ) : failureReasons.length > 0 ? (
                  <div className="p-3 rounded-xl bg-destructive/15 border border-destructive/30 flex items-center gap-2 text-destructive font-display font-bold text-sm">
                    <XCircle weight="fill" className="size-5 shrink-0" />
                    <span>Verdict: Different Character ({failureReasons.length} issue{failureReasons.length > 1 ? "s" : ""})</span>
                  </div>
                ) : (
                  <div className="p-3 rounded-xl bg-muted/40 border border-muted flex items-center gap-2 text-foreground/60 text-xs">
                    <Info weight="duotone" className="size-4 text-primary shrink-0" />
                    <span>Select <strong>Same Character (0)</strong> or failure reasons <strong>(1-7)</strong> to submit.</span>
                  </div>
                )}

                {error && (
                  <div role="alert" className="p-3 rounded-xl bg-destructive/10 border border-destructive/30 text-destructive text-xs font-medium flex items-center gap-2 animate-in fade-in slide-in-from-top-1 duration-200">
                    <XCircle weight="bold" className="size-4 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <button
                  onClick={handleSubmit}
                  disabled={isPending || !isSubmissionValid}
                  className={`w-full py-3.5 px-4 rounded-xl font-display font-bold text-sm sm:text-base transition-all flex items-center justify-center gap-2.5 active:scale-[0.98] ${
                    isPending
                      ? "bg-muted text-foreground/40 border border-muted cursor-not-allowed"
                      : !isSubmissionValid
                      ? "bg-surface text-foreground/40 border border-muted cursor-not-allowed"
                      : "bg-secondary text-foreground hover:brightness-95 cursor-pointer neo-shadow-sm shadow-secondary/20"
                  }`}
                >
                  <span>{isPending ? "Submitting..." : "Submit Final Decision"}</span>
                  <kbd className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${isSubmissionValid && !isPending ? "bg-foreground/10 text-foreground" : "bg-foreground/5 text-foreground/40"}`}>
                    Enter ↵
                  </kbd>
                </button>
              </div>

            </div>
          </div>
        </div>
      </main>

      {/* Lightbox / Full-Screen Inspection Modal */}
      {lightboxOpen && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 bg-foreground/80 backdrop-blur-md flex flex-col p-4 md:p-8 animate-in fade-in duration-200">
          <div className="flex items-center justify-between pb-4 text-surface border-b border-surface/20">
            <div className="flex items-center gap-3">
              <h3 className="font-display font-extrabold text-lg">High-Resolution Image Inspector</h3>
              <div className="flex items-center rounded-lg bg-surface/10 p-1 border border-surface/20">
                <button onClick={() => setActiveLightboxTab("side-by-side")} className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${activeLightboxTab === "side-by-side" ? "bg-surface text-foreground" : "text-surface/80 hover:text-surface"}`}>Side-by-Side</button>
                <button onClick={() => setActiveLightboxTab("canonical")} className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${activeLightboxTab === "canonical" ? "bg-surface text-foreground" : "text-surface/80 hover:text-surface"}`}>Reference</button>
                <button onClick={() => setActiveLightboxTab("scene")} className={`px-3 py-1 rounded-md text-xs font-semibold transition-colors ${activeLightboxTab === "scene" ? "bg-surface text-foreground" : "text-surface/80 hover:text-surface"}`}>Scene</button>
              </div>
            </div>
            <button onClick={() => setLightboxOpen(false)} className="p-2 rounded-xl bg-surface/10 hover:bg-surface/20 text-surface transition-colors" title="Close (Esc)">
              <X weight="bold" className="size-5" />
            </button>
          </div>
          <div className="flex-1 overflow-auto flex items-center justify-center p-4">
            {activeLightboxTab === "side-by-side" ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-6xl w-full h-full max-h-[80vh]">
                <div className="bg-surface rounded-2xl p-4 flex flex-col items-center justify-center gap-2 overflow-hidden">
                  <span className="font-display font-bold text-xs text-primary uppercase">Canonical Reference</span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={pair.canonical_signed_url} alt="Canonical Reference" className="object-contain w-full h-full max-h-[70vh]" />
                </div>
                <div className="bg-surface rounded-2xl p-4 flex flex-col items-center justify-center gap-2 overflow-hidden">
                  <span className="font-display font-bold text-xs text-primary uppercase">Generated Scene</span>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={pair.scene_signed_url} alt="Generated Scene" className="object-contain w-full h-full max-h-[70vh]" />
                </div>
              </div>
            ) : activeLightboxTab === "canonical" ? (
              <div className="bg-surface rounded-2xl p-6 max-w-3xl w-full max-h-[80vh] flex flex-col items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={pair.canonical_signed_url} alt="Canonical Reference" className="object-contain w-full h-full max-h-[75vh]" />
              </div>
            ) : (
              <div className="bg-surface rounded-2xl p-6 max-w-3xl w-full max-h-[80vh] flex flex-col items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={pair.scene_signed_url} alt="Generated Scene" className="object-contain w-full h-full max-h-[75vh]" />
              </div>
            )}
          </div>
        </div>
      )}

      {/* Shortcuts Modal */}
      {showShortcutsModal && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 bg-foreground/60 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150">
          <div className="bg-surface rounded-2xl neo-border neo-shadow-lg max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
            <div className="p-6 border-b border-primary/10 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <BookOpen className="size-5 text-primary" weight="duotone" />
                <h3 className="font-display font-extrabold text-lg text-foreground">Shortcuts &amp; Guide</h3>
              </div>
              <button onClick={() => setShowShortcutsModal(false)} className="p-1.5 rounded-lg text-foreground/50 hover:text-foreground hover:bg-muted/60 transition-colors" title="Close (Esc)">
                <X weight="bold" className="size-4" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto space-y-6 text-sm">
              <div className="space-y-2.5">
                <span className="text-xs font-mono uppercase font-bold text-foreground/70">Keyboard Shortcuts</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                    <span className="font-medium text-foreground text-xs">Same Character</span><kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">0</kbd>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                    <span className="font-medium text-foreground text-xs">Drift Reasons (1–7)</span><kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">1 – 7</kbd>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                    <span className="font-medium text-foreground text-xs">Broken Anatomy</span><kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">A</kbd>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                    <span className="font-medium text-foreground text-xs">Text Visible</span><kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">T</kbd>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                    <span className="font-medium text-foreground text-xs">Submit Annotation</span><kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">Enter</kbd>
                  </div>
                  <div className="flex items-center justify-between p-2.5 rounded-lg bg-surface border border-muted">
                    <span className="font-medium text-foreground text-xs">Image Lightbox</span><kbd className="px-2 py-0.5 rounded bg-muted/70 font-mono text-xs font-bold text-foreground">Space</kbd>
                  </div>
                </div>
              </div>
            </div>
            <div className="p-4 border-t border-primary/10 bg-muted/20 flex justify-end">
              <button onClick={() => setShowShortcutsModal(false)} className="px-6 py-2.5 rounded-xl bg-primary text-surface font-semibold text-sm hover:bg-primary-deep transition-all">Close Guide</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
