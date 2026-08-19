"use client";

import { useState, useEffect, useCallback, useTransition } from "react";
import { useRouter } from "next/navigation";
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

const TAXONOMY_LABELS: Record<keyof TaxonomyState, { label: string; shortcut: string }> = {
  wrong_colour: { label: "Wrong Color", shortcut: "1" },
  wrong_species: { label: "Wrong Species", shortcut: "2" },
  wrong_body_feature: { label: "Wrong Body Feature", shortcut: "3" },
  wrong_clothing: { label: "Wrong Clothing/Accessories", shortcut: "4" },
  wrong_style: { label: "Wrong Style", shortcut: "5" },
  different_face: { label: "Different Face", shortcut: "6" },
  character_absent: { label: "Character Absent", shortcut: "7" },
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

  const failureReasons = (Object.keys(taxonomy) as Array<keyof TaxonomyState>).filter(
    (k) => taxonomy[k]
  );
  const sameCharacter = explicitSameCharacter;

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
      router.refresh();
    });
  }, [isPending, pair.id, failureReasons, sameCharacter, brokenAnatomy, textVisible, router]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === "Enter" && !isPending) {
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
  }, [handleSubmit, toggleSameCharacter, toggleTaxonomy, isPending]);

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Visual Conflict Summary Banner */}
      <div className="w-full bg-orange-50 border border-orange-200 p-4 rounded-lg flex flex-col md:flex-row md:items-start gap-4">
        <div className="font-semibold text-orange-900 w-48">Conflicts Detected:</div>
        <div className="flex-1 grid grid-cols-3 gap-4 text-sm">
          <div className="font-medium text-gray-500">Field</div>
          <div className="font-semibold text-gray-800">Annotator 1</div>
          <div className="font-semibold text-gray-800">Annotator 2</div>

          {hasConflict(annotationA, annotationB, "same_character") && (
            <>
              <div className="text-red-600 font-medium">Same Character</div>
              <div>{annotationA.same_character ? "Yes" : "No"}</div>
              <div>{annotationB.same_character ? "Yes" : "No"}</div>
            </>
          )}
          {hasConflict(annotationA, annotationB, "failure_reasons") && (
            <>
              <div className="text-red-600 font-medium">Failure Reasons</div>
              <div>{formatReasons(annotationA.failure_reasons)}</div>
              <div>{formatReasons(annotationB.failure_reasons)}</div>
            </>
          )}
          {hasConflict(annotationA, annotationB, "anatomy_intact") && (
            <>
              <div className="text-red-600 font-medium">Broken Anatomy</div>
              <div>{!annotationA.anatomy_intact ? "Broken" : "Intact"}</div>
              <div>{!annotationB.anatomy_intact ? "Broken" : "Intact"}</div>
            </>
          )}
          {hasConflict(annotationA, annotationB, "text_free") && (
            <>
              <div className="text-red-600 font-medium">Text Visible</div>
              <div>{!annotationA.text_free ? "Visible" : "None"}</div>
              <div>{!annotationB.text_free ? "Visible" : "None"}</div>
            </>
          )}
        </div>
      </div>

      <div className="w-full flex gap-8">
        {/* Images */}
        <div className="flex-1 flex flex-col gap-4">
          <div className="aspect-square bg-gray-200 rounded-lg overflow-hidden relative border border-gray-300">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pair.canonical_signed_url}
              alt="Canonical Reference"
              className="object-contain w-full h-full"
            />
          </div>
          <p className="text-center font-medium text-sm text-gray-500">Canonical Reference</p>
        </div>

        <div className="flex-1 flex flex-col gap-4">
          <div className="aspect-square bg-gray-200 rounded-lg overflow-hidden relative border border-gray-300">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={pair.scene_signed_url}
              alt="Generated Scene"
              className="object-contain w-full h-full"
            />
          </div>
          <p className="text-center font-medium text-sm text-gray-500">Generated Scene</p>
        </div>

        {/* Resolution Control Panel */}
        <div className="w-80 flex-shrink-0 bg-white p-6 rounded-lg shadow-sm border border-gray-200 flex flex-col">
          <h2 className="font-semibold mb-2 border-b pb-2 text-purple-900">Authoritative Label</h2>
          <p className="text-xs text-gray-500 mb-4">
            Resolve the conflict by selecting the final ground truth label.
          </p>

          <div className="flex-1 flex flex-col gap-3">
            <label
              className={`flex items-center gap-3 cursor-pointer group p-2 hover:bg-green-50 rounded transition-colors mb-2 border border-gray-200 bg-gray-50 ${
                isPending ? "opacity-50 cursor-not-allowed" : ""
              }`}
            >
              <input
                type="checkbox"
                checked={explicitSameCharacter}
                onChange={toggleSameCharacter}
                disabled={isPending}
                data-testid="same-character-checkbox"
                aria-label="Mark as same character"
                className="w-5 h-5 rounded border-gray-300 text-green-600 focus:ring-green-500 disabled:bg-gray-200"
              />
              <span className="flex-1 text-sm font-bold text-green-800">Same Character</span>
              <kbd className="px-2 py-1 bg-white border border-gray-200 rounded text-xs text-gray-500 font-mono">
                0
              </kbd>
            </label>

            {(Object.entries(TAXONOMY_LABELS) as [keyof TaxonomyState, { label: string; shortcut: string }][]).map(
              ([key, { label, shortcut }]) => (
                <label
                  key={key}
                  className={`flex items-center gap-3 cursor-pointer group p-2 hover:bg-gray-50 rounded transition-colors ${
                    isPending ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={taxonomy[key]}
                    onChange={() => toggleTaxonomy(key)}
                    disabled={isPending}
                    aria-label={label}
                    className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:bg-gray-200"
                  />
                  <span className="flex-1 text-sm font-medium text-gray-700 group-hover:text-gray-900">
                    {label}
                  </span>
                  <kbd className="px-2 py-1 bg-gray-100 border border-gray-200 rounded text-xs text-gray-500 font-mono">
                    {shortcut}
                  </kbd>
                </label>
              )
            )}

            <div className="border-t my-2 pt-2"></div>

            <label
              className={`flex items-center gap-3 cursor-pointer group p-2 hover:bg-gray-50 rounded transition-colors ${
                isPending ? "opacity-50 cursor-not-allowed" : ""
              }`}
            >
              <input
                type="checkbox"
                checked={brokenAnatomy}
                onChange={() => setBrokenAnatomy((p) => !p)}
                disabled={isPending}
                aria-label="Broken Anatomy"
                className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500 disabled:bg-gray-200"
              />
              <span className="flex-1 text-sm font-medium text-gray-700 group-hover:text-gray-900">
                Broken Anatomy
              </span>
              <kbd className="px-2 py-1 bg-gray-100 border border-gray-200 rounded text-xs text-gray-500 font-mono">
                A
              </kbd>
            </label>

            <label
              className={`flex items-center gap-3 cursor-pointer group p-2 hover:bg-gray-50 rounded transition-colors ${
                isPending ? "opacity-50 cursor-not-allowed" : ""
              }`}
            >
              <input
                type="checkbox"
                checked={textVisible}
                onChange={() => setTextVisible((p) => !p)}
                disabled={isPending}
                aria-label="Text Visible"
                className="w-5 h-5 rounded border-gray-300 text-purple-600 focus:ring-purple-500 disabled:bg-gray-200"
              />
              <span className="flex-1 text-sm font-medium text-gray-700 group-hover:text-gray-900">
                Text Visible
              </span>
              <kbd className="px-2 py-1 bg-gray-100 border border-gray-200 rounded text-xs text-gray-500 font-mono">
                T
              </kbd>
            </label>
          </div>

          <div className="mt-6 pt-4 border-t flex flex-col gap-2">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-semibold">Authoritative Verdict:</span>
              <span
                className={`text-sm font-bold px-2 py-1 rounded ${
                  sameCharacter
                    ? "bg-green-100 text-green-800"
                    : failureReasons.length > 0
                      ? "bg-red-100 text-red-800"
                      : "bg-gray-100 text-gray-600"
                }`}
              >
                {sameCharacter
                  ? "Same Character"
                  : failureReasons.length > 0
                    ? "Different Character"
                    : "Unselected"}
              </span>
            </div>

            {error && <p className="text-sm text-red-600 mb-2">{error}</p>}

            <button
              onClick={handleSubmit}
              disabled={isPending}
              className="w-full py-3 bg-purple-600 text-white rounded-md font-medium hover:bg-purple-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isPending ? "Submitting..." : "Submit Final Decision"}
              <kbd className="px-2 py-0.5 bg-purple-500 rounded text-xs border border-purple-400">
                Enter
              </kbd>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
