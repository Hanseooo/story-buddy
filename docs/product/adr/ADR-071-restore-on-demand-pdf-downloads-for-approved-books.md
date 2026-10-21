# ADR-071 — Restore on-demand PDF downloads for approved books

**Status:** Accepted (2026-10-21), owner approved direct PDF downloads, the renderer dependency,
runtime libraries and API addition. Supersedes ADR-058's PDF cut only, retains its narration cut, and restores
ADR-013's server-side renderer decision. ADR-017's teacher approval gate and ADR-027's
on-demand, never-stored PDF decision remain in force.

## Context

The owner requests PDF export with UX as the priority. Export does not exist. ADR-058 deliberately
removed it from product and evaluated scope, and requires a new accepted ADR before reinstatement.
The reader currently has a mobile header defect, so a download control must not crowd its title.

## Decision

1. Offer a direct **Download PDF** action for the student's own completed, teacher-approved book.
   Place it below the reader header rather than beside the mobile title and reading-mode toggle.
   Peer-book export and a separate teacher export surface are outside this first implementation.
2. Restore the previously selected **WeasyPrint** renderer. Generate the PDF on the backend when
   requested, then return it as a download. This includes the approved backend dependency,
   its runtime libraries, and a new API route. No new service, datastore, migration, pipeline node,
   generation call, or persisted PDF.
3. Add `GET /jobs/{job_id}/pdf`. Authenticate through
   the existing mechanism and authorize the student's own row on every request. Require a
   complete, nonempty book, `approved_at` set and `rejected_at` unset. Do not treat the visibility
   of a button or an already-signed image URL as authorization. A later request after approval
   withdrawal must fail. An already-downloaded file cannot be revoked.
4. Include only the checked stored title (or `Untitled`), finalized moderated illustrations,
   existing post-redaction captions and page numbers. Never export `input_text`, character
   references, failed attempts, internal errors, asset URLs, or child/account identifiers.
5. Use an A4 portrait layout with each scene starting on a new page, an uncropped illustration
   and readable caption. Preserve the full caption, using continuation pages when necessary.
   Generate no cover illustration. PDF bytes and source-image fetches stay transient.
6. Provide an announced **Preparing PDF…** state, prevent duplicate requests, and keep reading
   and bookshelf navigation usable. A failure shows a short retry message and retains the book.
   Closing or navigating away cancels the browser request and discards its result.
7. In this implementation, propagate the restored scope through the existing product, safety/policy,
   functional-verification and capstone documents. Preserve historical reported results and
   struck-through preregistered prose. Re-widen the future Tool A criterion with an explicit
   amendment and separate verification evidence, never retroactively count export as tested.
   No change to Objective 4's judge comparison or narration.

## Alternatives

- **Browser print / Save as PDF:** avoids a renderer dependency and endpoint, but requires the
  family to navigate the system print flow. It is a different interaction from direct download.
- **Client-side PDF renderer:** keeps rendering off the backend but introduces a frontend
  dependency and device-side image/font processing. It also moves work onto the student's phone.
- **Server-generated direct download (recommended):** adds backend/runtime setup but centralizes
  authorization and document layout, with one consistent reader action.

## Consequences and acceptance

Export produces a durable copy outside classroom access controls. Teacher approval is a product
gate, not a way to revoke a saved copy. Policy/consent text must be reconciled before deployment.
Validate mobile download/open behavior, full captions, image completeness, typography and denial
after approval withdrawal before marking the feature built.

Implementation is described in [the export spec](../../specs/export-pdf.md). Deployment and
evaluation claims require the verification recorded there. Owner approval does not alter historical
research results or replace adviser approval of a revised questionnaire.
