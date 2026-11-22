import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CHARTS as LIMITATION_CHARTS } from "../limitations/data";
import { CHARTS as RESULT_CHARTS } from "../results/data";

// Seam S-4 (US-22 AC-08, AC-09): the figure PNGs exist, and none is stale against its source
// (a drawio file, or a chart page's data.ts).
// Re-export with `node scripts/export-research-figures.mjs` from frontend/.
const FRONTEND = path.resolve(__dirname, "../../../../..");
const REPO_ROOT = path.resolve(FRONTEND, "..");
const DIAGRAMS = path.join(FRONTEND, "public/research/diagrams");
const RESEARCH_APP = path.join(FRONTEND, "app/(research)");

type ChartSource = { page: string; chartId: string; dataFile: string };
type Entry = { png: string; kind: "diagram" | "chart"; source: string | ChartSource; sourceSha256?: string };
const manifest: { figures: Entry[] } = JSON.parse(readFileSync(path.join(DIAGRAMS, "manifest.json"), "utf8"));
const diagrams = manifest.figures.filter((f) => f.kind === "diagram");
const charts = manifest.figures.filter((f) => f.kind === "chart");
// A chart's numbers live in its page's data.ts, so that file is its source.
const CHART_DATA = [
  ...RESULT_CHARTS.map((c) => [c.id, "frontend/app/(research)/research/(reference)/results/data.ts"] as const),
  ...LIMITATION_CHARTS.map((c) => [c.id, "frontend/app/(research)/research/(reference)/limitations/data.ts"] as const),
];

// Hash with LF line endings so a Windows autocrlf checkout and a CI checkout agree.
const sha256 = (repoPath: string) =>
  createHash("sha256").update(readFileSync(path.join(REPO_ROOT, repoPath), "utf8").replace(/\r\n/g, "\n")).digest("hex");

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return sourceFiles(full);
    return /\.(ts|tsx)$/.test(name) && !/\.test\./.test(name) ? [full] : [];
  });
}

describe("figure manifest", () => {
  it("matches each diagram's current source", () => {
    expect(diagrams.length).toBeGreaterThan(0);
    for (const f of diagrams) {
      const source = f.source as string;
      expect(sha256(source), `${source} changed since export: re-export ${f.png}`).toBe(f.sourceSha256);
    }
  });

  it("matches each chart's current data, and lists exactly the pages' charts", () => {
    const listed = charts.map((f) => (f.source as ChartSource).chartId);
    expect(listed.sort()).toEqual(CHART_DATA.map(([id]) => id).sort());
    for (const [id, dataFile] of CHART_DATA) {
      const f = charts.find((c) => (c.source as ChartSource).chartId === id)!;
      expect((f.source as ChartSource).dataFile).toBe(dataFile);
      expect(sha256(dataFile), `${dataFile} changed since export: re-export ${f.png}`).toBe(f.sourceSha256);
    }
  });

  it("lists every drawio source", () => {
    const listed = diagrams.map((f) => path.basename(f.source as string));
    const onDisk = readdirSync(path.join(REPO_ROOT, "docs/diagrams/drawio")).filter((n) => n.endsWith(".drawio.svg"));
    expect(listed.sort()).toEqual(onDisk.sort());
  });

  it("has a PNG for every entry", () => {
    for (const f of manifest.figures) {
      expect(existsSync(path.join(DIAGRAMS, f.png)), `${f.png} is in the manifest but missing from public/research/diagrams`).toBe(true);
    }
  });

  it("has a PNG for every figure link under (research)", () => {
    const linked = new Set<string>([...RESULT_CHARTS, ...LIMITATION_CHARTS].map((c) => c.png));
    for (const file of sourceFiles(RESEARCH_APP)) {
      for (const m of readFileSync(file, "utf8").matchAll(/\/research\/diagrams\/[\w.-]+\.png/g)) linked.add(m[0]);
    }
    expect(linked.size).toBeGreaterThan(0);
    for (const url of linked) {
      expect(existsSync(path.join(FRONTEND, "public", url)), `${url} is linked but has no PNG`).toBe(true);
    }
  });
});
