# ADR-070 — Static synthetic examples illustrate visible limitations

**Status:** Accepted (2026-10-13) · owner approved the chat design and instructed implementation,
commit and push to main · supersedes ADR-067 decision 7 for these examples only · extends
ADR-065's static, synthetic-only publication boundary

**Context:** The owner wants visible failures illustrated on `/research/limitations`, with images
bundled in the frontend so a Supabase subscription downgrade does not affect the page. The chat
design proposed four examples, explicit requirements and output roles, and a link to existing
Dataset identity examples. The owner authorized verification and selection of the remaining
candidates, rather than a separate contact-sheet selection step for this change. This does not
change the selection procedure for the Dataset page's six frozen examples.

**Decision:**

1. Add four hand-picked synthetic training examples to the existing public, static limitations
   page: duplication, stated body count, action mismatch and background groups without references.
   Reuse the already-public Dataset image for the last example. Publish no donated or held-out
   assets, private screenshots, private stories or new model draws.
2. Store four new resized WebP files in `frontend/public/research/limitations/`. Use local image
   paths only, without Supabase, a backend request or a new dependency. Preserve full compositions,
   reserve their dimensions, lazy-load images and stack comparisons on narrow screens.
3. State the requirement and visible discrepancy beside each example. Identify story, scene or
   reference, attempt and selected-final status. Show the action example's reference for context.
   These are historical generation-version-4 captures, not proof of present failure frequency.
4. Keep existing audit numbers, provisional caveats, group-guide wording and research results
   unchanged. Add a nearby hand-picked/illustrative disclaimer and a Dataset link for identity
   drift. Textual limitations such as scope, sampling and labels do not acquire decorative images.
5. Record source commits and asset SHA-256 values in the feature spec. Verify source provenance,
   manifests, selection and requirements before conversion. Selection and caption review here
   are AI-assisted, not new independent human labels or a research finding.

**Consequences:** The page and its images work with Supabase and the backend unavailable. These
selected images become permanent public repository artifacts. Existing moderation, storage access,
judge, prompt, gate, selection and research protocols remain unchanged.

**Alternatives:** Thumbnails in every limitation card make evidence too small and imply that every
limitation is visually demonstrable. A separate gallery adds navigation and a route without need.
Remote Storage URLs conflict with the owner's requested hosting independence.

Implementation and provenance: [research limitations examples spec](../../specs/research-limitations-examples.md).
