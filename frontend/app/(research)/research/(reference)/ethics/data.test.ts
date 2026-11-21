import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { MODELS } from "../architecture/data";
import * as data from "./data";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const read = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");
const flat = (text: string) => text.replace(/\s+/g, " ");
const sources = Object.fromEntries(Object.entries(data.SOURCES).map(([key, file]) => [key, flat(read(file))]));

describe("ethics page data", () => {
  // SH-02: every sentence that states a fact carries a quote that its named source prints.
  it("finds the quote behind each stated fact in its source", () => {
    const all = [...data.BASIS, ...data.CONSENT, ...data.PRIVACY, ...data.SAFETY_FEATURES, ...data.LIMITS, ...data.MODERATION_LAYERS];
    expect(all.length).toBeGreaterThan(10);
    for (const fact of all) {
      expect(sources[fact.source].includes(fact.quote), `${fact.source}: ${fact.quote}`).toBe(true);
    }
  });

  it("states consent exactly as D-22 says, with no wider scope", () => {
    const text = data.CONSENT.map((fact) => fact.text).join(" ");
    expect(text).toContain("teacher's signed hard-copy consent");
    expect(text).toContain("No separate parental consent was collected");
    expect(text).toContain("Expert evaluators sign their own informed consent form");
    expect(text).not.toMatch(/guardian|assent|all learners|school-wide|permission to publish/i);
  });

  it("discloses the public repo, the missing donated images, Presidio and North America", () => {
    const text = data.PRIVACY.map((fact) => fact.text).join(" ");
    expect(text).toMatch(/story IDs, plot summaries and character names/);
    expect(text).toMatch(/no donated images/i);
    expect(text).toMatch(/Presidio/);
    expect(text).toMatch(/North America/);
  });

  it("takes the moderation model IDs from the architecture data, which reads config.py", () => {
    const settings = MODELS.map((m) => m.setting);
    for (const layer of data.MODERATION_LAYERS) for (const setting of layer.modelSettings) expect(settings).toContain(setting);
    const config = read("backend/app/config.py");
    expect(config).toContain("enable_teacher_moderation_review: bool = True");
    expect(config).toContain("enable_magic_pencil: bool = True");
    expect(config).toContain(`MAX_PENCIL_CHARS = ${data.PENCIL.chars}`);
    expect(config).toContain(`MAX_PAGE_PENCILS = ${data.PENCIL.pagePencils}`);
  });

  it("points each moderation layer at a file that runs it", () => {
    for (const layer of data.MODERATION_LAYERS) {
      expect(read(layer.file).includes(layer.mentions), `${layer.file} mentions ${layer.mentions}`).toBe(true);
    }
  });

  it("names no researcher or contact detail", () => {
    expect(JSON.stringify(data)).not.toMatch(/@[a-z]+\.[a-z]+|\+63|Hanseooo/i);
  });
});
