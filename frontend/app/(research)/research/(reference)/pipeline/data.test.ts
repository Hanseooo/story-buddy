import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as data from "./data";

const FRONTEND = path.resolve(__dirname, "../../../../..");
const REPO_ROOT = path.resolve(FRONTEND, "..");
const read = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");
const flat = (file: string) => read(file).replace(/\s+/g, " ");
const lineOf = (file: string, n: number) => read(file).split(/\r?\n/)[n - 1];

const GRAPH_NODES = [...read(data.SOURCES.graph).matchAll(/add_node\("([a-z_]+)"/g)].map((m) => m[1]);

describe("pipeline page data (SH-02, SH-08)", () => {
  it("counts nodes and modes as graph.py and the architecture doc say", () => {
    expect(GRAPH_NODES).toHaveLength(14);
    expect(data.NODE_COUNTS).toEqual({ total: 14, baseline: 11, teacherReview: 14 });
    expect(GRAPH_NODES.length - data.TEACHER_ONLY_NODES.length).toBe(data.NODE_COUNTS.baseline);
    const arch = flat(data.SOURCES.architecture);
    expect(arch).toContain("which makes the graph 14 nodes instead of the baseline 11");
    for (const id of data.TEACHER_ONLY_NODES) {
      expect(GRAPH_NODES, id).toContain(id);
      expect(arch, id).toContain(`\`${id}\``);
    }
  });

  it("pins each cap to its source line", () => {
    const wanted = { pagesMax: "10", pagesMin: "3", attempts: "3", taps: "3", words: "500" };
    for (const [key, value] of Object.entries(wanted)) {
      const cap = data.CAPS.find((c) => c.key === key);
      expect(cap, key).toBeDefined();
      expect(cap!.value, key).toBe(value);
      expect(lineOf(cap!.file, cap!.line), `${key}: ${cap!.file}:${cap!.line}`).toContain(cap!.text);
      expect(cap!.text, key).toContain(value);
    }
    expect(data.CAPS).toHaveLength(5);
  });

  it("says the corpus was made under a 300-word limit, from ADR-068", () => {
    expect(data.CORPUS_WORD_LIMIT).toBe("300");
    expect(flat(data.SOURCES.adr068)).toContain("both enforce 300 words");
    expect(flat(data.SOURCES.adr068)).toContain("Accepted (2026-10-11;");
  });

  it("maps every paper module to graph nodes that exist, and says the prompt optimizer is not a node", () => {
    const arch = flat(data.SOURCES.architecture);
    expect(data.MODULES).toHaveLength(10);
    expect(data.MODULES.filter((m) => m.nodes.length > 0)).toHaveLength(7);
    expect(flat(data.SOURCES.auditPaper)).toContain("11-module AI pipeline");
    for (const row of data.MODULES) {
      expect(flat(data.SOURCES.methodology), row.module).toContain(`| ${row.module} |`);
      expect(arch, row.module).toContain(`| ${row.module} | ${row.archCell} |`);
      for (const id of row.nodes) expect(GRAPH_NODES, id).toContain(id);
    }
    const optimizer = data.MODULES.find((m) => m.module === "Prompt Optimizer")!;
    expect(optimizer.nodes).toEqual([]);
    expect(arch).toContain("a node input, not a separate node");
    expect(flat(data.SOURCES.auditPaper)).toContain("Prompt Optimizer, Style Preset and Story Memory are not graph nodes");
  });

  it("states failure behaviour as the code and ADRs do", () => {
    expect(read(data.SOURCES.graph)).toContain('raise RuntimeError("output_moderation_failed")');
    expect(flat(data.SOURCES.adr025)).toContain("never** ships a placeholder or partial book");
    const arch = flat(data.SOURCES.architecture);
    expect(arch).toContain("In baseline mode a flag fails the job");
    expect(arch).toContain("`moderation_review` (a second `interrupt()`, the teacher hold, entered at the first moderation flag)");
    expect(flat(data.SOURCES.adr080)).toContain("request one bounded picture replacement or stop");
  });

  it("states the magic pencil and other versions as ADR-082 does", () => {
    const adr = flat(data.SOURCES.adr082);
    expect(adr).toContain("1. **Other versions.** Unchosen reference draws are kept");
    expect(adr).toContain("2. **Pencil.** The child writes a change (about 200 characters");
    expect(adr).toContain("Only on jobs submitted in `teacher_review_v1`");
  });

  it("links figures whose PNG and drawio source exist (SH-06)", () => {
    for (const fig of Object.values(data.FIGURES)) {
      expect(existsSync(path.join(FRONTEND, "public", fig.png)), fig.png).toBe(true);
      expect(existsSync(path.join(REPO_ROOT, fig.source)), fig.source).toBe(true);
      expect(fig.asOf).toBe("2026-11-21");
    }
  });
});
