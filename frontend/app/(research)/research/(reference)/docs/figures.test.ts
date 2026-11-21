import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CHARTS as LIMITATION_CHARTS } from "../limitations/data";
import { CHARTS as RESULT_CHARTS } from "../results/data";

// Seam S-4 (US-22 AC-08, AC-09): the figure PNGs exist, and none is stale against its drawio source.
// Re-export with `node scripts/export-research-figures.mjs` from frontend/.
const FRONTEND = path.resolve(__dirname, "../../../../..");
const REPO_ROOT = path.resolve(FRONTEND, "..");
const DIAGRAMS = path.join(FRONTEND, "public/research/diagrams");
const RESEARCH_APP = path.join(FRONTEND, "app/(research)");

type Entry = { png: string; kind: "diagram" | "chart"; source: string | { page: string; chartId: string }; sourceSha256?: string };
const manifest: { figures: Entry[] } = JSON.parse(readFileSync(path.join(DIAGRAMS, "manifest.json"), "utf8"));
const diagrams = manifest.figures.filter((f) => f.kind === "diagram");

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
      const sha = createHash("sha256").update(readFileSync(path.join(REPO_ROOT, source))).digest("hex");
      expect(sha, `${source} changed since export: re-export ${f.png}`).toBe(f.sourceSha256);
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
