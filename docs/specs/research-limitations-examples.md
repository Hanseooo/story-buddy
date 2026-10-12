# Feature Spec — Research limitations examples

**Status:** built (2026-10-13, approved chat design) · **Owner surface:** `/research/limitations`
**Derived from:** MASTER_SPEC §5–6 · **Rationale:** ADR-065, ADR-067, ADR-070

## 1. Purpose

Illustrate visible limitations using existing synthetic captures bundled with the frontend.
The page remains useful without Supabase or a running backend.

## 2. Contract and position

Static server component at `frontend/app/(research)/research/(reference)/limitations/page.tsx`.
Reads local `data.ts` and committed public WebP files. No Story Memory read at runtime, API,
schema, authentication, storage policy or pipeline change.

## 3. Behavior and acceptance criteria

- Add an anchored “Examples of visible limitations” section after the common-defects table.
- Four examples show a requirement, visible discrepancy, synthetic story ID, training split,
  scene/character, attempt and selected-final/reference status. The action example also shows its
  canonical reference. Identity drift links to `/research/dataset#examples`.
- Display full images at their intrinsic 768×576 ratio, with meaningful alt text, reserved size,
  native lazy loading and responsive comparisons stacked below `sm`. Use existing design tokens.
- State that the hand-picked examples do not establish frequency or current performance. The
  audit date is 2026-10-08, not an asserted generation date; captures use generation/judge/constraint
  versions 4/4/4. Current prompts and completed research results are not changed.
- Preserve all existing numbers, provisional qualifications, nine limitations and tried-fix text.
- Images load from `/research/limitations/` or the existing `/research/dataset/` directory only.
  No external image request, dependency, session read, Supabase read or paid call.
- Use the inherited reference-route error boundary and existing page navigation. Images are
  informational, with captions available independently of successful image loading.
- The shared Research header's tab list wraps within 320px. Its existing outer wrapping did not
  constrain the inner unwrapped navigation, which measured 349px; only CSS classes change, with
  tab destinations, visibility and account behavior preserved.

## 4. Selected examples and requirements

Source metadata was inspected before each memory: all four stories are `synthetic`, split `train`.
Source images matched `data/judge/corpus/runs/<story>/assets.json` SHA-256 values before inspection.
The owner authorized assistant verification/selection and publication in this change (ADR-070).
This is AI-assisted illustration selection, not independent human annotation.

| Story / asset | Requirement shown | Role and observation |
|---|---|---|
| syn-021 / s6-1 | Lala looks up at the sky. | Scene s6's selected final, attempt 1; the named cast is only c0 (Lala), but two copies are depicted. |
| syn-002 / ref-c1-1 | It had six legs and its wool was green moss and little white flowers grew in it. | Final canonical reference for c1 (Mopsi), draw 1; only four legs are depicted. No claim about a page inheriting this defect is made from this image alone. |
| syn-019 / s1-3 and ref-c0-1 | He practised breathing fire every night and what came out was air, because he was a sock. | Scene s1's selected final, attempt 3, and final canonical reference c0, draw 1; the page depicts flames. Other body/cast defects coexist; this example does not isolate a cause. |
| syn-016 / s2-4 | He called himself General Lint and he commanded an army of six smaller dust bunnies. | Scene s2's selected final, attempt 4; the direction requests his soldiers, but the roster references only Lint and the vacuum. The page depicts helmeted humanoid soldiers. Reuses public Dataset pair 1843d7d4835a8397's page. This historical run's four attempts are not a statement of the current attempt cap. |

Source files resolve from `data/judge/corpus/`, with campaign prefix
`<story>--campaign-1d28e1f3bc4b64625e3b3cc8f5765043`, except syn-019, whose prefix is
`syn-019--readmit-5ffaafaecb324f749fbc400cbb97eb76`.

| Source asset suffix | Original SHA-256 | Public asset |
|---|---|---|
| syn-021 scene `_s6-1.png` | `29ac85c288bc7c6c8f6a874626f8252159807a86b4f3aa3091d6f0cd56ac6aff` | `/research/limitations/syn-021-s6-1.webp` |
| syn-002 ref `_ref-c1-1.png` | `072e83c11f1f754f01d4560eefc53e2bc9933d96eb05711d23ee0fcac8e9c8fa` | `/research/limitations/syn-002-ref-c1-1.webp` |
| syn-019 ref `_ref-c0-1.png` | `c353b2471755caf2d1af1895810c4434017dd61ff6a6e0ff37f3e8e7d92f5c27` | `/research/limitations/syn-019-ref-c0-1.webp` |
| syn-019 scene `_s1-3.png` | `7da4f6fbacf61f6ce482b43d5f22c65a8d9e85e7a914b78f1575ad467523dbc2` | `/research/limitations/syn-019-s1-3.webp` |
| syn-016 scene `_s2-4.png` | `a4dc1af1b3b739bb0ad312be5672d7415fa75c03bc4da74276e1c32089344d99` | Existing `/research/dataset/1843d7d4835a8397-page.webp` |

Capture commits: syn-002 `1ddf1ceacabcae5b3167ecb54e18396f0492af78`; syn-021 and syn-016
`f2048a463a8fd963d725878da8a861980e72ab58`; syn-019
`56d7f4c2b9b63e4a7bde4edae77496e99ad05680`. Styles respectively Gouache, Paper Cutout,
Cartoon and Cartoon. Captions make no inferred generated-on date or current quality claim.

Conversion uses the already-installed Sharp package: resize 1024×768 originals to 768×576 with
`fit: inside`, no crop or enlargement, then WebP quality 85. The four new files total 112,140 bytes.
The existing Dataset file is reused unchanged.

## 5. Cross-cutting concerns

- CC-2/4: only authorized synthetic examples, no private stories/screenshots or held-out assets.
  ADR-065/070 allow these curated public assets without changing production asset privacy.
- CC-3/7: existing immutable captures only, no draws; retained source hashes and version boundaries.
- CC-6/8/9: informative alt text, focusable section/Dataset links, responsive full compositions,
  existing adult research-page design and error handling.

## 6. Verification

Existing page/data tests gain one visible-example test and one static-asset/provenance test.
Run them red before implementation. Run frontend lint, build and full tests with placeholder
configuration and dotenv disabled. Inspect desktop and 320px layouts and locally served assets.
No image-quality assertions in CI, new research labels or paid experiments.

Fresh verification: frozen frontend install, lint and production build passed; 694 tests in 73
files passed. Browser inspection loaded all five local images with external requests blocked,
confirmed desktop/320px layout, stacked mobile comparisons, zero horizontal overflow and both
example navigation links. An unchanged gallery test timed out once during concurrent checks,
then its 10-test suite and the full suite passed unchanged without concurrent build/lint work.
No timeout was increased and no test was skipped. The temporary dotenv guard's initial Windows
path escaping and lint errors were resolved in the verification harness, which is not committed.
