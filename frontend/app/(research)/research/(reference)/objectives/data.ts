import { PARTIAL_SENTENCES, TRADEOFF } from "../results/data";

// SH-02: every sentence below is pinned to a tracked source by data.test.ts.
export const SOURCES = {
  goals: "docs/capstone/research_direction_and_goals.md",
  graph: "backend/pipeline/graph.py",
  groupGuide: "docs/capstone/group-guide.md",
  methodology: "docs/capstone/methodology.md",
  changelog: "docs/capstone/research-changelog.md",
  readiness: "docs/specs/obj4-readiness-audit.md",
  runbook: "docs/capstone/research_runbook.md",
  spec: "docs/specs/research-page-refresh.md",
} as const;

export type Objective = {
  n: number;
  /** The manuscript's wording, research_direction_and_goals.md "Objectives" (AC-10). */
  text: string;
  answer: { lead: string; body: string[] };
  evidence: { label: string; path: string }[];
  explained: { label: string; href: string };
};

// D-10: Objectives 3 and 5 show "Survey pending" and nothing else, so they have no evidence list.
export const OBJECTIVES: Objective[] = [
  {
    n: 1,
    text: "Implement an orchestrated AI pipeline as the core processing framework of StoryBuddy.",
    // AC-12, D-20. Tool A was dropped (D-28), so it is not mentioned.
    answer: {
      lead: "Achieved.",
      body: [
        "The orchestrated pipeline is implemented as a LangGraph graph of 14 nodes (11 in baseline mode). It produced the 42 study books end to end, and its automated tests pass.",
      ],
    },
    evidence: [
      { label: "The graph: every node is one add_node call", path: SOURCES.graph },
      { label: "The corpus holds 42 generated books", path: SOURCES.groupGuide },
      { label: "Decision D-20: Objective 1 is Achieved", path: SOURCES.spec },
    ],
    explained: { label: "Conceptual framework and pipeline", href: "/research/pipeline" },
  },
  {
    n: 2,
    text: "Produce digital picture books from child-written stories through the implemented pipeline.",
    // AC-13, with the sourced account of the three donated stories (methodology.md 3.3 and 4.1).
    answer: {
      lead: "42 digital picture books were produced through the pipeline: 30 from synthetic stories and 12 from donated stories.",
      body: [
        "Fifteen donated stories were collected and twelve were generated into books. The other three did not finish (two invalid_terminal, one budget_stopped) and were left out on purpose, not rerun.",
      ],
    },
    evidence: [
      { label: "Respondents and corpus size, sections 3.3 and 4.1", path: SOURCES.methodology },
      { label: "Changelog row 2026-09-16 to 17: the corpus generated", path: SOURCES.changelog },
      { label: "Readiness audit, section 7: the three stories left out", path: SOURCES.readiness },
    ],
    explained: { label: "Methodology at a glance", href: "/research/methodology" },
  },
  {
    n: 3,
    text: "Determine the acceptability of the generated digital picture books — presentation quality and classroom suitability — through expert validation.",
    answer: { lead: "Survey pending", body: [] },
    evidence: [],
    explained: { label: "Evaluation instruments", href: "/research/instruments" },
  },
  {
    n: 4,
    text: "Evaluate the character-consistency classification performance of the fine-tuned lightweight vision-language model against human-established reference labels, using standard classification metrics: precision, recall, and F1-score (F1 primary).",
    // AC-15: the verbatim tradeoff sentence (results page source) and the partial-comparison note (US-10 AC-05).
    answer: {
      lead: "The fine-tuned judge did not beat its untrained base on F1 (0.31 vs 0.47).",
      body: [TRADEOFF, `The comparison is partial. ${PARTIAL_SENTENCES[0]} ${PARTIAL_SENTENCES[1]}`],
    },
    evidence: [
      { label: "Exact values of the partial comparison", path: SOURCES.runbook },
      { label: "The tradeoff in plain words, section 5.2", path: SOURCES.groupGuide },
      { label: "Why the comparison is partial", path: SOURCES.changelog },
    ],
    explained: { label: "Character-consistency results", href: "/research/results" },
  },
  {
    n: 5,
    text: "Evaluate the software quality of StoryBuddy against applicable ISO/IEC 25010 quality characteristics.",
    answer: { lead: "Survey pending", body: [] },
    evidence: [],
    explained: { label: "Evaluation instruments", href: "/research/instruments" },
  },
];
