# ADR-083 — `/research` is a hub, the paper's chapters get static pages, and diagrams export to PNG

**Status:** Accepted (2026-11-21) · the owner accepted it in the research-page-refresh grill session
(D-19) · extends ADR-065, ADR-066 and ADR-067 · adds public frontend routes · no backend route,
no migration, no `StoryMemory` or `contracts/` change · no Supabase read

**Specified by:** [`docs/specs/research-page-refresh.md`](../../specs/research-page-refresh.md)
(D-01, D-02, D-03, D-13).

## Context

Groupmates use the public research pages to write the paper. Those pages cover the dataset, the
partial judge result and the limitations, but not the paper's pipeline, methodology, instruments,
architecture, ethics or per-objective answers. `/research` is a landing page with its own nav, and
the header has one tab per page, which does not fit at 390px once more pages exist.
AGENTS.md freezes ADRs and requires a new one before a new public route is built.

## Decision

1. **New static public routes (D-01, D-02).** Six server components under
   `app/(research)/research/(reference)/`: `/research/pipeline`, `/research/methodology`,
   `/research/instruments`, `/research/architecture`, `/research/ethics` and
   `/research/objectives`. Each is one paper chapter or section. Each keeps ADR-065 decision 1: it
   fetches nothing and reads no session, and `frontend/middleware.ts` is not changed.
2. **`/research` is the hub (D-02, D-03).** It lists every research page in paper order in three
   groups, Methodology, Results and Reference, each entry with a one-line summary and the paper
   section it feeds. It reads no session and no profile, so it needs no `loading.tsx` (D-26).
3. **Three-item header (D-03).** The header shows Research home, Docs and Runs for every viewer. The
   role-gated Annotate and Adjudicate stay for researchers (D-24). Dataset, Results and Limitations
   leave the header and are reached from the hub. Every page except the hub starts with a back link
   to `/research` and ends with Previous and Next links in the hub's order. Runs
   (`/research/metrics/`) is outside that order because it needs sign-in.
4. **Diagrams export to PNG (D-13).** Each diagram under `docs/diagrams/` is exported to a PNG,
   committed with a manifest of source hashes, and shown on its page with alt text, an "As of"
   caption, a download link and a link to the editable source. A missing PNG, or a source changed
   without re-export, fails a test. Export uses Playwright, which is already installed.
5. **Rules kept from ADR-065/066/067.** Static pages only. Synthetic material only: no donated image
   and no held-out test image, and donated material only as whole-split counts (ADR-065 decision 5).
   Every number and factual sentence on a page lives in a tracked source file that the page names,
   and its `data.test.ts` fails when the page and the source disagree (ADR-066 decision 6).
6. **Pipeline facts come from code (SH-08).** The node count and names, the page and attempt caps,
   the retry taps and the word limit (ADR-068) are tested against `backend/pipeline/graph.py` and
   `backend/app/config.py`, so a code change fails the page test.

## Consequences

- All new pages work with Supabase and the backend down, as ADR-065 requires.
- Dataset, Results and Limitations are one click further from the header. The hub and
  Previous/Next replace the tabs.
- Each new page needs a source doc first (SH-02), so the source-doc corrections land before the
  page code.
- Donated story IDs, plot summaries and character names stay in the public repo and are disclosed on
  the ethics page (D-09). The pages themselves show none.
- PNGs are committed binaries and stay in repository history.
- Adding a pipeline node now fails tests on the pipeline page and on the run-viewer map until both
  are updated.

## Alternatives considered

- **A longer single `/research` page.** Rejected by the owner (D-01): it does not map onto the
  paper's chapters.
- **A flat header with a tab per page.** Rejected (D-03): about 11 tabs would hide most items
  off-screen on a phone.
- **Export diagrams with draw.io desktop.** Rejected (D-13): not installed. Playwright is.
