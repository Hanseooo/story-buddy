"use client";

/* eslint-disable react-hooks/refs */
/* eslint-disable @next/next/no-img-element */

import { use, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useJob } from "@/lib/useJob";
import FailureScreen from "@/components/FailureScreen";
import { supabase } from "@/lib/supabaseClient";

const BUCKET = "storybook-images";
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

export default function ProcessingPage({ params }: { params: Promise<{ jobId: string }> }) {
  const { jobId } = use(params);
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
      supabase.storage.from(BUCKET).createSignedUrls(paths, 3600).then(({ data }) => {
        if (!data && attempt < 2) { sign(attempt + 1); return; }
        if (!data) return; // render without images (spec §4.2)
        const map: Record<string, string> = {};
        characters.forEach((c, i) => {
          if (data[i]?.signedUrl) map[c.char_id] = data[i].signedUrl as string;
        });
        setSignedCharUrls(map);
      });
    }
    sign(1);
  }, [bucket, row?.reveal]);

  // Push to /book on terminal-success & manage justConfirmed lifecycle
  useEffect(() => {
    if (bucket === "terminal-success") {
      justConfirmed.current = false;
      router.push(`/book/${jobId}`);
    }
    if (bucket === "terminal-failure" || bucket === "not-found") {
      justConfirmed.current = false;
    }
    if (bucket === "paused" && prevBucket.current === "in-flight") {
      justConfirmed.current = false;
    }
    prevBucket.current = bucket;
  }, [bucket, jobId, router]);

  async function handleConfirm(
    action: "confirm" | "try_again",
    char_id?: string,
    attribute?: string
  ) {
    justConfirmed.current = true;
    setConfirming(true);
    setConfirmError(false);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/jobs/${jobId}/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      <div className="flex flex-col items-center gap-8 p-6">
        <h1 className="font-kid text-2xl text-center">Meet your characters!</h1>
        <div className="flex flex-wrap justify-center gap-6">
          {characters.map(c => (
            <div key={c.char_id} className="flex flex-col items-center gap-3 neo-border rounded-3xl p-4 neo-shadow">
              {signedCharUrls[c.char_id] && (
                <img
                  src={signedCharUrls[c.char_id]}
                  alt={c.name}
                  className="w-40 h-40 object-cover rounded-2xl"
                />
              )}
              <p className="font-kid text-lg">Meet {c.name}!</p>
              {taps_left > 0 && c.chips.map(chip => (
                <button
                  key={chip}
                  disabled={confirming}
                  onClick={() => handleConfirm("try_again", c.char_id, chip)}
                  className="rounded-2xl neo-border neo-shadow-sm min-h-[44px] px-4 font-kid text-sm disabled:opacity-50"
                >
                  {chip}
                </button>
              ))}
            </div>
          ))}
        </div>
        {confirmError && (
          <p role="alert" className="font-kid text-sm text-destructive">
            That didn&apos;t work — try once more.
          </p>
        )}
        <button
          disabled={confirming}
          onClick={() => handleConfirm("confirm")}
          className="rounded-2xl neo-border neo-shadow min-h-[44px] px-8 font-kid text-lg disabled:opacity-50"
        >
          Use this one!
        </button>
      </div>
    );
  }

  // in-flight bucket (or justConfirmed redraw state)
  const currentStep = getStep(row?.current_stage ?? null);
  const STEPS: StepperStep[] = [1, 2, 3, 4];
  const isRedrawing = justConfirmed.current;

  return (
    <div className="flex flex-col items-center gap-8 p-6">
      <h1 className="font-kid text-2xl text-center">Making your book!</h1>

      {isRedrawing ? (
        <p className="font-kid text-lg animate-shimmer rounded-2xl px-6 py-3">
          Drawing it again…
        </p>
      ) : (
        <ol className="flex flex-col gap-4 w-full max-w-sm" aria-live="polite">
          {STEPS.map(step => {
            const isDone = currentStep !== null && step < currentStep;
            const isActive = step === currentStep;
            return (
              <li
                key={step}
                className={[
                  "flex items-center gap-3 rounded-2xl p-3 neo-border",
                  isDone ? "opacity-100" : isActive ? "neo-shadow animate-stepper-pulse" : "opacity-40",
                ].join(" ")}
                aria-current={isActive ? "step" : undefined}
              >
                <span className="font-kid text-lg">
                  {isDone ? "✓" : isActive ? "▶" : "○"}
                </span>
                <span className="font-kid text-base">
                  {isActive || isDone
                    ? getStepLabel(step, row?.current_stage ?? null)
                    : getStepLabel(step, null)}
                </span>
              </li>
            );
          })}
        </ol>
      )}

      {stalling && !isRedrawing && (
        <p className="font-kid text-sm text-center opacity-70">
          Still going! We saved your spot, so you can leave and come back.
        </p>
      )}
    </div>
  );
}
