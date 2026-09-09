"use client";

/* eslint-disable @next/next/no-img-element */

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useJob, type JobRow } from "@/lib/useJob";
import { displayTitle } from "@/lib/displayTitle";
import FailureScreen from "@/components/FailureScreen";
import { supabase } from "@/lib/supabaseClient";
import { signPaths } from "@/lib/signedUrls";
import { motion, AnimatePresence } from "framer-motion";
import { BookOpen, Users, PaintBrush, MagicWand, Check, MagnifyingGlass } from "@phosphor-icons/react";

// ponytail: 90s is chosen so the line arrives before a child gives up; will fire on slow image calls
const STALL_MS = 90_000;

// Swept-pause synthetic status — replace with real value when data-deletion names it (spec §4.4.4)
const SWEPT_STATUS = "__swept__";

type StepperStep = 1 | 2 | 3 | 4;
type SelectedTrait = { charId: string; attribute: string } | null;
type SubmissionState = "idle" | "sending" | "reconciling" | "unknown";

function getStep(stage: string | null): StepperStep | null {
  if (!stage) return null;
  if (["queued", "input_gate", "analyze", "segment"].some(p => stage.startsWith(p))) return 1;
  if (["char_bible", "char_ref_mod", "reveal"].some(p => stage.startsWith(p))) return 2;
  if (["generate_scene", "consistency_check", "regenerate", "output_mod"].some(p => stage.startsWith(p))) return 3;
  if (stage.startsWith("compose")) return 4;
  return null;
}

function getStepLabel(step: StepperStep, stage: string | null): string {
  if (step === 3) {
    const m = (stage ?? "").match(/:(\d+)\/(\d+)$/);
    if (m) return `Drawing picture ${m[1]} of ${m[2]}`;
    return "Drawing your pictures";
  }
  return [
    "Reading your story",
    "Meeting your characters",
    "Drawing your pictures",
    "Putting your book together",
  ][step - 1];
}

function KineticText({ text, className }: { text: string; className?: string }) {
  const words = text.split(" ");
  return (
    <div className={className + " flex flex-wrap justify-center gap-[0.25em]"}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true" className="flex flex-wrap justify-center gap-[0.25em]">
        {words.map((word, i) => (
          <span key={i} className="flex">
            {Array.from(word).map((letter, j) => (
              <motion.span
                key={j}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{
                  type: "spring",
                  bounce: 0.5,
                  delay: (i * 5 + j) * 0.04,
                }}
                className="inline-block"
              >
                {letter}
              </motion.span>
            ))}
          </span>
        ))}
      </span>
    </div>
  );
}

const ReadingVignette = () => (
  <div className="relative flex flex-col justify-center items-center h-32 w-48 my-4">
    <div className="w-full p-5 bg-[var(--color-surface)] border border-[var(--color-primary)]/20 rounded-[20px] shadow-[0_10px_28px_rgba(49,85,217,0.12)] flex flex-col gap-3 relative overflow-hidden">
      <div className="w-full h-3 bg-[var(--color-muted)] rounded-full opacity-60" />
      <div className="w-5/6 h-3 bg-[var(--color-muted)] rounded-full opacity-60" />
      <div className="w-4/6 h-3 bg-[var(--color-muted)] rounded-full opacity-60" />
    </div>
    <motion.div
      className="absolute z-10 text-[var(--color-primary)] drop-shadow-md"
      animate={{ x: [-40, 40, -40], y: [-10, 10, -10] }}
      transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
    >
      <MagnifyingGlass size={48} weight="duotone" />
    </motion.div>
  </div>
);

const CharactersVignette = () => (
  <div className="relative w-48 h-32 my-4 flex items-center justify-center">
    {[
      { rotate: -15, x: -30, delay: 0 },
      { rotate: 0, x: 0, delay: 0.15 },
      { rotate: 15, x: 30, delay: 0.3 }
    ].map((card, i) => (
      <motion.div
        key={i}
        className="absolute w-12 h-16"
        initial={{ y: 20, opacity: 0, rotate: 0, x: 0 }}
        animate={{ y: 0, opacity: 1, rotate: card.rotate, x: card.x }}
        transition={{ 
          y: { type: "spring", bounce: 0.3, delay: card.delay },
          opacity: { duration: 0.4, delay: card.delay },
          rotate: { type: "spring", bounce: 0.3, delay: card.delay },
          x: { type: "spring", bounce: 0.3, delay: card.delay }
        }}
        style={{ zIndex: i }}
      >
        <motion.div
          className="w-full h-full bg-[var(--color-surface)] border border-[var(--color-primary)]/20 rounded-[12px] shadow-[0_10px_28px_rgba(49,85,217,0.12)] flex items-center justify-center"
          animate={{ y: [-4, 4, -4], rotate: [-2, 2, -2] }}
          transition={{ repeat: Infinity, duration: 3, delay: i * 0.5, ease: "easeInOut" }}
        >
          <motion.div 
            className="w-6 h-6 rounded-full bg-[var(--color-primary)]/10"
            animate={{ scale: [0.85, 1.15, 0.85], opacity: [0.4, 1, 0.4] }}
            transition={{ repeat: Infinity, duration: 2, delay: card.delay, ease: "easeInOut" }}
          />
        </motion.div>
      </motion.div>
    ))}
  </div>
);

