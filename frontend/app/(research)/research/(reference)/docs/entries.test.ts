import { existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { DOC_FOLDERS, githubUrl } from "./entries";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const listed = DOC_FOLDERS.flatMap((folder) => folder.entries.map((entry) => `${folder.path}/${entry.file}`));

// The files issue #105 names, written out by hand.
const REQUIRED = [
  "docs/capstone/group-guide.md",
  "docs/capstone/research-changelog.md",
  "docs/capstone/methodology.md",
  "docs/capstone/research_direction_and_goals.md",
  "docs/product/PREREGISTRATION_OBJ4.md",
  "docs/capstone/research_runbook.md",
  "docs/specs/labelling-rulebook.md",
  "docs/product/ADRs.md",
  "docs/capstone/model-probes-2026-10.md",
  "docs/capstone/pipeline-stage-audit-2026-10.md",
  "docs/diagrams/drawio/langgraph_pipeline_after_2026-10.drawio.svg",
  "docs/diagrams/drawio/langgraph_pipeline_before_2026-07.drawio.svg",
];

// ADR-066 amendment (a): where the judge's training is written down.
const TRAINING = ["docs/specs/judge-finetune.md", "backend/finetune/train_qlora.yaml"];

describe("docs hub entries", () => {
  it("lists every file issue #105 names and the two training files, once", () => {
    expect([...listed].sort()).toEqual([...REQUIRED, ...TRAINING].sort());
  });

  it.each([...REQUIRED, ...TRAINING])("%s exists in the repository", (file) => {
    expect(existsSync(path.join(REPO_ROOT, file))).toBe(true);
  });

  it("links to the file on the main branch on GitHub", () => {
    expect(githubUrl("docs/capstone/group-guide.md")).toBe(
      "https://github.com/Hanseooo/story-buddy/blob/main/docs/capstone/group-guide.md"
    );
  });
});
