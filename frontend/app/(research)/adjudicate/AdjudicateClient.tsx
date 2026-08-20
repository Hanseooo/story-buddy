"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Keyboard, WarningCircle, SignOut } from "@phosphor-icons/react";
import { submitAdjudication, type BlindAnnotation } from "./actions";
import { ResearchPair, TaxonomyState, INITIAL_TAXONOMY, TAXONOMY_LABELS } from "../_shared/constants";
import { LightboxModal } from "../_shared/components/LightboxModal";
import { ShortcutsModal } from "../_shared/components/ShortcutsModal";
import { ImageCards } from "../_shared/components/ImageCards";
import { VerdictBar } from "../_shared/components/VerdictBar";
import { TaxonomyControls } from "../_shared/components/TaxonomyControls";

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
  const [isSameCharacterSelected, setIsSameCharacterSelected] = useState(false);
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
  const isSubmissionValid = isSameCharacterSelected && (explicitSameCharacter || failureReasons.length > 0);

  const handleSetExplicitSameCharacter = useCallback((val: boolean) => {
    setExplicitSameCharacter(val);
    if (val) {
      setTaxonomy(INITIAL_TAXONOMY);
    }
  }, []);

  const toggleTaxonomy = useCallback((key: keyof TaxonomyState) => {
    if (explicitSameCharacter || !isSameCharacterSelected) return;
    setTaxonomy((prev) => ({ ...prev, [key]: !prev[key] }));
  }, [explicitSameCharacter, isSameCharacterSelected]);

  const handleSubmit = useCallback(async () => {
    if (isPending || !isSubmissionValid) return;
    setError(null);
    startTransition(async () => {
      const result = await submitAdjudication({
        pairId: pair.id,
        failureReasons,
        sameCharacter: explicitSameCharacter,
        anatomyIntact: !brokenAnatomy,
        textFree: !textVisible
      });
      if (result.error) {
        setError(result.error);
        return;
      }
      setTaxonomy(INITIAL_TAXONOMY);
      setIsSameCharacterSelected(false);
      setExplicitSameCharacter(false);
      setBrokenAnatomy(false);
      setTextVisible(false);
      setLightboxOpen(false);
      router.refresh();
    });
  }, [isPending, isSubmissionValid, pair.id, failureReasons, explicitSameCharacter, brokenAnatomy, textVisible, router]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === "Escape") {
        if (showShortcutsModal) { setShowShortcutsModal(false); return; }
        if (lightboxOpen) { setLightboxOpen(false); return; }
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

      if (e.key === "D" && e.shiftKey && !isPending) {
        e.preventDefault();
        setIsSameCharacterSelected(true);
        handleSetExplicitSameCharacter(false);
        return;
      }

      if (e.key === "0" && !isPending) {
        e.preventDefault();
        setIsSameCharacterSelected(true);
        handleSetExplicitSameCharacter(true);
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
        if (!isSameCharacterSelected || explicitSameCharacter) {
          setIsSameCharacterSelected(true);
          handleSetExplicitSameCharacter(false);
        }
        toggleTaxonomy(entry[0] as keyof TaxonomyState);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSubmit, handleSetExplicitSameCharacter, toggleTaxonomy, isPending, showShortcutsModal, lightboxOpen, isSubmissionValid, isSameCharacterSelected, explicitSameCharacter]);

  return (
    <div className="w-full flex flex-col flex-1 pb-20">
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
            <button
              onClick={() => setShowShortcutsModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-admin/20 bg-surface text-foreground/80 hover:text-foreground hover:bg-admin/5 text-xs font-medium transition-all"
              title="View Keyboard Shortcuts & Guide (?)"
            >
              <Keyboard className="size-4 text-admin" weight="duotone" />
              <span className="hidden md:inline">Shortcuts &amp; Guide</span>
              <kbd className="px-1.5 py-0.5 rounded bg-muted/60 text-[10px] font-mono border border-foreground/15">?</kbd>
            </button>
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

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start flex-1">
          <ImageCards 
            pair={pair} 
            onOpenLightbox={() => setLightboxOpen(true)} 
            setActiveLightboxTab={setActiveLightboxTab} 
          />

          <div className="lg:col-span-5 flex flex-col font-sans h-full">
            <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-5 md:p-6 flex flex-col gap-6 h-full min-h-[500px]">
              <div className="border-b border-primary/10 pb-3">
                <h2 className="font-display font-extrabold text-xl text-foreground tracking-tight">
                  Authoritative Label
                </h2>
                <p className="text-xs text-foreground/70 mt-1 leading-relaxed">
                  Resolve the conflict by selecting the final ground truth label.
                </p>
              </div>

              <TaxonomyControls
                isPending={isPending}
                explicitSameCharacter={explicitSameCharacter}
                setExplicitSameCharacter={handleSetExplicitSameCharacter}
                taxonomy={taxonomy}
                toggleTaxonomy={toggleTaxonomy}
                brokenAnatomy={brokenAnatomy}
                setBrokenAnatomy={setBrokenAnatomy}
                textVisible={textVisible}
                setTextVisible={setTextVisible}
                isSameCharacterSelected={isSameCharacterSelected}
                setIsSameCharacterSelected={setIsSameCharacterSelected}
              />

              <VerdictBar
                sameCharacter={explicitSameCharacter}
                failureReasonsCount={failureReasons.length}
                error={error}
                isPending={isPending}
                isSubmissionValid={isSubmissionValid}
                onSubmit={handleSubmit}
                submitLabel="Submit Final Decision"
              />
            </div>
          </div>
        </div>
      </main>

      <LightboxModal
        isOpen={lightboxOpen}
        onClose={() => setLightboxOpen(false)}
        pair={pair}
        activeTab={activeLightboxTab}
        setActiveTab={setActiveLightboxTab}
      />
      <ShortcutsModal isOpen={showShortcutsModal} onClose={() => setShowShortcutsModal(false)} />
    </div>
  );
}
