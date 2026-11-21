// SH-02: every fact on the SDLC page is copied from the SDLC record, which data.test.ts checks against git
// (merge commit, date and title per PR) and against methodology.md §1.3.
export const SOURCES = {
  record: "docs/capstone/sdlc-record.md",
  methodology: "docs/capstone/methodology.md",
  roadmap: "docs/product/ROADMAP.md",
  phase05: "docs/product/PHASE_05_RESULTS.md",
} as const;

export const AS_OF = "2026-11-22";

export const MODEL = "Boehm's Spiral Model — a risk-driven, iterative SDLC with stage-gated phases.";

export const FIGURE = {
  id: "sdlc-spiral",
  png: "/research/diagrams/sdlc_spiral.png",
  source: "docs/diagrams/drawio/sdlc_spiral.drawio.svg",
  asOf: AS_OF,
  alt: "The six development loops drawn as a spiral through the four Spiral quadrants, each loop numbered and marked with its gate result.",
} as const;

/** How the gate result reads, in one word. The page shows it as a label next to the result. */
export type Outcome = "recorded" | "split" | "not run" | "partial" | "relaxed" | "open";

export type Loop = {
  loop: number;
  phase: string;
  risk: string;
  prs: number;
  first: string | null;
  last: string | null;
  gate: string;
  result: string;
  /** The loop's PR numbers, a run of three or more written as a range. */
  prList: string;
  outcome: Outcome;
};

// The record's §2 loop table, cell for cell.
export const LOOPS: Loop[] = [
  {
    loop: 1,
    phase: "0 & 0.5",
    risk: "Can an open image model hold a stylized, invented, non-human character across scenes?",
    prs: 0,
    first: null,
    last: null,
    gate: "Reference conditioning retains identity on ≥ 80% of items and exceeds unconditioned by ≥ 30 points.",
    result: "Split. Run 3 passed absolute (80%), failed separation (+25 vs ≥30); the failed gate is carried as a stated limitation.",
    prList: "",
    outcome: "split",
  },
  {
    loop: 2,
    phase: "1",
    risk: "Does the consistency loop work on clean stories?",
    prs: 21,
    first: "2026-07-29",
    last: "2026-10-13",
    gate: "A clean multi-scene, multi-character story produces a coherent, character-consistent storybook, and you can point to a case where the VLM-judge caught an off-model image and the targeted retry fixed it.",
    result: "Recorded as complete on 2026-08-02, when all ten Phase-1 specs were built. No run showing the exit case is named in the repository.",
    prList: "#1–#11, #30, #35, #38, #40, #41, #43, #124–#127",
    outcome: "recorded",
  },
  {
    loop: 3,
    phase: "2",
    risk: "Is it safe for a real child in a real classroom, and does it survive messy input?",
    prs: 20,
    first: "2026-08-02",
    last: "2026-10-23",
    gate: "Entry: probe 4 (Filipino/Taglish moderation), no MISS in either direction.",
    result: "Not run. Phase 2 was built without its entry gate.",
    prList: "#12–#18, #20–#22, #34, #36, #37, #39, #42, #80, #122, #123, #128, #129",
    outcome: "not run",
  },
  {
    loop: 4,
    phase: "2.5",
    risk: "Does fine-tuning make the Consistency Judge better?",
    prs: 17,
    first: "2026-08-22",
    last: "2026-10-09",
    gate: "The results table exists and is honest, and the held-out set was read exactly once.",
    result: "Partial. Paid evaluation stopped on 2026-10-07; on the held-out set the untuned model scored higher F1 than every fine-tuned seed.",
    prList: "#66, #67, #69, #70, #81–#91, #93, #101",
    outcome: "partial",
  },
  {
    loop: 5,
    phase: "After the technical defense",
    risk: "Do the panel's suggestions work without weakening child safety?",
    prs: 5,
    first: "2026-10-26",
    last: "2026-11-21",
    gate: "Items that touch ADR-011, ADR-017, ADR-029 or the teacher-review spec ship behind an off-by-default setting pending an ethics re-review.",
    result: "Shipped off by default, then turned on by default on 2026-11-21 so they can be tested. The real-child gates (ethics re-review, moderation audit 01) still apply.",
    prList: "#130–#134",
    outcome: "relaxed",
  },
  {
    loop: 6,
    phase: "3",
    risk: "Does the system hold up under the study's three evaluations?",
    prs: 5,
    first: "2026-08-10",
    last: "2026-10-11",
    gate: "One full expert-validation session (Objective 3) and one full ISO/IEC 25010 session (Objective 5) end-to-end, and a clean metrics table.",
    result: "Open. The repository records no completed session yet, and the functional verification matrix was dropped (D-28).",
    prList: "#19, #79, #113, #115, #116",
    outcome: "open",
  },
];

// The record's §3, each as its bold lead and the sentences after it.
export const DEVIATIONS = [
  {
    title: "Loop 1's separation gate was missed.",
    detail: "It was reported as a miss and carried as a limitation, not as a pass. The escalation was declined (ADR-001).",
  },
  {
    title: "Loop 3 started without its entry gate.",
    detail: "Probe 4 has not run. The moderation stack shipped in PR #12 on 2026-08-02 without it.",
  },
  {
    title: "Loop 2 kept going after its gate.",
    detail: "10 consistency PRs merged after Phase 1 was recorded complete, the last on 2026-10-13.",
  },
  {
    title: "Loop 4's exit criterion is not met.",
    detail: "The held-out result is partial: paid evaluation stopped for budget and the Gemma baseline failed authentication (group-guide.md §4).",
  },
  {
    title: "Scope changed inside loop 3.",
    detail: "Narration and PDF export were cut (ADR-058, PR #79); PDF download was restored on 2026-10-21 (ADR-071, PR #128).",
  },
  {
    title: "A planned instrument was dropped.",
    detail: "The functional verification matrix for Objectives 1–2 was never built (D-28).",
  },
  {
    title: "Loop 5's off-by-default rule was relaxed for testing.",
    detail: "The features are on by default since PR #134; the release gate for real children did not change.",
  },
] as const;

// The Phase 0.5 result, as PHASE_05_RESULTS.md and methodology.md §1.3 state it (moved from the methodology page).
export const PHASE_05 = {
  recorded:
    "Run 3 passed absolute (80%), failed separation (+25 vs ≥30); escalation declined, Qwen-Image-Edit stays primary per the ADR-001 amendment, and the failed gate is carried as a stated limitation.",
  methodology:
    "reference conditioning retained identity on 80% of pipeline-ON items (absolute gate met) but exceeded pipeline-OFF by only +25 points against a pre-committed ≥30 (separation gate missed).",
} as const;
