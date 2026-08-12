"use client";

/* eslint-disable react-hooks/refs */
/* eslint-disable @next/next/no-img-element */

import { use, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useJob } from "@/lib/useJob";
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

  // Prevent the stepper from flashing during a redraw (spec §4.2)
  const justConfirmed = useRef(false);
  const prevBucket = useRef(bucket);
  const [confirming, setConfirming] = useState(false);
  const [confirmError, setConfirmError] = useState(false);

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

  // Push to /book on terminal-success & manage justConfirmed lifecycle
  useEffect(() => {
    if (bucket === "terminal-success") {
      justConfirmed.current = false;
      router.replace(`/s/${profileId}/book/${jobId}`);
    }
    if (bucket === "terminal-failure" || bucket === "not-found") {
      justConfirmed.current = false;
    }
    if (bucket === "paused" && prevBucket.current === "in-flight") {
      justConfirmed.current = false;
    }
    prevBucket.current = bucket;
  }, [bucket, profileId, jobId, router]);

  async function handleConfirm(
    action: "confirm" | "try_again",
    char_id?: string,
    attribute?: string
  ) {
    justConfirmed.current = true;
    setConfirming(true);
    setConfirmError(false);
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
      if (!res.ok) {
        justConfirmed.current = false;
        setConfirmError(true);
      }
    } catch {
      justConfirmed.current = false;
      setConfirmError(true);
    } finally {
      setConfirming(false);
      await refetch();
    }
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
    return <FailureScreen kind={kind} inputText={row?.input_text} />;
  }

  if (bucket === "paused" && row?.reveal) {
    const { characters, taps_left } = row.reveal;
    return (
      <div className="flex flex-col items-center p-6 w-full max-w-5xl mx-auto min-h-[100dvh] justify-center pt-24 pb-24">
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="flex flex-col items-center gap-4 text-center mb-12"
        >
          <h1 className="font-display text-4xl md:text-5xl text-foreground tracking-tight text-center">
            <KineticText text="Meet your cast!" />
          </h1>
          <p className="font-kid text-lg text-foreground/70 max-w-md">
            Make sure they look right! Tap a word to fix it, or let&apos;s start drawing.
          </p>
        </motion.div>

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
                {taps_left > 0 && c.chips.map(chip => (
                  <button
                    key={chip}
                    disabled={confirming}
                    onClick={() => handleConfirm("try_again", c.char_id, chip)}
                    className="rounded-full border border-[var(--color-primary)]/20 bg-background hover:bg-[var(--color-primary)]/5 min-h-[44px] px-4 font-kid text-sm disabled:opacity-50 transition-colors text-foreground"
                  >
                    {chip}
                  </button>
                ))}
              </div>
            </motion.div>
          ))}
        </motion.div>

        <div className="mt-12 w-full flex justify-center">
          <button
            disabled={confirming}
            onClick={() => handleConfirm("confirm")}
            className="rounded-[16px] bg-[var(--color-primary)] text-[var(--color-surface)] min-h-[56px] px-12 font-kid text-xl disabled:opacity-50 hover:brightness-105 active:scale-[0.98] transition-all font-bold shadow-[0_10px_28px_rgba(49,85,217,0.12)]"
          >
            They look great! Let&apos;s go!
          </button>
        </div>
        
        <div className="h-16 mt-8 flex items-center justify-center">
          <AnimatePresence>
            {confirmError && (
              <motion.p 
                initial={{ opacity: 0, height: 0, scale: 0.9 }}
                animate={{ opacity: 1, height: "auto", scale: 1 }}
                exit={{ opacity: 0, height: 0, scale: 0.9 }}
                role="alert" 
                className="font-kid text-base text-[var(--color-destructive)] bg-[var(--color-destructive)]/10 px-6 py-3 rounded-xl"
              >
                That didn&apos;t work — try once more.
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
  const isRedrawing = justConfirmed.current;

  const ICONS = {
    1: BookOpen,
    2: Users,
    3: PaintBrush,
    4: MagicWand,
  };

  return (
    <div className="flex flex-col items-center p-6 w-full max-w-4xl mx-auto min-h-[100dvh] justify-center relative overflow-hidden">
      
      {/* Spotlight Background effect */}
      <div className="absolute inset-0 pointer-events-none flex justify-center items-center opacity-30 z-0">
         <div className="w-[600px] h-[600px] bg-[var(--color-secondary)]/20 rounded-full blur-[100px]" />
      </div>

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
              className="flex flex-col items-center gap-6"
            >
               <DrawingVignette />
               <h2 className="font-display text-3xl md:text-4xl text-foreground tracking-tight">
                 Drawing it again…
               </h2>
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
      <div className="z-10 mt-12 min-h-[60px] flex justify-center w-full">
          {stalling && !isRedrawing && (
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="flex items-center gap-3 bg-[var(--color-surface)] neo-border px-6 py-4 rounded-full shadow-sm max-w-sm w-full md:max-w-md mx-auto"
            >
              <div className="w-3 h-3 rounded-full bg-[var(--color-secondary)] animate-pulse shrink-0" />
              <p className="font-kid text-sm md:text-base text-foreground/80 leading-snug">
                Still going! We saved your spot, so you can leave and come back.
              </p>
            </motion.div>
          )}
      </div>
    </div>
  );
}

