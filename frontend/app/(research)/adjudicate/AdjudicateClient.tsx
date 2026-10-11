"use client";

import { useState, useEffect, useCallback, useTransition, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Keyboard, WarningCircle, SignOut, Scales } from "@phosphor-icons/react";
import type { BlindAnnotation } from "./actions";
import { ResearchPair, TaxonomyState, INITIAL_TAXONOMY, TAXONOMY_LABELS } from "../_shared/constants";
import { LightboxModal } from "../_shared/components/LightboxModal";
import { ShortcutsModal } from "../_shared/components/ShortcutsModal";
import { ImageCards } from "../_shared/components/ImageCards";
import { VerdictBar } from "../_shared/components/VerdictBar";
import type { DemoSample } from "../_shared/demoSamples";
import type { SubmissionPayload } from "../_shared/validation";
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

type Props =
  | {
      mode: "live";
      pair: ResearchPair;
      annotationA: BlindAnnotation;
      annotationB: BlindAnnotation;
      submitAction: (payload: SubmissionPayload) => Promise<{ error?: string; success?: boolean }>;
      samples?: never;
    }
  | { mode: "demo"; samples: DemoSample[]; submitAction?: never };

export default function AdjudicateClient(props: Props) {
  const router = useRouter();
  const isDemo = props.mode === "demo";
  const [sessionCount, setSessionCount] = useState(0);
  const demoComplete = isDemo && sessionCount >= props.samples.length;
  const sample = isDemo ? props.samples[Math.min(sessionCount, props.samples.length - 1)] : null;
  const pair = props.mode === "live" ? props.pair : sample!.pair;
  const annotationA = props.mode === "live" ? props.annotationA : sample!.annotationA;
  const annotationB = props.mode === "live" ? props.annotationB : sample!.annotationB;
  const [imageState, setImageState] = useState<"loading" | "ready" | "error">("loading");
  const headingRef = useRef<HTMLHeadingElement>(null);
  const submitLock = useRef(false);
  useEffect(() => {
    if (isDemo) headingRef.current?.focus();
  }, [isDemo, sessionCount]);

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
  const isSubmissionValid = !demoComplete &&
    (!isDemo || imageState === "ready") &&
    isSameCharacterSelected && (explicitSameCharacter || failureReasons.length > 0);

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
    if (submitLock.current || isPending || !isSubmissionValid || lightboxOpen || showShortcutsModal) return;
    if (props.mode === "demo") {
      submitLock.current = true;
      setSessionCount((prev) => prev + 1);
      setTaxonomy(INITIAL_TAXONOMY);
      setIsSameCharacterSelected(false);
      setExplicitSameCharacter(false);
      setBrokenAnatomy(false);
      setTextVisible(false);
      setError(null);
      setLightboxOpen(false);
      setActiveLightboxTab("side-by-side");
      setImageState("loading");
      return;
    }
    setError(null);
    startTransition(async () => {
      const result = await props.submitAction({
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
  }, [isPending, isSubmissionValid, pair.id, failureReasons, explicitSameCharacter, brokenAnatomy, textVisible, router, props, lightboxOpen, showShortcutsModal]);

  useEffect(() => { submitLock.current = false; }, [sessionCount]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.target instanceof HTMLTextAreaElement) return;
      if (e.target instanceof HTMLElement && e.target.isContentEditable) return;
      if (e.target instanceof HTMLInputElement && !["radio", "checkbox", "button", "submit"].includes(e.target.type)) return;

      if (e.key === "Escape") {
        if (showShortcutsModal) { setShowShortcutsModal(false); return; }
        if (lightboxOpen) { setLightboxOpen(false); return; }
      }

      if (demoComplete) return;
      // Preserve native activation for focused buttons and navigation links.
      if (e.target instanceof HTMLElement && (
        ((e.key === "Enter" || e.key === " ") && e.target.closest("button, a")) ||
        (e.key === " " && e.target instanceof HTMLInputElement)
      )) return;

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
        const key = entry[0] as keyof TaxonomyState;
        setTaxonomy((prev) => ({ ...prev, [key]: !prev[key] }));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSubmit, handleSetExplicitSameCharacter, toggleTaxonomy, isPending, showShortcutsModal, lightboxOpen, isSubmissionValid, isSameCharacterSelected, explicitSameCharacter, demoComplete]);

  const sameCharConflict = hasConflict(annotationA, annotationB, "same_character");
  const reasonsConflict = hasConflict(annotationA, annotationB, "failure_reasons");
  const anatomyConflict = hasConflict(annotationA, annotationB, "anatomy_intact");
  const textConflict = hasConflict(annotationA, annotationB, "text_free");

  return (
    <div className="w-full flex flex-col flex-1">
      <header className="sticky top-0 z-30 bg-surface/90 backdrop-blur-md border-b border-admin/10 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-16 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              href="/research"
              aria-label="Research Lab"
              className="inline-flex min-h-11 items-center gap-1.5 px-3 py-1.5 rounded-xl text-sm font-semibold text-admin hover:bg-admin/10 transition-colors"
            >
              <ArrowLeft weight="bold" className="size-4" />
              <span className="hidden sm:inline">Research Lab</span>
            </Link>
            <div className="h-4 w-px bg-admin/20 hidden sm:block" />
            <div className="flex flex-wrap items-center gap-2">
              <Scales weight="duotone" className="size-5 text-admin hidden sm:inline" />
              <span className="font-display font-bold text-foreground text-sm md:text-base">
                Conflict Adjudication
              </span>
              <span className="px-2 py-0.5 rounded-md bg-warning/15 text-warning-deep text-xs font-mono font-semibold uppercase tracking-wider">
                {isDemo ? "Demo" : "Authoritative"}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-xl bg-admin/5 border border-admin/20 text-xs font-medium text-foreground/80 neo-shadow-xs">
              {isDemo ? "Demo: " : "Session: "}<strong className="text-foreground">{sessionCount}</strong> {isDemo ? "examples completed" : "adjudicated"}
            </div>

            <button
              aria-label="Shortcuts and guide"
              onClick={() => setShowShortcutsModal(true)}
              className="inline-flex min-h-11 items-center gap-1.5 px-3 py-1.5 rounded-xl border border-admin/20 bg-surface text-foreground/80 hover:text-foreground hover:bg-admin/5 text-xs font-medium transition-all"
              title="View Keyboard Shortcuts & Guide (?)"
            >
              <Keyboard className="size-4 text-admin" weight="duotone" />
              <span className="hidden md:inline">Shortcuts &amp; Guide</span>
              <kbd className="px-1.5 py-0.5 rounded bg-muted/60 text-[10px] font-mono border border-foreground/15">?</kbd>
            </button>
            <form action="/auth/signout" method="post" className="inline-flex">
              <button
                type="submit"
                className="inline-flex min-h-11 items-center gap-1.5 px-3 py-1.5 rounded-xl border border-destructive/20 bg-surface text-destructive hover:bg-destructive/10 text-xs font-medium transition-all"
                title="Log Out"
                aria-label="Log out"
              >
                <SignOut className="size-4" weight="bold" />
                <span className="hidden md:inline">Log Out</span>
              </button>
            </form>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-6 md:py-8 flex-1 flex flex-col gap-6">
        {isDemo && (
          <section aria-label="Demo information" className="mb-6 rounded-2xl border border-admin/25 bg-admin/5 p-4 sm:p-5 flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-admin">Demo · Synthetic samples · Nothing is saved</p>
              <h1 ref={headingRef} tabIndex={-1} aria-live="polite" className="mt-1 text-lg font-display font-bold focus-visible:outline-secondary focus-visible:outline-3">
                {demoComplete ? "Demo complete — nothing was saved" : `Example ${sessionCount + 1} of ${props.mode === "demo" ? props.samples.length : 0}`}
              </h1>
            </div>
            <div className="flex flex-wrap gap-3">
              {demoComplete && (
                <button
                  type="button"
                  onClick={() => { setSessionCount(0); setImageState("loading"); }}
                  className="min-h-11 px-4 py-2 rounded-xl bg-secondary font-semibold neo-shadow-xs focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3"
                >
                  Restart demo
                </button>
              )}
              <Link href="/adjudicate" prefetch={false} className="min-h-11 inline-flex items-center px-4 py-2 rounded-xl border border-admin/25 font-semibold text-sm text-admin hover:bg-admin/10 focus-visible:outline-secondary focus-visible:outline-3 focus-visible:outline-offset-3">Exit demo</Link>
            </div>
          </section>
        )}
        {!demoComplete && (
          <>
            {/* Structured Conflict Comparison Summary */}
            <section
              aria-label="Annotator Discrepancies"
              className="bg-surface rounded-2xl neo-border neo-shadow-sm p-4 md:p-5 flex flex-col gap-3.5"
            >
              <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-primary/10 pb-2.5">
                <div className="flex items-center gap-2 text-warning-deep">
                  <WarningCircle weight="bold" className="size-5 text-warning" />
                  <h2 className="font-display font-extrabold text-sm tracking-wide uppercase text-foreground">
                    Conflicts Detected
                  </h2>
                </div>
                <span className="text-[11px] font-mono font-medium text-foreground/60">
                  {isDemo ? "Illustrative disagreements — not recorded rater answers" : "Blinded Dual Annotations (A1 vs A2)"}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs md:text-sm">
                {/* Field 1: Same Character */}
                <div
                  className={`p-3 rounded-xl border flex flex-col gap-2 transition-all ${
                    sameCharConflict
                      ? "bg-warning/10 border-warning/40 shadow-xs"
                      : "bg-muted/30 border-muted opacity-80"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold uppercase tracking-wider text-[10px] text-foreground/70">
                      Same Character
                    </span>
                    {sameCharConflict && (
                      <span className="px-1.5 py-0.5 rounded bg-warning/20 text-warning-deep text-[10px] font-bold">
                        Disagreement
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-1.5 bg-surface/80 px-2 py-1 rounded-lg border border-primary/5">
                      <span className="font-mono font-bold text-foreground/50 text-[11px]">A1</span>
                      <span className={`font-semibold ${annotationA.same_character ? "text-success" : "text-destructive"}`}>
                        {annotationA.same_character ? "Yes" : "No"}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 bg-surface/80 px-2 py-1 rounded-lg border border-primary/5">
                      <span className="font-mono font-bold text-foreground/50 text-[11px]">A2</span>
                      <span className={`font-semibold ${annotationB.same_character ? "text-success" : "text-destructive"}`}>
                        {annotationB.same_character ? "Yes" : "No"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Field 2: Failure Reasons */}
                <div
                  className={`p-3 rounded-xl border flex flex-col gap-2 transition-all ${
                    reasonsConflict
                      ? "bg-warning/10 border-warning/40 shadow-xs"
                      : "bg-muted/30 border-muted opacity-80"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold uppercase tracking-wider text-[10px] text-foreground/70">
                      Failure Reasons
                    </span>
                    {reasonsConflict && (
                      <span className="px-1.5 py-0.5 rounded bg-warning/20 text-warning-deep text-[10px] font-bold">
                        Disagreement
                      </span>
                    )}
                  </div>
                  <div className="flex flex-col gap-1.5 text-xs">
                    <div className="flex items-start gap-1.5 bg-surface/80 px-2 py-1 rounded-lg border border-primary/5">
                      <span className="font-mono font-bold text-foreground/50 text-[11px] shrink-0 mt-0.5">A1</span>
                      <span className="text-foreground leading-snug font-medium break-words" title={formatReasons(annotationA.failure_reasons)}>
                        {formatReasons(annotationA.failure_reasons)}
                      </span>
                    </div>
                    <div className="flex items-start gap-1.5 bg-surface/80 px-2 py-1 rounded-lg border border-primary/5">
                      <span className="font-mono font-bold text-foreground/50 text-[11px] shrink-0 mt-0.5">A2</span>
                      <span className="text-foreground leading-snug font-medium break-words" title={formatReasons(annotationB.failure_reasons)}>
                        {formatReasons(annotationB.failure_reasons)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Field 3: Broken Anatomy */}
                <div
                  className={`p-3 rounded-xl border flex flex-col gap-2 transition-all ${
                    anatomyConflict
                      ? "bg-warning/10 border-warning/40 shadow-xs"
                      : "bg-muted/30 border-muted opacity-80"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold uppercase tracking-wider text-[10px] text-foreground/70">
                      Broken Anatomy
                    </span>
                    {anatomyConflict && (
                      <span className="px-1.5 py-0.5 rounded bg-warning/20 text-warning-deep text-[10px] font-bold">
                        Disagreement
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-1.5 bg-surface/80 px-2 py-1 rounded-lg border border-primary/5">
                      <span className="font-mono font-bold text-foreground/50 text-[11px]">A1</span>
                      <span className={`font-semibold ${!annotationA.anatomy_intact ? "text-warning-deep" : "text-foreground/80"}`}>
                        {!annotationA.anatomy_intact ? "Broken" : "Intact"}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 bg-surface/80 px-2 py-1 rounded-lg border border-primary/5">
                      <span className="font-mono font-bold text-foreground/50 text-[11px]">A2</span>
                      <span className={`font-semibold ${!annotationB.anatomy_intact ? "text-warning-deep" : "text-foreground/80"}`}>
                        {!annotationB.anatomy_intact ? "Broken" : "Intact"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Field 4: Text Visible */}
                <div
                  className={`p-3 rounded-xl border flex flex-col gap-2 transition-all ${
                    textConflict
                      ? "bg-warning/10 border-warning/40 shadow-xs"
                      : "bg-muted/30 border-muted opacity-80"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold uppercase tracking-wider text-[10px] text-foreground/70">
                      Text Visible
                    </span>
                    {textConflict && (
                      <span className="px-1.5 py-0.5 rounded bg-warning/20 text-warning-deep text-[10px] font-bold">
                        Disagreement
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="flex items-center gap-1.5 bg-surface/80 px-2 py-1 rounded-lg border border-primary/5">
                      <span className="font-mono font-bold text-foreground/50 text-[11px]">A1</span>
                      <span className={`font-semibold ${!annotationA.text_free ? "text-warning-deep" : "text-foreground/80"}`}>
                        {!annotationA.text_free ? "Visible" : "None"}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 bg-surface/80 px-2 py-1 rounded-lg border border-primary/5">
                      <span className="font-mono font-bold text-foreground/50 text-[11px]">A2</span>
                      <span className={`font-semibold ${!annotationB.text_free ? "text-warning-deep" : "text-foreground/80"}`}>
                        {!annotationB.text_free ? "Visible" : "None"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            {/* Visual Inspection + Decision Panel */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start flex-1">
              <ImageCards
                key={pair.id}
                onImageStateChange={isDemo ? setImageState : undefined}
                pair={pair}
                onOpenLightbox={() => setLightboxOpen(true)}
                setActiveLightboxTab={setActiveLightboxTab}
              />

              <div className="lg:col-span-5 flex flex-col font-sans h-full">
                <div className="bg-surface rounded-2xl neo-border neo-shadow-sm p-5 md:p-6 flex flex-col gap-6 h-full min-h-[500px]">
                  <div className="border-b border-primary/10 pb-3">
                    <h2 className="font-display font-extrabold text-xl text-foreground tracking-tight">
                      {isDemo ? "Practice decision" : "Authoritative Label"}
                    </h2>
                    <p className="text-xs text-foreground/70 mt-1 leading-relaxed">
                      {isDemo ? "Resolve the illustrative conflict using the study rubric. Nothing is saved." : "Resolve the conflict by selecting the final ground truth label."}
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
                    failureReasons={failureReasons}
                    error={error}
                    isPending={isPending}
                    isSubmissionValid={isSubmissionValid}
                    onSubmit={handleSubmit}
                    submitLabel={isDemo ? "Submit demo decision" : "Submit Final Decision"}
                  />
                </div>
              </div>
            </div>
          </>
        )}
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
