import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { DOC_CHAPTERS, githubUrl } from "./entries";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const listed = DOC_CHAPTERS.flatMap((chapter) => chapter.entries.map((entry) => entry.path));

// Issue #105's files, written out by hand.
const ISSUE_105 = [
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

// Research page refresh US-25 AC-03: audit-3 D6 and D7, the new questionnaires, ADR-083, the
// restored hardware doc, and the new diagrams.
const REFRESH = [
  "docs/capstone/system_architecture.md",
  "docs/capstone/research_instruments.md",
  "docs/capstone/evaluation_instruments_brief.md",
  "docs/capstone/ethics_and_safety.md",
  "docs/capstone/story_donation_consent_and_assent_draft.md",
  "docs/capstone/iso_iec_25010_readiness_audit.md",
  "docs/capstone/model_finetuning.md",
  "docs/capstone/adjudication-notes-2026-09.md",
  "docs/capstone/design_decisions_and_risks.md",
  "docs/product/RESEARCH_PROTOCOL.md",
  "docs/product/PHASE_05_RESULTS.md",
  "docs/specs/iso-25010-scope-freeze.md",
  "docs/specs/functional-verification-matrix.md",
  "docs/TECH_STACK.md",
  "docs/MASTER_SPEC.md",
  "docs/capstone/expert-evaluation-questionnaire.md",
  "docs/capstone/iso-25010-questionnaire.md",
  "docs/capstone/hardware_and_hosting.md",
  "docs/product/adr/ADR-083-research-pages-hub-chapter-routes-and-png-diagram-export.md",
  "docs/diagrams/drawio/system_architecture.drawio.svg",
  "docs/diagrams/drawio/ipo_model.drawio.svg",
  "docs/diagrams/drawio/dataset_build_and_annotation_flow.drawio.svg",
  "docs/diagrams/drawio/student_journey.drawio.svg",
  "docs/diagrams/drawio/teacher_journey.drawio.svg",
];

const ALL = [...ISSUE_105, ...TRAINING, ...REFRESH];

describe("docs hub entries", () => {
  it("lists every required file, once", () => {
    expect([...listed].sort()).toEqual([...ALL].sort());
  });

  it.each(ALL)("%s exists in the repository", (file) => {
    expect(existsSync(path.join(REPO_ROOT, file))).toBe(true);
  });

  it("groups entries into chapters that each have a title and at least one entry", () => {
    expect(DOC_CHAPTERS.length).toBeGreaterThanOrEqual(5);
    for (const chapter of DOC_CHAPTERS) {
      expect(chapter.title).not.toBe("");
      expect(chapter.entries.length).toBeGreaterThan(0);
    }
  });

  it("links to the file on the main branch on GitHub", () => {
    expect(githubUrl("docs/capstone/group-guide.md")).toBe(
      "https://github.com/Hanseooo/story-buddy/blob/main/docs/capstone/group-guide.md"
    );
  });

  it("dates the pipeline diagram's 'as built' state instead of saying 'as it runs today'", () => {
    const after = DOC_CHAPTERS.flatMap((c) => c.entries).find((e) => e.path.includes("langgraph_pipeline_after"));
    expect(after?.answers).toMatch(/2026-11-21/);
    expect(after?.answers).not.toMatch(/runs today/);
  });
});

// AC-04. The date is a literal in entries.ts, because git history is not there at Vercel build time
// or in a shallow CI checkout. Where history is there, the literal may not be older than the file's
// last commit, so a doc edit that skips the date fails here. Author date, so rebases keep it.
function lastCommitDate(file: string): string | null {
  try {
    const shallow = execFileSync("git", ["rev-parse", "--is-shallow-repository"], { cwd: REPO_ROOT })
      .toString()
      .trim();
    if (shallow === "true") return null;
    const out = execFileSync("git", ["log", "-1", "--format=%as", "--", file], { cwd: REPO_ROOT })
      .toString()
      .trim();
    return out || null;
  } catch {
    return null;
  }
}

describe("last-changed dates", () => {
  const entries = DOC_CHAPTERS.flatMap((c) => c.entries);

  it.each(entries.map((e) => [e.path, e.lastChanged]))("%s has an ISO date (%s)", (_file, date) => {
    expect(date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(Number.isNaN(Date.parse(date))).toBe(false);
  });

  it.each(entries.map((e) => [e.path, e.lastChanged]))("%s date is not in the future", (_file, date) => {
    expect(date <= new Date().toISOString().slice(0, 10)).toBe(true);
  });

  it.each(entries.map((e) => [e.path, e.lastChanged]))("%s date is not older than its last commit", (file, date) => {
    const committed = lastCommitDate(file);
    if (committed === null) return; // no usable history (shallow clone or no git): nothing to compare
    expect(date >= committed, `${file}: entries.ts says ${date}, last commit says ${committed}`).toBe(true);
  });
});
