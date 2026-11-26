import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import * as data from "./data";

const REPO_ROOT = path.resolve(__dirname, "../../../../../..");
const FRONTEND = path.join(REPO_ROOT, "frontend");
const read = (file: string) => readFileSync(path.join(REPO_ROOT, file), "utf8");
const lines = (file: string) => read(file).split(/\r?\n/);

const config = read(data.SOURCES.config);
const pyproject = read(data.SOURCES.pyproject);
const packageJson = JSON.parse(read(data.SOURCES.packageJson));
const hardware = lines(data.SOURCES.hardware);

// The second cell of the markdown row that starts with `| <item> |`, after one section heading of the hardware doc.
function cell(section: string, item: string) {
  const from = hardware.findIndex((line) => line.startsWith(section));
  expect(from, section).toBeGreaterThan(-1);
  const row = hardware.slice(from).find((line) => line.startsWith(`| ${item} |`));
  expect(row, item).toBeDefined();
  return row!.split("|")[2].trim();
}

describe("architecture page data", () => {
  it("shows the redrawn diagram, its PNG and its editable source", () => {
    expect(existsSync(path.join(REPO_ROOT, data.DIAGRAM.source))).toBe(true);
    expect(existsSync(path.join(FRONTEND, "public", data.DIAGRAM.png))).toBe(true);
    expect(data.DIAGRAM.png).toBe("/research/diagrams/system_architecture.png");
    expect(data.DIAGRAM.asOf).toBe("2026-11-22");
  });

  it("names a real source file for each component, and the file mentions what the row claims", () => {
    for (const component of data.COMPONENTS) {
      expect(component.files.length, component.name).toBeGreaterThan(0);
      for (const file of component.files) expect(existsSync(path.join(REPO_ROOT, file)), `${component.name}: ${file}`).toBe(true);
      expect(read(component.files[0]).includes(component.mentions), `${component.name} mentions ${component.mentions}`).toBe(true);
    }
  });

  it("lists the components the old diagram missed", () => {
    const names = data.COMPONENTS.map((c) => c.name).join(" | ");
    for (const wanted of ["Supabase Auth", "Redis", "OpenRouter", "fal.ai", "Presidio", "Langfuse", "Research", "Teacher review", "Teacher notes", "Magic pencil", "PDF export"]) {
      expect(names, wanted).toContain(wanted);
    }
  });

  it("puts the web-tier gate where main.py has it", () => {
    const web = data.COMPONENTS.find((c) => c.name.startsWith("Web-tier"))!;
    expect(web.files).toContain("backend/app/main.py");
    const body = lines("backend/app/main.py").slice(210, 240).join("\n");
    expect(body).toContain("redact_pii");
    expect(body).toContain("check_text");
  });

  it("reads each model ID from config.py", () => {
    expect(data.MODELS).toHaveLength(8);
    for (const model of data.MODELS) {
      expect(config.includes(`    ${model.setting}: str = "${model.id}"`), model.setting).toBe(true);
    }
  });

  it("reads each library version from pyproject.toml or package.json", () => {
    for (const lib of data.BACKEND_LIBS) expect(pyproject.includes(`"${lib.name}${lib.version}"`), lib.name).toBe(true);
    expect(pyproject).toContain(`requires-python = "${data.PYTHON_VERSION}"`);
    for (const lib of data.FRONTEND_LIBS) {
      const declared = packageJson.dependencies?.[lib.name] ?? packageJson.devDependencies?.[lib.name];
      expect(declared, lib.name).toBe(lib.version);
    }
  });

  it("copies the training hardware from the restored hardware doc", () => {
    for (const row of data.TRAINING) expect(cell("## 7.", row.item), row.item).toContain(row.value);
    expect(hardware.join("\n")).toContain("the record itself does not name the provider");
  });

  it("states hosting as Northflank, North America, free tier", () => {
    const text = read(data.SOURCES.hardware);
    expect(text).toContain("Northflank, North America region, free tier");
    expect(text).toContain("Frontend on Vercel");
    expect(text).toContain("The Supabase project region is not recorded in any tracked doc.");
    expect(read(data.SOURCES.techStack)).toContain("**Northflank** (North America region, free tier; D-07)");
  });

  it("lists only the confirmed development hardware, at the runbook line that says it", () => {
    expect(lines(data.SOURCES.runbook)[data.RUNBOOK_GPU_LINE - 1]).toContain("RTX 3050 Ti has 4 GB VRAM");
    const confirmed = data.DEV_HARDWARE.filter((row) => row.value !== data.OWNER_TO_SUPPLY);
    expect(confirmed.map((row) => row.item)).toEqual(["Graphics card"]);
    expect(confirmed[0].value).toBe("NVIDIA RTX 3050 Ti, 4 GB VRAM");
    expect(data.DEV_HARDWARE.map((row) => row.item)).toEqual(["Processor", "Memory", "Graphics card", "Storage"]);
  });

  it("names no researcher or contact detail", () => {
    expect(JSON.stringify(data)).not.toMatch(/@[a-z]+\.[a-z]+|\+63|Hanseooo/i);
  });
});