const DrawingVignette = () => (
  <div className="relative w-48 h-32 flex flex-col items-center justify-center my-4">
    <motion.div
      className="absolute top-0 z-10 text-[var(--color-primary)] origin-bottom drop-shadow-md"
      animate={{ x: [-40, 40, -40], rotate: [-15, 15, -15] }}
      transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
    >
      <PaintBrush size={48} weight="duotone" />
    </motion.div>
    <div className="w-36 h-24 mt-8 border border-[var(--color-primary)]/20 rounded-[16px] overflow-hidden bg-[var(--color-surface)] shadow-[0_10px_28px_rgba(49,85,217,0.12)] relative">
      <motion.div
        className="absolute inset-0 bg-[var(--color-secondary)]/30 origin-left"
        animate={{ scaleX: [0, 1, 1] }}
        transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
      />
    </div>
  </div>
);

const StackingVignette = () => (
  <div className="relative w-32 h-32 my-4 flex justify-center">
    {[0, 1, 2, 3].map((i) => {
      const isCover = i === 3;
      return (
        <motion.div
          key={i}
          className={`absolute h-24 w-20 border border-[var(--color-primary)]/20 rounded-[8px] shadow-[0_6px_18px_rgba(49,85,217,0.10)] overflow-hidden ${isCover ? 'bg-[var(--color-primary)]' : 'bg-[var(--color-surface)]'}`}
          animate={{ 
            y: [-40, i * 4, i * 4], 
            opacity: [0, 1, 0],
            rotate: [0, isCover ? 0 : (i % 2 === 0 ? -4 : 4), isCover ? 0 : (i % 2 === 0 ? -4 : 4)]
          }}
          transition={{
            repeat: Infinity,
            duration: 3,
            times: [0, 0.4, 1],
            delay: i * 0.3,
            ease: "easeInOut"
          }}
          style={{ zIndex: i, top: 20 }}
        >
          {isCover && (
             <div className="absolute left-1.5 top-0 bottom-0 w-1.5 bg-black/20" />
          )}
        </motion.div>
      );
    })}
  </div>
);

