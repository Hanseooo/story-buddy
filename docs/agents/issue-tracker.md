# Issue tracker: Local Markdown

- Tickets: `.scratch/<feature>/issues/<NN>-<slug>.md`, numbered from `01`.
- Specs: `docs/specs/<feature>.md`, following the repository's spec-first rules.
  Tickets link to that spec rather than keeping a second copy.
- Record triage state near the top as `Status: <role>`.
  Use the roles in `triage-labels.md`. Preserve existing bold Status lines.
- Append discussion under `## Comments`.
- Publishing a ticket means creating its Markdown file.
- Fetching a ticket means reading its referenced file.
  If a number matches multiple features, ask which feature.

## Wayfinding

- Map: `.scratch/<feature>/map.md`.
- Child tickets use the numbered issues directory above.
- Record `Type: research|prototype|grilling|task`.
- Record dependencies as `Blocked by: <ticket paths>`.
- Track execution separately as `Progress: open|claimed|resolved`.
- Choose the first numbered open, unclaimed ticket whose blockers are resolved.
- Claim before starting work.
- Resolve by appending `## Answer`, setting Progress to resolved,
  and adding the answer summary and ticket link to the map.
