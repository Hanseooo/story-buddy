# 06 — Source docs, docs hub and ADR

Index: [../research-page-refresh.md](../research-page-refresh.md). These land first in the PR
(index §4.2), because the page tests pin page copy to these docs. Evidence:
`evidence/audit-3-docs-paper.md` (D- and P- rows).

## US-24 Correct the repo docs

As a groupmate reading the repo docs, I want them to agree with the owner's answers and the code, so
that the pages built from them are correct.

Applies: SH-02

- **AC-01** Each doc is corrected, and each change cites its decision or code line:

  | Doc | Change |
  |---|---|
  | `methodology.md`, `ethics_and_safety.md`, `RESEARCH_PROTOCOL.md`, `PRD_v2.md` | Matina Aplaya → Vicente Hizon, Sr. ES (D-04). Grep the whole repo excluding `.worktrees/` and `brag-output*/`; every hit changes. |
  | ADR-008 (frozen) | No edit. A new amendment ADR or a note in `ADRs.md`, following the AGENTS.md ADR rule (D-04). |
  | `research_instruments.md`, `iso-25010-scope-freeze.md`, `evaluation_instruments_brief.md` | Expert panel and 7-question interview (D-05); 6 ISO characteristics, 23 items, scale 5 = Strongly Agree, ≥30 respondents, descriptive statistics only, no CVI or α (D-06). |
  | `TECH_STACK.md` | Region: North America, free tier (D-07). Line 260's "unconfirmed" is removed. |
  | `hardware_and_hosting.md` | Restored from `2cb6d2f^` (D-15), then updated with the training hardware and hosting facts of US-18. |
  | `methodology.md` | 3–10 scenes, not 10–15. Up to two redraws, not one retry. 12 donated books generated. Teacher-review mode. Implementation-site options (D-16). |
  | `system_architecture.md` | One retry count (up to two); Mistral primary and Gemma backstop instead of "NSFW ViT"; teacher-review nodes. |
  | `ethics_and_safety.md` | ADR-071/080/081/082 features; the D-08 basis; the D-09 disclosure. |
  | `group-guide.md` | §3 and §4 updated for teacher hold, magic pencil, notes and PDF; "Last updated" bumped. |
  | `research_runbook.md` | Entries for every new fact the pages cite: US-04 AC-02, US-05 AC-07–AC-09, US-09 AC-21, US-10 AC-03, US-11 AC-08. |
  | `research-changelog.md` | One row per new fact above, dated, labelled Finding or Correction. |

- **AC-10** The expert questionnaire is saved as a tracked doc, for example
  `docs/capstone/expert-evaluation-questionnaire.md`, built from the owner's 2026-11-21 paste. It
  holds the overview, the instructions, the seven questions with their guide prompts, and the
  consent form's terms. It omits the researcher's name and email. `research_instruments.md` and
  `evaluation_instruments_brief.md` point to it.
- **AC-11** `annotation-surface.md` gains a rationale section with the owner-stated reasons of
  US-27 AC-26.
- **AC-12** Objective 1 is recorded as Achieved (D-20) in `research_direction_and_goals.md` or
  `group-guide.md` §4, whichever states objective status, noting that Tool A was dropped (D-28).
- **AC-13** The ISO questionnaire is saved as a tracked doc, for example
  `docs/capstone/iso-25010-questionnaire.md`, built from the owner's 2026-11-21 paste: overview,
  instructions, scale, and the 23 items under their six headings (D-27). It omits the researcher's
  name and email. It records the consent-form mismatch as O-12. `iso-25010-scope-freeze.md` points to
  it, and its older 5-characteristic draft is marked superseded.
- **AC-02** After the change, grepping the repo for `Matina Aplaya`, `Railway` (as a host),
  `10–15 scenes` and `NSFW ViT` finds no current-state claims. Historical changelog rows may keep
  them.

## US-25 Docs hub

As a groupmate, I want the docs hub grouped by paper chapter and showing what the paper must say, so
that I can sync the paper in one place.

Applies: SH-02, SH-04

- **AC-03** `/research/docs` groups its entries by paper chapter. It adds the docs listed in
  `evidence:audit-3-docs-paper.md` D6 and D7. Each new entry is in `entries.test.ts` `REQUIRED`.
- **AC-04** Each entry shows the source doc's last-changed date. A test reads it from a "Last
  reviewed" line or the file's git date; the implementer picks one and records it.
- **AC-05** A "What the paper must say" panel lists two things:
  - `research-changelog.md` §1
  - each paper/repo correction from `evidence:audit-3-docs-paper.md` P1–P24, given its settled value
    (D-04–D-08, D-16) or "repo is right" with the source

  Open items show as open.
- **AC-06** The paper typos found ("Visibile", "Cohen's Cappa", "considerable" for κ 0.634, "31%"
  for 0.310) are listed in the panel for groupmates to fix.
- **AC-07** The entry for the pipeline diagram no longer says "as it runs today" unless the diagram
  is current (US-20).

## US-26 ADR-083

As the owner, I want the new public routes recorded as a decision, so that the frozen-ADR rule is
followed.

Applies: None

- **AC-08** A new `docs/product/adr/ADR-083-<kebab-title>.md` plus its row in `docs/product/ADRs.md`
  records:
  - the new static public routes (D-01, D-02)
  - `/research` as a hub
  - the three-item header (D-03)
  - D-13's export of diagrams to PNG

  It extends ADR-065/066/067 and keeps their static, synthetic-only rules.
- **AC-09** The owner accepted the decision on 2026-11-21 (D-19). The ADR is written with status
  Accepted and that date, before any US-01–US-03 or US-15–US-19 code.

## US-28 Retire the Tool A/B/C labels

As a groupmate, I want the docs to name the instruments plainly, so that stale labels and a tool
that was never built don't end up in the paper.

Applies: SH-02, SH-09

- **AC-14** In every live doc, "Tool B" becomes "the expert questionnaire" and "Tool C" becomes "the
  ISO/IEC 25010 questionnaire". Text about Tool A as a planned instrument is removed or replaced by
  "Objectives 1–2 are evidenced by the built pipeline, its tests and the 42 books" (D-20, D-28).
- **AC-15** `docs/specs/functional-verification-matrix.md` gets status "Dropped 2026-11-21 (D-28)"
  at the top. Its body stays as history.
- **AC-16** Frozen ADRs (008, 026, 030, 058, 071) are not edited. One dated note in `ADRs.md` says
  the labels are retired and Tool A was dropped.
- **AC-17** `research-changelog.md` gets one Correction row. Its older rows keep their wording.
- **AC-18** Afterwards, grepping `docs/` and `frontend/app/` for `Tool [ABC]` finds only frozen ADRs,
  changelog history, the dropped spec, and this spec and its evidence.
