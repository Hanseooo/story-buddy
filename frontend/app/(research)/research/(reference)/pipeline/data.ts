// SH-02: every fact on the pipeline page is copied from one of these tracked files. data.test.ts reads each
// file as text and fails when the page value or sentence is not in it. Node names come from graph.py.
export const SOURCES = {
  graph: "backend/pipeline/graph.py",
  config: "backend/app/config.py",
  reveal: "backend/pipeline/reveal.py",
  architecture: "docs/capstone/system_architecture.md",
  methodology: "docs/capstone/methodology.md",
  auditPaper: "docs/specs/research-page-refresh/evidence/audit-3-docs-paper.md",
  adr025: "docs/product/adr/ADR-025-provider-resilience-failure-mode-policy-d-c.md",
  adr068: "docs/product/adr/ADR-068-story-input-expands-to-500-words-with-the-existing-page-and-image-ceilings.md",
  adr080: "docs/product/adr/ADR-080-teacher-held-moderation-and-exact-content-clearance.md",
  adr082: "docs/product/adr/ADR-082-magic-pencil-child-edits-and-other-versions.md",
} as const;

const AS_OF = "2026-11-21";

export const FIGURES = {
  ipo: {
    id: "ipo-model",
    png: "/research/diagrams/ipo_model.png",
    source: "docs/diagrams/drawio/ipo_model.drawio.svg",
    asOf: AS_OF,
    alt: "The IPO model: the child's story is the input, the pipeline is the process, and the finished picture book is the output.",
  },
  pipeline: {
    id: "langgraph-pipeline",
    png: "/research/diagrams/langgraph_pipeline_after_2026-10.png",
    source: "docs/diagrams/drawio/langgraph_pipeline_after_2026-10.drawio.svg",
    asOf: AS_OF,
    alt: "The LangGraph pipeline as it is now: the nodes from Input Gate to Compose, the scene loop, and the three teacher-review nodes.",
  },
} as const;

// graph.py has 14 add_node calls. These three run only in teacher-review mode (system_architecture.md §4).
export const NODE_COUNTS = { total: 14, baseline: 11, teacherReview: 14 } as const;
export const TEACHER_ONLY_NODES = ["optional_themes", "moderation_review", "moderation_replace"] as const;

// Each cap is pinned to a source line. The test checks that `text` is on line `line` of `file`.
// The "try again" cap lives in reveal.py, not config.py: config.py has no constant for it.
export const CAPS = [
  { key: "pagesMax", label: "Most pages in a book", value: "10", file: SOURCES.config, line: 193, text: "MAX_SCENES = 10" },
  { key: "pagesMin", label: "Fewest pages in a book", value: "3", file: SOURCES.config, line: 211, text: "MIN_SCENES = 3" },
  { key: "attempts", label: "Drawing attempts per page", value: "3", file: SOURCES.config, line: 108, text: "max_scene_attempts: int = 3" },
  { key: "taps", label: "“Try again” taps per book", value: "3", file: SOURCES.reveal, line: 24, text: "MAX_RETRY_TAPS = 3" },
  { key: "words", label: "Words in a story", value: "500", file: SOURCES.config, line: 224, text: "MAX_STORY_WORDS = 500" },
] as const;

// ADR-068: the study corpus was made before the limit rose to 500.
export const CORPUS_WORD_LIMIT = "300";

// The paper's ten modules (methodology.md §2) and where each lives (system_architecture.md §4).
// `archCell` is that table's cell word for word; `plain` is the page's wording.
export const MODULES: { module: string; nodes: string[]; archCell: string; plain: string }[] = [
  { module: "Input Moderation", nodes: ["input_gate"], archCell: "`input_gate` node", plain: "Input Gate" },
  { module: "Story Analyzer", nodes: ["analyze"], archCell: "`analyze` node", plain: "Analyze" },
  { module: "Scene Segmentation", nodes: ["segment"], archCell: "`segment` node", plain: "Segment" },
  {
    module: "Story Memory Manager",
    nodes: [],
    archCell: "the `StoryMemory` Pydantic contract — every node reads/writes through it, not a node itself",
    plain: "Not a graph node. It is the shared record every node reads and writes.",
  },
  { module: "Character Bible", nodes: ["char_bible"], archCell: "`char_bible` node", plain: "Character Bible" },
  {
    module: "Style Preset",
    nodes: [],
    archCell: "config chosen before generation and frozen (`style.style_preset_id`) — an input to `generate_scene`, not its own node (ADR-007, ADR-022)",
    plain: "Not a graph node. It is a setting chosen before drawing and passed to Generate Scene.",
  },
  {
    module: "Prompt Optimizer",
    nodes: [],
    archCell: "folded into `generate_scene`'s prompt construction — a node input, not a separate node",
    plain: "Not a graph node. Its work happens inside Generate Scene, when it builds the drawing prompt.",
  },
  { module: "AI Scene Generation", nodes: ["generate_scene"], archCell: "`generate_scene` node", plain: "Generate Scene" },
  {
    module: "Consistency Judge & Targeted Regeneration",
    nodes: ["consistency_check", "regenerate"],
    archCell: "`consistency_check` + `regenerate` nodes",
    plain: "Consistency Check and Regenerate",
  },
  {
    module: "Picture Book Composition",
    nodes: ["compose"],
    archCell: "`compose` node (no `export` node — ADR-058)",
    plain: "Compose",
  },
];
