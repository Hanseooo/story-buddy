# ADR-013 — Caption source and PDF export

**Status:** Accepted · **revised 2026-07-21** — PDF renderer resolved to WeasyPrint (D-2) · **the export
half is retired by [ADR-058](./ADR-058-narration-and-pdf-export-are-cut-from-the-evaluated-scope.md)**
(2026-09-04): PDF export is cut and WeasyPrint never shipped. **The caption decision below — the child's
verbatim post-redaction text, never LLM-rewritten — is untouched and remains live.**

**Context:** Captions can be the child's words or LLM-rewritten; each generated surface adds a moderation surface and a fidelity risk. Export needs a PDF renderer.

**Decision:** Captions are the **child's verbatim text excerpt** (post-PII-redaction), not rewritten. PDF export renders an **HTML storybook template → PDF server-side with WeasyPrint** (`@react-pdf/renderer` is the lighter client-side fallback).

**Consequences:** Preserves fidelity; no extra generation/moderation surface for captions. **D-2 resolved (2026-07-21): WeasyPrint**, not Playwright — the storybook is a static paged-media template (one page per scene: image + verbatim caption, no JS-driven layout), which is WeasyPrint's purpose-built domain. Pure-Python, small runtime footprint (pango/cairo system libs, no browser binary), the right call on a RAM-constrained worker (§9).

**Alternatives:** LLM-polished captions — rejected for MVP (fidelity + moderation surface); could be an opt-in Future Work toggle. **Playwright** (server-side Chromium) — rejected as the PDF renderer: a full browser engine and its RAM cost to render a static template that needs no JS.
