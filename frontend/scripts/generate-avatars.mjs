// Generates the fixed avatar set into public/avatars/ from the manifest below.
// Build-time only — DiceBear is a devDependency and never ships to the client.
// Run: node scripts/generate-avatars.mjs
//
// Every style used here is CC0 1.0 (no attribution obligation). Do not add a
// CC BY style (adventurer, big-smile, croodles, fun-emoji, dylan, micah,
// miniavs, personas, toon-head) without also adding the attribution surface.
//
// ponytail: the manifest is the whole config. No CLI flags, no randomness —
// regenerating always produces byte-identical files.

import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { createAvatar } from "@dicebear/core";
import { lorelei, openPeeps, pixelArt, thumbs } from "@dicebear/collection";

const STYLES = { lorelei, openPeeps, pixelArt, thumbs };

// Soft backgrounds that read well inside a circular crop on the app's surfaces.
const BG = {
  blue: "b6e3f4",
  peach: "ffd5dc",
  mint: "c0eecf",
  butter: "ffdfbf",
  lilac: "d1d4f9",
  sky: "a0e7e5",
};

/**
 * id      — stored in profiles.avatar_id and used as the filename. Never free text.
 * style   — key of STYLES.
 * seed    — fixes everything not pinned below.
 * options — deliberate overrides. skinColor is pinned rather than left to the
 *           seed so the spread across tones is guaranteed, not hoped for.
 */
const MANIFEST = [
  // ── Open Peeps — hand-drawn humans ───────────────────────────────────────
  {
    id: "peeps-01",
    style: "openPeeps",
    seed: "story",
    options: { backgroundColor: [BG.blue] },
  },
  {
    id: "peeps-02",
    style: "openPeeps",
    seed: "ani",
    options: { backgroundColor: [BG.peach] },
  },
  {
    id: "peeps-03",
    style: "openPeeps",
    seed: "nganoman",
    options: { backgroundColor: [BG.mint] },
  },
  {
    id: "peeps-04",
    style: "openPeeps",
    seed: "chatjosseppe",
    options: { backgroundColor: [BG.butter] },
  },
  {
    id: "peeps-05",
    style: "openPeeps",
    seed: "41gijgpx",
    options: { backgroundColor: [BG.lilac] },
  },
  {
    id: "peeps-06",
    style: "openPeeps",
    seed: "41g",
    options: { backgroundColor: [BG.sky] },
  },

  // ── Pixel Art — game-sprite look ─────────────────────────────────────────
  {
    id: "pixel-01",
    style: "pixelArt",
    seed: "fc46p71n",
    options: { backgroundColor: [BG.blue] },
  },
  {
    id: "pixel-02",
    style: "pixelArt",
    seed: "rqsmos6h",
    options: { backgroundColor: [BG.peach] },
  },
  {
    id: "pixel-03",
    style: "pixelArt",
    seed: "dmt0b0q6",
    options: { backgroundColor: [BG.mint] },
  },
  {
    id: "pixel-04",
    style: "pixelArt",
    seed: "0dt4r12y",
    options: { backgroundColor: [BG.butter] },
  },
  {
    id: "pixel-05",
    style: "pixelArt",
    seed: "f9toqxgs",
    options: { backgroundColor: [BG.lilac] },
  },
  {
    id: "pixel-06",
    style: "pixelArt",
    seed: "ppt5l7a6",
    options: { backgroundColor: [BG.sky] },
  },

  // ── Lorelei — line-art faces ──────────────────────────────────────────────
  {
    id: "lorelei-01",
    style: "lorelei",
    seed: "Sampaguita",
    options: { backgroundColor: [BG.blue] },
  },
  {
    id: "lorelei-02",
    style: "lorelei",
    seed: "Felix",
    options: { backgroundColor: [BG.peach] },
  },
  {
    id: "lorelei-03",
    style: "lorelei",
    seed: "Nar",
    options: { backgroundColor: [BG.mint] },
  },
  {
    id: "lorelei-04",
    style: "lorelei",
    seed: "e8jd4a2h",
    options: { backgroundColor: [BG.butter] },
  },
  {
    id: "lorelei-05",
    style: "lorelei",
    seed: "Bundok",
    options: { backgroundColor: [BG.lilac] },
  },
  {
    id: "lorelei-06",
    style: "lorelei",
    seed: "ar2h8clv",
    options: { backgroundColor: [BG.sky] },
  },

  // ── Thumbs — abstract. The non-face option, so it is not a fallback. ─────
  {
    id: "thumbs-01",
    style: "thumbs",
    seed: "Kislap",
    options: { backgroundColor: [BG.blue] },
  },
  {
    id: "thumbs-02",
    style: "thumbs",
    seed: "Sigla",
    options: { backgroundColor: [BG.peach] },
  },
  {
    id: "thumbs-03",
    style: "thumbs",
    seed: "Himig",
    options: { backgroundColor: [BG.mint] },
  },
  {
    id: "thumbs-04",
    style: "thumbs",
    seed: "Diwa",
    options: { backgroundColor: [BG.butter] },
  },
  {
    id: "thumbs-05",
    style: "thumbs",
    seed: "Alasmxksa5xb",
    options: { backgroundColor: [BG.lilac] },
  },
  {
    id: "thumbs-06",
    style: "thumbs",
    seed: "Yakap",
    options: { backgroundColor: [BG.sky] },
  },
];

const outDir = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "avatars");
mkdirSync(outDir, { recursive: true });

const rendered = MANIFEST.map(({ id, style, seed, options }) => {
  const svg = createAvatar(STYLES[style], { seed, radius: 50, ...options }).toString();
  writeFileSync(join(outDir, `${id}.svg`), svg);
  return { id, style, svg };
});

// Contact sheet — the review surface. Every avatar the picker can offer, numbered.
const cards = rendered
  .map(
    ({ id, style, svg }, i) => `<figure>
      <div class="a">${svg}</div>
      <figcaption><b>${i + 1}</b> ${id}<br><span>${style}</span></figcaption>
    </figure>`
  )
  .join("\n");

writeFileSync(
  join(outDir, "index.html"),
  `<!doctype html><meta charset="utf-8"><title>Avatar set — ${rendered.length}</title>
<style>
 body{font:14px system-ui;margin:2rem;background:#fafafa;color:#111}
 h1{font-size:1.25rem}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:1.25rem;margin-top:1.5rem}
 figure{margin:0;text-align:center}
 .a{width:96px;height:96px;margin:0 auto;border-radius:50%;overflow:hidden;background:#fff}
 .a svg{width:100%;height:100%;display:block}
 figcaption{margin-top:.5rem;font-size:12px}
 figcaption span{color:#777}
</style>
<h1>Avatar set — ${rendered.length} options</h1>
<p>Generated from <code>scripts/generate-avatars.mjs</code>. All styles CC0 1.0.</p>
<div class="grid">${cards}</div>`
);

console.log(`Wrote ${rendered.length} avatars + index.html to public/avatars/`);

const libDir = join(dirname(fileURLToPath(import.meta.url)), "..", "lib");
writeFileSync(
  join(libDir, "avatars.ts"),
  [
    "// Generated by scripts/generate-avatars.mjs — do not edit.",
    `export const AVATAR_IDS = [`,
    rendered.map(({ id }) => `  "${id}",`).join("\n"),
    `] as const;`,
    ``,
    `export type AvatarId = (typeof AVATAR_IDS)[number];`,
    ``,
  ].join("\n")
);
console.log(`Wrote lib/avatars.ts (${rendered.length} ids)`);
