// The research pages, once. The hub lists them, the header and Previous/Next follow them, and
// readingOrder.test.ts pins the titles, routes and order to docs/specs/research-page-refresh.md section 4.1.
// `paper` names are the paper sections each page feeds (audit-3 section (b)); the test finds each in the audit.

export type ResearchPage = {
  group: "Methodology" | "Results" | "Reference";
  title: string;
  href: string;
  /** One line on what the page covers. */
  line: string;
  /** Paper sections the page feeds. */
  paper: string[];
  /** Runs is outside the reading order: it needs sign-in (US-01 AC-02). */
  inOrder: boolean;
};

export const RESEARCH_PAGES: ResearchPage[] = [
  {
    group: "Methodology",
    title: "Conceptual framework and pipeline",
    href: "/research/pipeline",
    line: "How a story becomes a picture book: the input-process-output model, the nodes and the limits.",
    paper: ["Conceptual framework", "Appendix A", "Appendix B"],
    inOrder: true,
  },
  {
    group: "Methodology",
    title: "Methodology at a glance",
    href: "/research/methodology",
    line: "The research design, where the stories came from, how many there are and who answers the questionnaires.",
    paper: ["Research design", "Respondents", "Data collection"],
    inOrder: true,
  },
  {
    group: "Methodology",
    title: "Development loops (SDLC)",
    href: "/research/sdlc",
    line: "The six development loops, the risk each addressed, its gate and whether the gate was met, traced to merged pull requests.",
    paper: ["Figure 3 Spiral", "Table 1"],
    inOrder: true,
  },
  {
    group: "Methodology",
    title: "Dataset",
    href: "/research/dataset",
    line: "What a pair is, how pairs were labelled, and how they were split.",
    paper: ["Dataset", "Annotation", "Dataset Division"],
    inOrder: true,
  },
  {
    group: "Methodology",
    title: "Evaluation instruments",
    href: "/research/instruments",
    line: "The expert questionnaire and the ISO/IEC 25010 questionnaire, as written.",
    paper: ["Expert validation data", "Evaluation of instruments"],
    inOrder: true,
  },
  {
    group: "Methodology",
    title: "System architecture and specifications",
    href: "/research/architecture",
    line: "What runs where, and the models, libraries and hardware behind it.",
    paper: ["System architecture", "Hardware and software"],
    inOrder: true,
  },
  {
    group: "Methodology",
    title: "Ethics and safety",
    href: "/research/ethics",
    line: "The basis the study rests on, what was consented to, what is public and how safety is set up.",
    paper: ["Ethical considerations"],
    inOrder: true,
  },
  {
    group: "Results",
    title: "Objectives and answers",
    href: "/research/objectives",
    line: "Each of the five objectives with its current answer and evidence.",
    paper: ["Objectives", "Results"],
    inOrder: true,
  },
  {
    group: "Results",
    title: "Character-consistency results (Objective 4)",
    href: "/research/results",
    line: "How the fine-tuned judge compares with its untrained base, in plain words and in counts.",
    paper: ["Results 3.3 Objective 4", "Training and validation"],
    inOrder: true,
  },
  {
    group: "Results",
    title: "Limitations",
    href: "/research/limitations",
    line: "What goes wrong in the books, how often, what was tried and what the study must state as a limit.",
    paper: ["Results 3.2 Books", "Conclusion and Recommendations"],
    inOrder: true,
  },
  {
    group: "Reference",
    title: "Docs",
    href: "/research/docs",
    line: "The files behind the study, grouped by paper chapter, and what the paper must say.",
    paper: ["All chapters"],
    inOrder: true,
  },
  {
    group: "Reference",
    title: "Runs",
    href: "/research/metrics",
    line: "Every pipeline run, step by step. Needs a researcher sign-in.",
    paper: [],
    inOrder: false,
  },
];

export const READING_ORDER = RESEARCH_PAGES.filter((page) => page.inOrder);

export const HUB_GROUPS = ["Methodology", "Results", "Reference"] as const;

/** The pages either side of `pathname` in the reading order. The hub, Runs and unknown paths have neither. */
export function neighbours(pathname: string): { previous: ResearchPage | null; next: ResearchPage | null } {
  const path = pathname.replace(/\/+$/, "");
  const at = READING_ORDER.findIndex((page) => page.href === path);
  if (at === -1) return { previous: null, next: null };
  return { previous: READING_ORDER[at - 1] ?? null, next: READING_ORDER[at + 1] ?? null };
}