export default function ProcessingPage({ params }: { params: Promise<{ profileId: string; jobId: string }> }) {
  const { profileId, jobId } = use(params);
  const { bucket, row, refetch } = useJob(jobId);
  const router = useRouter();

  // Prevent the stepper from flashing during a redraw (spec §4.2). Holds the stage the job was
  // paused on when we confirmed; the bridge lifts the moment the backend reports a different one.
  // It must be state, not a ref: a ref cannot re-render the thing that reads it, so the bridge
  // would only ever lift on some *other* render.
  const [bridgeStage, setBridgeStage] = useState<string | null>(null);
  const [submissionState, setSubmissionState] = useState<SubmissionState>("idle");
  const [confirmError, setConfirmError] = useState(false);
  const [selectedTrait, setSelectedTrait] = useState<SelectedTrait>(null);
  const [pendingRedrawName, setPendingRedrawName] = useState<string | null>(null);
  const submissionInFlight = useRef(false);
  const submissionsDisabled = submissionState !== "idle";

  function toggleTrait(charId: string, attribute: string) {
    setSelectedTrait((current) =>
      current?.charId === charId && current.attribute === attribute
        ? null
        : { charId, attribute }
    );
  }

  const revealFingerprint = row?.reveal
    ? JSON.stringify({
        tapsLeft: row.reveal.taps_left,
        characters: row.reveal.characters.map(({ char_id, image_path, chips }) => ({
          charId: char_id,
          imagePath: image_path,
          chips,
        })),
      })
    : null;
  const previousRevealFingerprint = useRef<string | null>(null);
  const [choiceUpdated, setChoiceUpdated] = useState(false);

  useEffect(() => {
    if (bucket !== "paused" || !row?.reveal || !revealFingerprint) {
      previousRevealFingerprint.current = null;
      return;
    }

    const previous = previousRevealFingerprint.current;
    const selectionStillOffered = selectedTrait === null || row.reveal.characters.some(
      (character) => character.char_id === selectedTrait.charId && character.chips.includes(selectedTrait.attribute)
    );
    const revealChanged = previous !== null && previous !== revealFingerprint;

    if (selectedTrait && (!selectionStillOffered || revealChanged)) {
      setSelectedTrait(null);
      setPendingRedrawName(null);
      setChoiceUpdated(true);
    }

    previousRevealFingerprint.current = revealFingerprint;
  }, [bucket, revealFingerprint, row?.reveal, selectedTrait]);

  // Stall line: show after STALL_MS of no stage change
  const [stalling, setStalling] = useState(false);
  useEffect(() => {
    if (bucket !== "in-flight") return;
    const timer = setTimeout(() => setStalling(true), STALL_MS);
    return () => {
      clearTimeout(timer);
      setStalling(false);
    };
  }, [bucket, row?.current_stage]);

  // Reveal character image signing
  const [signedCharUrls, setSignedCharUrls] = useState<Record<string, string>>({});
  useEffect(() => {
    if (bucket !== "paused" || !row?.reveal?.characters.length) return;
    const characters = row.reveal.characters;
    const paths = characters.map(c => c.image_path);
    function sign(attempt: number) {
      signPaths(paths).then((signed) => {
        const map: Record<string, string> = {};
        characters.forEach((c) => {
          if (signed[c.image_path]) map[c.char_id] = signed[c.image_path];
        });
        if (Object.keys(map).length === 0) {
          if (attempt < 2) sign(attempt + 1);
          return; // render without images (spec §4.2)
        }
        setSignedCharUrls(map);
      });
    }
    sign(1);
  }, [bucket, row?.reveal]);

  // Push to /book on terminal-success. The bridge needs no teardown here: `isRedrawing` is read
  // only on the in-flight branch and only while the stage still matches, so a stale value cannot
  // show through. Clearing it from this effect would in fact break it — `useRouter()` hands back
  // a new object every render, so this effect re-runs on every render and would wipe the bridge
  // one render after the tap.
  useEffect(() => {
    if (bucket === "terminal-success") {
      router.replace(`/s/${profileId}/book/${jobId}`);
    }
  }, [bucket, profileId, jobId, router]);

  async function handleConfirm(
    action: "confirm" | "try_again",
    char_id?: string,
    attribute?: string
  ) {
    if (submissionInFlight.current || submissionsDisabled) return;
    submissionInFlight.current = true;
    setBridgeStage(row?.current_stage ?? null);
    setSubmissionState("sending");
    setConfirmError(false);
    let requestFailed = false;
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/confirm`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.access_token}`,
        },
        body: JSON.stringify({ action, char_id: char_id ?? null, attribute: attribute ?? null }),
      });
      requestFailed = !res.ok;
    } catch {
      requestFailed = true;
    }

    setSubmissionState("reconciling");
    let refreshed = false;
    try {
      refreshed = await refetch();
    } catch {
      refreshed = false;
    }
    if (!refreshed) {
      setBridgeStage(null);
      setSubmissionState("unknown");
      return;
    }

    if (requestFailed) setConfirmError(true);
    setSubmissionState("idle");
    submissionInFlight.current = false;
  }

  async function retryCharacterChoices() {
    if (submissionState !== "unknown") return;
    setSubmissionState("reconciling");
    let refreshed = false;
    try {
      refreshed = await refetch();
    } catch {
      refreshed = false;
    }
    if (refreshed) {
      submissionInFlight.current = false;
      setSubmissionState("idle");
      return;
    }
    setSubmissionState("unknown");
  }

  // Derive FailureScreen kind from row state
  if (bucket === "not-found") {
    return <FailureScreen kind="not-found" />;
  }

  if (bucket === "terminal-failure") {
    const kind =
      row?.failure_reason === "child_text"
        ? "revise"
        : row?.status === SWEPT_STATUS
        ? "asleep"
        : "retry";
    return (
      <FailureScreen
        kind={kind}
        reason={row?.failure_reason}
        jobId={jobId}
        inputText={row?.input_text}
        title={row?.title}
        stylePresetId={row?.style_preset_id}
      />
    );
  }

  if (bucket === "paused" && row?.reveal) {
    const { characters, taps_left } = row.reveal;
    return (
      <div className="w-full flex-1 min-h-[calc(100dvh-5rem)] flex flex-col justify-center items-center p-6 max-w-5xl mx-auto">
        <div className="w-full flex justify-start mb-4 z-20">
          <Link
            href={`/s/${profileId}`}
            className="inline-flex items-center gap-1.5 font-kid text-sm font-bold text-foreground/60 hover:text-primary transition-colors focus-visible:outline-secondary focus-visible:outline-2 rounded-lg py-1 px-2.5"
          >
            ← Bookshelf
          </Link>
        </div>
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center gap-4 text-center mb-12"
        >
          {row && (
            <p className="text-sm font-bold text-foreground/50 uppercase tracking-wider">
              {displayTitle(row.title, row.input_text)}
            </p>
          )}
          <h1 className="font-display text-4xl md:text-5xl text-foreground tracking-tight text-center">
            <KineticText text="Meet your cast!" />
          </h1>
          <p className="font-kid text-lg text-foreground/70 max-w-md">
            Choose a detail you want us to try drawing again.
          </p>
          {choiceUpdated && (
            <p aria-live="polite" className="sr-only">
              The character choices were updated.
            </p>
          )}
        </motion.div>

        <div className="mb-6 text-center font-kid text-foreground">
          {taps_left > 0 ? (
            <>
              <p className="font-bold">
                {taps_left} {taps_left === 1 ? "redraw" : "redraws"} left for this book
              </p>
              <p className="text-sm text-foreground/70">Shared by all your characters.</p>
            </>
          ) : (
            <p className="max-w-lg">
              No redraws left for this book. You can use these characters or go back to your bookshelf.
            </p>
          )}
        </div>

        <motion.div 
          className="flex flex-wrap justify-center gap-8 w-full"
          initial="hidden"
          animate="show"
          variants={{
            hidden: { opacity: 0 },
            show: {
              opacity: 1,
              transition: { staggerChildren: 0.15 }
            }
          }}
        >
          {characters.map(c => (
            <motion.div 
              key={c.char_id} 
              variants={{
                hidden: { opacity: 0, y: 40, scale: 0.8 },
                show: { opacity: 1, y: 0, scale: 1, transition: { type: "spring", bounce: 0.4 } }
              }}
              className="flex flex-col items-center gap-4 neo-border bg-[var(--color-surface)] rounded-[24px] p-5 shadow-[0_10px_28px_rgba(49,85,217,0.12)] hover:-translate-y-1 transition-transform max-w-xs w-full"
            >
              {signedCharUrls[c.char_id] ? (
                <img
                  src={signedCharUrls[c.char_id]}
                  alt={c.name}
                  className="w-full aspect-square object-cover rounded-[16px] bg-[var(--color-muted)]"
                />
              ) : (
                <div className="w-full aspect-square rounded-[16px] bg-[var(--color-muted)] animate-pulse" />
              )}
              <p className="font-display text-2xl text-foreground mt-2">{c.name}</p>
              
              <div className="flex flex-wrap justify-center gap-2 mt-2 w-full">
                {taps_left > 0 && c.chips.map(chip => {
                  const selected = selectedTrait?.charId === c.char_id && selectedTrait.attribute === chip;
                  return (
                    <button
                      key={chip}
                      type="button"
                      aria-pressed={selected}
                      disabled={submissionsDisabled}
                      onClick={() => toggleTrait(c.char_id, chip)}
                      className={`min-h-[44px] max-w-full rounded-full border px-4 py-2 font-kid text-sm text-foreground transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary disabled:opacity-50 ${
                        selected
                          ? "border-[var(--color-primary)] bg-[var(--color-primary)]/10 font-bold"
                          : "border-[var(--color-primary)]/20 bg-background hover:bg-[var(--color-primary)]/5"
                      }`}
                    >
                      {chip}
                      {selected && <span className="sr-only"> selected</span>}
                    </button>
                  );
                })}
              </div>

              {selectedTrait?.charId === c.char_id && (
                <div className="w-full rounded-[16px] bg-[var(--color-primary)]/5 p-4 text-left">
                  <p className="font-kid text-sm leading-relaxed text-foreground">
                    We&apos;ll draw a new picture, paying extra attention to {selectedTrait.attribute}. Other details may change.
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={submissionsDisabled}
                      onClick={() => {
                        setPendingRedrawName(c.name);
                        void handleConfirm("try_again", c.char_id, selectedTrait.attribute);
                      }}
                      className="min-h-[44px] rounded-xl bg-[var(--color-primary)] px-4 py-2 font-kid font-bold text-[var(--color-surface)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary disabled:opacity-50"
                    >
                      Redraw {c.name}
                    </button>
                    <button
                      type="button"
                      disabled={submissionsDisabled}
                      onClick={() => setSelectedTrait(null)}
                      className="min-h-[44px] rounded-xl px-4 py-2 font-kid font-bold text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </motion.div>

        <div className="mt-12 w-full flex flex-col items-center justify-center gap-3">
          <p className="font-kid text-sm text-foreground/70">Continue with the pictures shown.</p>
          <button
            type="button"
            disabled={submissionsDisabled}
            onClick={() => {
              setSelectedTrait(null);
              setPendingRedrawName(null);
              void handleConfirm("confirm");
            }}
            className="rounded-[16px] bg-[var(--color-primary)] text-[var(--color-surface)] min-h-[56px] px-12 font-kid text-xl disabled:opacity-50 hover:brightness-105 active:scale-[0.98] transition-all font-bold shadow-[0_10px_28px_rgba(49,85,217,0.12)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary"
          >
            Use these characters
          </button>
        </div>
        
        <div className="h-16 mt-8 flex items-center justify-center">
          <AnimatePresence>
            {submissionState === "unknown" ? (
              <motion.div
                initial={{ opacity: 0, height: 0, scale: 0.9 }}
                animate={{ opacity: 1, height: "auto", scale: 1 }}
                exit={{ opacity: 0, height: 0, scale: 0.9 }}
                role="alert"
                className="flex flex-wrap items-center justify-center gap-3 rounded-xl bg-[var(--color-destructive)]/10 px-6 py-3 font-kid text-base text-[var(--color-destructive)]"
              >
                <p>We couldn&apos;t refresh your character choices. Try loading them again.</p>
                <button
                  type="button"
                  onClick={() => void retryCharacterChoices()}
                  disabled={submissionState === "reconciling"}
                  className="min-h-[44px] rounded-xl bg-[var(--color-surface)] px-4 py-2 font-bold text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary disabled:opacity-50"
                >
                  Load character choices again
                </button>
              </motion.div>
            ) : confirmError && (
              <motion.p 
                initial={{ opacity: 0, height: 0, scale: 0.9 }}
                animate={{ opacity: 1, height: "auto", scale: 1 }}
                exit={{ opacity: 0, height: 0, scale: 0.9 }}
                role="alert" 
                className="font-kid text-base text-[var(--color-destructive)] bg-[var(--color-destructive)]/10 px-6 py-3 rounded-xl"
              >
                We couldn&apos;t send that choice. Please try again.
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </div>
    );
  }

  // in-flight bucket (or justConfirmed redraw state)
  const currentStepRaw = getStep(row?.current_stage ?? null);
  const currentStep = currentStepRaw ?? 1;
  const STEPS: StepperStep[] = [1, 2, 3, 4];
  const isRedrawing = bridgeStage !== null && (row?.current_stage ?? null) === bridgeStage;

  const ICONS = {
    1: BookOpen,
    2: Users,
    3: PaintBrush,
    4: MagicWand,
  };

  return (
    <div className="w-full flex-1 min-h-[calc(100dvh-5rem)] flex flex-col justify-center items-center p-6 max-w-4xl mx-auto relative overflow-hidden">
      
      {/* Top Navigation Exit */}
      <div className="w-full flex justify-start mb-4 z-20">
        <Link
          href={`/s/${profileId}`}
          className="inline-flex items-center gap-1.5 font-kid text-sm font-bold text-foreground/60 hover:text-primary transition-colors focus-visible:outline-secondary focus-visible:outline-2 rounded-lg py-1 px-2.5"
        >
          ← Bookshelf
        </Link>
      </div>

      {/* Spotlight Background effect */}
      <div className="absolute inset-0 pointer-events-none flex justify-center items-center opacity-30 z-0">
         <div className="w-[600px] h-[600px] bg-[var(--color-secondary)]/20 rounded-full blur-[100px]" />
      </div>

      {row && (
        <p className="z-10 -mb-8 text-sm font-bold text-foreground/50 uppercase tracking-wider">
          {displayTitle(row.title, row.input_text)}
        </p>
      )}
      <h1 className="z-10 mb-16 h-20 flex items-center justify-center font-display text-5xl md:text-6xl text-foreground tracking-tighter">
        <KineticText text="Making your book!" />
      </h1>

      {/* The Journey Tracker */}
      <div className="flex items-center justify-center gap-4 md:gap-8 w-full max-w-2xl z-10 mb-16 relative">
         {/* Connecting line behind */}
         <div className="absolute top-1/2 left-8 right-8 h-1 bg-[var(--color-muted)] -translate-y-1/2 z-0 hidden sm:block" />
         <motion.div 
           className="absolute top-1/2 left-8 h-1 bg-[var(--color-primary)] -translate-y-1/2 z-0 hidden sm:block origin-left"
           initial={{ scaleX: 0 }}
           animate={{ scaleX: (currentStep - 1) / 3 }}
           transition={{ duration: 0.8, ease: "easeInOut" }}
         />

         {STEPS.map(step => {
           const isDone = currentStepRaw !== null && step < currentStepRaw;
           const isActive = step === currentStep && !isRedrawing && currentStepRaw !== null;
           const Icon = ICONS[step];
           
           return (
             <div key={step} className="relative z-10 flex flex-col items-center gap-2">
                <motion.div 
                  animate={{
                    scale: isActive ? 1.15 : 1
                  }}
                  style={{
                    backgroundColor: isDone || isActive ? "var(--color-primary)" : "var(--color-surface)",
                    borderColor: isDone || isActive ? "var(--color-primary)" : "var(--color-muted)",
                    color: isDone || isActive ? "#FFFDF7" : "var(--foreground)",
                  }}
                  className="w-14 h-14 md:w-16 md:h-16 rounded-full border-2 flex items-center justify-center shadow-sm relative transition-colors duration-300"
                >
                  {isDone ? <Check size={28} weight="bold" /> : <Icon size={28} weight={isActive ? "fill" : "regular"} />}
                </motion.div>
             </div>
           );
         })}
      </div>

      {/* Spotlight Theater Vignettes & Text */}
      <div className="z-10 text-center min-h-[220px] flex flex-col items-center justify-center w-full">
        <AnimatePresence mode="wait">
          {isRedrawing ? (
            <motion.div
              key="redrawing"
              initial={{ opacity: 0, scale: 0.8, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.8, y: -10 }}
              aria-live="polite"
              className="flex flex-col items-center gap-6"
            >
               <DrawingVignette />
               <h2 className="font-display text-3xl md:text-4xl text-foreground tracking-tight">
                 {pendingRedrawName ? `Redrawing ${pendingRedrawName}…` : "Redrawing your character…"}
               </h2>
               <p className="font-kid text-sm text-foreground/70">The picture shown before was the previous picture.</p>
            </motion.div>
          ) : (
            <motion.div
              key={`step-${currentStep}`}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.4, type: "spring", bounce: 0.3 }}
              className="flex flex-col items-center gap-4 w-full px-4"
            >
               <div className="h-[140px] flex items-center justify-center">
                 {currentStep === 1 && <ReadingVignette />}
                 {currentStep === 2 && <CharactersVignette />}
                 {currentStep === 3 && <DrawingVignette />}
                 {currentStep === 4 && <StackingVignette />}
               </div>
               
               <motion.h2 
                 animate={{ scale: [0.98, 1, 0.98] }}
                 transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
                 className="font-display text-3xl md:text-4xl text-foreground text-center tracking-tight"
               >
                 {currentStepRaw !== null 
                    ? getStepLabel(currentStep, row?.current_stage ?? null)
                    : "Warming up..."}
               </motion.h2>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Stalling Text */}
      <div className="z-10 mt-12 min-h-[60px] flex justify-center w-full" aria-live="polite">
          {stalling && !isRedrawing && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="flex flex-col sm:flex-row items-center gap-3 bg-[var(--color-surface)] neo-border px-6 py-4 rounded-2xl sm:rounded-full shadow-sm max-w-sm sm:max-w-xl w-full mx-auto justify-between"
            >
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full bg-[var(--color-secondary)] animate-pulse shrink-0" />
                <p className="font-kid text-sm md:text-base text-foreground/80 leading-snug">
                  This step is taking longer than usual. Your progress is saved, so you can leave and come back.
                </p>
              </div>
              <Link
                href={"/s/" + profileId}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-surface border border-primary/20 text-foreground font-bold hover:bg-muted/40 transition shrink-0 whitespace-nowrap focus-visible:outline-secondary focus-visible:outline-2 text-sm"
              >
                Return to Bookshelf
              </Link>
            </motion.div>
          )}
      </div>
    </div>
  );
}

