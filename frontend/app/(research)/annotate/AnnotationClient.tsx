"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Keyboard, SignOut } from "@phosphor-icons/react";
import { submitAnnotation } from "./actions";
import { ResearchPair, TaxonomyState, INITIAL_TAXONOMY, TAXONOMY_LABELS } from "../_shared/constants";
import { LightboxModal } from "../_shared/components/LightboxModal";
import { ShortcutsModal } from "../_shared/components/ShortcutsModal";
import { ImageCards } from "../_shared/components/ImageCards";
import { VerdictBar } from "../_shared/components/VerdictBar";
import { TaxonomyControls } from "../_shared/components/TaxonomyControls";

export default function AnnotationClient({ pair }: { pair: ResearchPair }) {
  const router = useRouter();
  const [isSameCharacterSelected, setIsSameCharacterSelected] = useState(false);
  const [explicitSameCharacter, setExplicitSameCharacter] = useState(false);
  const [taxonomy, setTaxonomy] = useState<TaxonomyState>(INITIAL_TAXONOMY);
  const [brokenAnatomy, setBrokenAnatomy] = useState(false);
  const [textVisible, setTextVisible] = useState(false);
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const [sessionCount, setSessionCount] = useState(0);
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
      const result = await submitAnnotation({
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

      setSessionCount((prev) => prev + 1);
      setTaxonomy(INITIAL_TAXONOMY);
      setIsSameCharacterSelected(false);
      setExplicitSameCharacter(false);
      setBrokenAnatomy(false);
      setTextVisible(false);
      setLightboxOpen(false);
      router.refresh();
    });
  }, [
    isPending,
    isSubmissionValid,
    pair.id,
    failureReasons,
    explicitSameCharacter,
    brokenAnatomy,
    textVisible,
    router,
  ]);

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
        // Auto select "Different Character" if a taxonomy shortcut is pressed and nothing is selected yet
        if (!isSameCharacterSelected || explicitSameCharacter) {
          setIsSameCharacterSelected(true);
          handleSetExplicitSameCharacter(false);
        }
        toggleTaxonomy(entry[0] as keyof TaxonomyState);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    handleSubmit,
    handleSetExplicitSameCharacter,
    toggleTaxonomy,
    isPending,
    showShortcutsModal,
    lightboxOpen,
    isSubmissionValid,
    isSameCharacterSelected,
    explicitSameCharacter
  ]);

  return (
    <div className="w-full flex flex-col flex-1">
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
                Pairwise Consistency
              </span>
              <span className="px-2 py-0.5 rounded-md bg-admin/10 text-admin text-xs font-mono font-semibold uppercase tracking-wider">
                Double-Blind
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-xl bg-admin/5 border border-admin/20 text-xs font-medium text-foreground/80 neo-shadow-xs">
              Session: <strong className="text-foreground">{sessionCount}</strong> completed
            </div>

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

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8 flex-1 flex flex-col">
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
                  Identity Evaluation
                </h2>
                <p className="text-xs text-foreground/70 mt-1 leading-relaxed">
                  Classify character consistency according to the pre-registered study rubric.
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
