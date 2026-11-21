// Exports every research figure to frontend/public/research/diagrams/ as a PNG and writes manifest.json.
// Hand-run, from frontend/:  node scripts/export-research-figures.mjs [baseUrl]
//
// Prerequisites
//   - the globally installed `playwright-cli` (pnpm add -g @playwright/cli) with Chromium installed
//   - `pnpm dev` running (default http://localhost:3000; pass another base URL as the first argument)
//   No project dependency is added: the script uses node's stdlib and shells out to playwright-cli.
//
// What it writes (light colour scheme, 2x device scale, element screenshots, white background)
//   - <name>.png for each docs/diagrams/drawio/<name>.drawio.svg (inlined in a white page by a throwaway local
//     server, because the browser blocks file: URLs)
//   - <chart-id>.png for each chart, a screenshot of its [data-chart-id] figure on the running page
//   - manifest.json: per PNG its source, the SHA-256 of its source file (the drawio file, or a chart's data.ts)
//     and the export date
//
// Re-run after editing any .drawio.svg or a chart page's data.ts; figures.test.ts fails on a stale hash or a missing PNG.
import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const FRONTEND = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const DRAWIO_DIR = resolve(FRONTEND, "../docs/diagrams/drawio");
const OUT_DIR = join(FRONTEND, "public/research/diagrams");
const BASE = (process.argv[2] ?? "http://localhost:3000").replace(/\/$/, "");
const SESSION = "research-figures";

// Charts are [data-chart-id] figures. Add a new chart's id and page here; figures.test.ts fails until
// this list matches the CHARTS in each page's data.ts. A chart's numbers live in its page's data.ts,
// so that file's hash is the chart's source hash.
const CHARTS = [
  ["/research/results", "judge-confusion-matrices"],
  ["/research/results", "judge-f1-precision-recall"],
  ["/research/results", "judge-catches-false-alarms"],
  ["/research/results", "judge-validation-checkpoints"],
  ["/research/limitations", "reference-check-outcomes"],
  ["/research/limitations", "page-check-outcomes"],
];
const dataFile = (page) => `frontend/app/(research)/research/(reference)/${page.split("/").pop()}/data.ts`;

const cfgPath = join(tmpdir(), `${SESSION}.config.json`);
writeFileSync(
  cfgPath,
  JSON.stringify({
    browser: {
      browserName: "chromium",
      launchOptions: { headless: true },
      contextOptions: { deviceScaleFactor: 2, colorScheme: "light", viewport: { width: 2000, height: 1200 } },
    },
  }),
);

// Async on purpose: a blocking call would starve the local SVG server the browser fetches from.
const run = promisify(execFile);
async function cli(...args) {
  const { stdout: out } = await run("playwright-cli", [`-s=${SESSION}`, ...args], { encoding: "utf8", shell: true });
  if (out.includes("### Error")) throw new Error(`playwright-cli ${args.join(" ")}\n${out}`);
  return out;
}
const q = (s) => `"${s}"`;
// The CLI's own screenshot command is 1x; run-code lets us ask for device pixels (2x).
// A chart figure is restyled for the export: white, square, flat, and without its download links.
const PLAIN_CHART =
  "document.documentElement.style.background = document.body.style.background = '#fff'; el.style.cssText += ';background:#fff;border:0;border-radius:0;box-shadow:inset 0 0 0 3px #fff;outline:0;max-width:none;padding-bottom:20px'; el.querySelectorAll('a[download]').forEach(a => a.closest('p').remove());";
const shot = (selector, file, prep = "") =>
  cli(
    "run-code",
    q(
      `async page => { const el = page.locator('${selector}').first(); await el.evaluate(el => { ${prep} }); await el.screenshot({ path: '${file.replaceAll("\\", "/")}', scale: 'device' }); }`,
    ),
  );
// LF-normalised, matching figures.test.ts, so autocrlf checkouts hash the same as CI.
const sha256 = (file) =>
  createHash("sha256").update(readFileSync(file, "utf8").replace(/\r\n/g, "\n")).digest("hex");

const server = createServer((req, res) => {
  const name = decodeURIComponent((req.url ?? "").split("?")[0]).replace(/^\//, "");
  try {
    if (!/^[\w.-]+\.drawio\.svg$/.test(name)) throw new Error("not a drawio file");
    // A bare .svg URL never fires domcontentloaded in this browser, so the file is inlined in a white page.
    const svg = readFileSync(join(DRAWIO_DIR, name), "utf8");
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    // Padding and visible overflow keep edge strokes, which some sources draw on their bounds, from being clipped.
    res.end(
      `<!doctype html><meta charset="utf-8"><style>svg{overflow:visible;display:block}</style><body style="margin:0;background:#fff"><div id="fig" style="display:inline-block;padding:12px;background:#fff">${svg}</div>`,
    );
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise((ok) => server.listen(0, "127.0.0.1", ok));
const origin = `http://localhost:${server.address().port}`;

const date = new Date().toISOString().slice(0, 10);
const entries = [];
mkdirSync(OUT_DIR, { recursive: true });
try {
  await cli("open", "about:blank", `--config=${q(cfgPath)}`);
  for (const file of readdirSync(DRAWIO_DIR).filter((f) => f.endsWith(".drawio.svg")).sort()) {
    const name = file.replace(/\.drawio\.svg$/, "");
    await cli("goto", q(`${origin}/${file}`));
    await shot("#fig", join(OUT_DIR, `${name}.png`));
    entries.push({
      png: `${name}.png`,
      kind: "diagram",
      source: `docs/diagrams/drawio/${file}`,
      sourceSha256: sha256(join(DRAWIO_DIR, file)),
      exportedOn: date,
    });
    console.log(`diagram ${name}`);
  }
  await cli("resize", "1280", "1000");
  for (const [page, id] of CHARTS) {
    await cli("goto", q(`${BASE}${page}`));
    await shot(`[data-chart-id=${id}]`, join(OUT_DIR, `${id}.png`), PLAIN_CHART);
    entries.push({
      png: `${id}.png`,
      kind: "chart",
      source: { page, chartId: id, dataFile: dataFile(page) },
      sourceSha256: sha256(resolve(FRONTEND, "..", dataFile(page))),
      exportedOn: date,
    });
    console.log(`chart ${id}`);
  }
} finally {
  try {
    await cli("close");
  } catch {}
  server.close();
  rmSync(cfgPath, { force: true });
}
writeFileSync(join(OUT_DIR, "manifest.json"), `${JSON.stringify({ exportedOn: date, figures: entries }, null, 2)}\n`);
console.log(`wrote ${entries.length} figures and manifest.json to ${OUT_DIR}`);
