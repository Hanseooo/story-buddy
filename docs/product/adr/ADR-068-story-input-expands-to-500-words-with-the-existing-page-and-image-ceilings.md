# ADR-068 — Story input expands to 500 words with the existing page and image ceilings

**Status:** Accepted (2026-10-11; owner confirmed 500 words after the frontend/backend mismatch
and ADR-037 amendment requirement were explained) · amends ADR-037 decision 1's word ceiling
only · no schema, API shape, provider, or model change

**Context:**

The owner requested a larger story input limit. The existing frontend and backend both enforce
300 words, rather than the initially remembered 350 characters. Changing only the frontend
would allow a child to submit text whose ending the backend would then discard.

**Decision:**

1. Set `MAX_STORY_WORDS = 500` in `frontend/app/s/[profileId]/write/page.tsx` and
   `backend/app/config.py`. Exactly 500 whitespace-separated words are accepted intact.
2. The frontend keeps the existing `Too long!` state and disables submission above 500 words,
   preserving the child's text for editing. The backend keeps its paragraph → sentence → hard-cut
   policy above 500 words, including `truncated=true` and the retains-half floor (now 250 words).
3. Keep `MIN_STORY_WORDS = 5`, `MAX_TITLE_CHARS = 80`, `MAX_SCENES = 10`, three consistency
   attempts per scene, `IMAGE_BUDGET = 55`, and `RECURSION_LIMIT = 87`. The deterministic scene
   merge still owns the page ceiling. No graph or moderation behavior changes.
4. Existing frozen corpora, labels, completed fine-tuning runs, and evaluation results are not
   regenerated or reinterpreted. This change applies to subsequent story submissions.

**Consequences:**

- Stories between 301 and 500 words can be submitted without losing their endings.
- At the joint maximum, 500 words across ten scenes average 50 words per scene, rather than
  the former 30. Longer inputs may produce denser pages and need more text processing.
- The structural paid-image ceiling remains 55 because it is bounded by scene count and retry
  count. This does not establish unchanged latency, text-provider cost, or visual quality.
- ADR-037 remains the historical record. Live specifications use this amendment for the word cap.

**Verification:**

Existing frontend boundary tests cover submitting all 500 words and blocking 501 without
discarding text. Backend tests cover preserving 500, clamping 501, paragraph/sentence cuts,
the floor guard, and the API's stored text and truncation flag. No paid quality probe is required
or claimed by this amendment.
