# Feature Spec — On-demand PDF download

**Status:** implemented and locally verified (2026-10-21); deployment and physical-device download/open checks pending.
**Owner:** existing student reader and backend job routes.
**Derived from:** MASTER_SPEC §5, ADR-013, ADR-017, ADR-027, ADR-058, ADR-071 and ADR-072.

## 1. Purpose

Let an active student save their own or a classmate's approved storybook from their current
classroom through one direct reader action, with a readable document and clear preparation/retry
feedback. No print-dialog workflow, new generated content, narration or PDF storage.

## 2. Contract and position

This is a read/export action after completion and teacher approval, outside the generation graph.
StoryMemory, jobs schema, image budgets and pipeline behavior remain unchanged.

- Reads the viewer's and author's active student/classroom membership, job completion and
  approval/rejection state, checked `title`, and final
  `pages[].image_path` / `pages[].caption` through existing authorized boundaries.
- Writes no application state, database rows, or Storage objects.
- Authenticated `GET /jobs/{job_id}/pdf` returns
  `application/pdf` with an attachment filename sanitized from the checked title.
- Follow existing authentication conventions. Return `404` for missing or inaccessible jobs,
  `409` for the owner's incomplete/unapproved/rejected job, `404` for an unavailable peer book,
  and a retryable service error if
  fetching any illustration or rendering fails. Never return a partial document.
- Use the existing Storage/provider seam for private assets. Never accept arbitrary image URLs,
  HTML, CSS, local file paths, or renderer options from the requester.

## 3. Reader UX and document layout

The approved classroom book's reader offers **Download PDF** as a quiet outlined action at the right of
the reader header, with Bookshelf on the left. At desktop widths (1024px and above), the title
uses the flexible space between them. Below that breakpoint, the title occupies a full-width
row beneath the actions. Pages / Scroll stays together on a centered row directly above the book.
Approval guidance and download errors appear beneath the action row, aligned toward the download
control. Use current tokens, a 44px minimum target, keyboard activation and visible focus.

An owner's completed book awaiting approval shows a disabled download action with the explanation
**Ask your teacher about downloading this book** (teacher-review-and-approval §14, AC-17). Do not expose moderation
categories or technical errors. Approved classmates' books offer the same download action.

The teacher review dialog explains before approval: **Classmates will be able to read and download
this book.** Saved copies remain after approval is withdrawn or the book is deleted. The privacy
and terms pages explain the same classroom-scoped sharing policy.

On activation, announce **Preparing PDF…** and disable repeat activation while retaining the
current reader mode/page. Failure announces **We couldn't download your book. Try again.** and
re-enables the action. Preserve the book and its navigation. On a 404 or 409, refetch the job through
the existing reader hook: approval withdrawal can hide a peer row from Realtime before its update
arrives. An inaccessible book uses the existing unavailable view; an owner's unapproved book shows
the disabled action and approval guidance. If the refresh fails, preserve the reader and retry feedback.
Do not infer successful saving from starting a browser download. Navigating away aborts the
request and prevents a stale download. Revoke transient browser object URLs after use.

Use WeasyPrint and a fixed, application-owned template, never HTML assembled from unescaped text.
Each scene starts on an A4 portrait page with an uncropped illustration, its complete existing
caption and a page number. Place the checked title on the first page without adding a generated
cover. Keep long captions readable, allowing continuation pages instead of clipping or shrinking
text. Include font glyphs needed by the supported story text, including Filipino and punctuation.
Do not embed original story text, account identity, asset URLs, internal metadata or failed images.

Fetch all required finalized images before returning a document. Apply existing configured page
bounds and bounded fetch/render resource use. Keep bytes transient and return `Cache-Control:
private, no-store`. Approval and viewer/author classroom membership are rechecked by the server
before returning each download. A file already
saved to a device cannot be revoked by later unapproval or deletion.

## 4. Cross-cutting requirements

- CC-1/2: only finalized moderated images, checked title and post-redaction captions.
- CC-3: no paid model calls, regeneration, or pipeline retries.
- CC-4: server-side active classroom membership/approval checks and private asset fetches. No public bucket or stored PDF.
- CC-5: log failure classes without text, signed URLs, or document contents.
- CC-6/8/9: familiar child-facing action, accessible state feedback, readable pages and retry.
- CC-7/10: no seed, checkpoint, resume or Objective 4 change.

## 5. Verification before release

Use existing test infrastructure, failing first. Backend coverage: one approved owner/peer main path
with complete ordered images/captions, and parameterized denial/failure cases including revoked
approval, changed classroom membership and a failed image fetch. Reader coverage: one owner/peer prepare/download main path and one failed
request/retry path, retaining reader state. Assert no generation or persistence side effects.

Render a PDF from sanitized existing fixtures and inspect every page. Check full captions,
uncropped images, fonts and page numbers. Verify direct download/open and failure/retry on mobile,
320px layout, 200% zoom and keyboard operation. Run frontend lint/build/tests and backend
lint/tests, then verify required runtime libraries in the deployment image before release.

The renderer lives in `backend/app/pdf_export.py` and the bounded private image read in
`backend/providers.py`. The reader uses its existing session and `useJob` approval fields.
`useJob` keeps completed-book subscriptions open for approval changes until unmount.
The existing page ceiling applies. `backend/app/config.py` names the export limits: 15,000 caption
characters per scene, 8 MiB per image, 32 MiB across images, 2048×2048 pixels per image and a
20-second total image-fetch deadline covering URL signing, response headers and body streaming.
Expiry cancels the in-flight network operation and closes the connection before releasing the
render slot. The synchronous provider entry point runs cancellable async Storage/HTTP clients
under one `asyncio.timeout`; it does not abandon a background thread. One PDF render is admitted
per API process; concurrent requests receive a retryable 503 rather than queueing unbounded
rendering work.

Scope/document propagation belongs to ADR-071/072. Deployment and the verification above are required
before claiming that the hosted application offers export.

### Local verification, 2026-10-21

- Frontend: `pnpm lint`, `pnpm build`, `pnpm test` (704 tests in 73 files, including the layout follow-up below).
- Backend: `uv run ruff check .`; `uv run pytest --ignore=tests/test_pdf_export.py -q`
  (1,493 passed, 87 expected environment-gated skips, 6 smoke tests deselected, including the timeout correction below).
  `uv run pytest tests/test_pdf_export.py -q` in the Linux verification image passes all 14,
  using the real renderer. Windows lacks the native Pango libraries, so renderer tests run
  against the Linux deployment runtime. No test is weakened or marked skipped for export.
- Production backend Docker build succeeds with the frozen lockfile and bundled libraries/fonts.
  The endpoint's OpenAPI response is explicitly a binary `application/pdf`, checked alongside
  the real attachment response. The initial contract check exposed FastAPI's default JSON media
  type; the corrected contract and all 14 endpoint tests pass.
- A four-page PDF rendered from existing sanitized synthetic fixtures passes exact normalized
  text/order checks, special-character/title escaping, continuation and page-number checks.
  Poppler renders all four pages for visual inspection: illustrations are uncropped and captions
  remain legible and complete.
- A temporary browser harness using the actual reader JSX and production CSS verifies no
  horizontal overflow at 320, 390, 768 and 1280 CSS pixels, plus the 640-pixel layout representing
  200% zoom on a 1280-pixel desktop. Keyboard order is Bookshelf, Download PDF, Pages, Scroll.
  Reader tests verify preparation, retry and cancellation. This does not substitute for a real
  phone's download/open workflow after deployment.
- An initial full-suite container attempt reported `47 failed, 1456 passed, 87 skipped` because the temporary image lacked Git and
  host fixtures. The normal-checkout suite passes as reported above. Live RLS/provider checks
  and the offline Tool A instrument were not run. Deployment has not been performed.

### Timeout correction verification, 2026-10-21

- Before the correction, `uv run pytest tests/test_providers.py -k "pdf_image_deadline" -q`
  reports two failures and one pass. A local HTTP server trickling headers takes 4.03 seconds
  against a one-second limit, and trickling signing headers completes without a timeout.
- After the correction, `uv run pytest tests/test_providers.py -q` passes all 85 tests.
  The regression uses real HTTP and the installed Storage SDK, an existing captured image,
  and a local Storage stand-in. It verifies ordinary downloads and cancellation during signing,
  response headers and body streaming, including the server observing the connection close.
- `uv run ruff check .` passes. The normal-checkout suite above includes all four new cases.
  In the existing Linux verification image, with current `providers.py`, `app/pdf_export.py`
  and `tests/` mounted read-only and external networking disabled,
  `uv run --no-sync pytest tests/test_providers.py tests/test_pdf_export.py -q -p no:cacheprovider`
  passes all 99 tests, including all 14 real-renderer PDF tests.
- The initial Linux rerun used an older PDF route baked into the image and reported two failures
  (JSON OpenAPI media type and the old renderer). Mounting the current route resolves that stale
  image mismatch. The existing Starlette test-client deprecation warning remains.
  Frontend checks were not repeated for this backend-only correction. Live services, deployment
  and physical-device checks remain outside this verification.

### Reader layout and trace visibility follow-up, 2026-10-21

- Frontend lint, production build/typecheck and all 704 tests pass. The Langfuse regression first
  fails for signed-out visitors, students, teachers and researchers lacking access to the run.
  The reader's current-page accessibility regression also fails before implementation.
- An isolated Vite preview uses the actual reader, student header/tab bar and production CSS
  with public sample illustrations. Playwright checks Pages at 320, 390, 640, 768 and 1280 CSS
  pixels, including a 640px viewport representing 200% desktop zoom. No horizontal overflow;
  PDF and page-dot targets measure at least 44px after existing transitions settle.
- Browser checks cover keyboard order, jumping to a page, Scroll mode, download error feedback,
  pending approval, a 15-page book and the absence of export on peer books under the initial ADR-071 policy, before ADR-072. Mobile and desktop
  screenshots were visually inspected. Initial preview checks needed the signing fixture's
  path-to-URL map, correct CSS serving and settled page transitions; these were harness issues.
- Existing build middleware deprecation and jsdom `scrollTo` notices remain. No live account,
  provider, deployment or physical-device download test was performed in this frontend follow-up.

### Approved classroom downloads follow-up, 2026-10-21 (ADR-072)

- Before implementation, the backend classmate main path returns 404 instead of 200, and the reader
  classmate main path fails because Download PDF is absent. The owner main path continues to pass.
- After implementation, `uv run ruff check .` passes and
  `uv run pytest --ignore=tests/test_pdf_export.py -q` reports 1,493 passed, 87 expected
  environment-gated skips and 6 smoke tests deselected. The current PDF route, provider and tests
  mounted read-only into the existing Linux image with external networking disabled pass all 27
  `tests/test_pdf_export.py` cases using the real renderer. Coverage includes active owner/peer access,
  foreign classrooms, inactive accounts, pending/rejected books, and withdrawn approval/membership.
- Frontend `pnpm lint`, `pnpm build` and `pnpm test` pass: 706 tests in 73 files. The focused
  reader/teacher-books selection passes 55 tests. Existing middleware and Starlette deprecation
  notices remain. Teacher approval copy and privacy/terms now explain classroom downloads and the
  permanence of saved copies.
- The isolated sample preview passes the same 320–1280px layout, 44px targets, keyboard order,
  reader-mode, error and pending checks, now requiring the approved classmate PDF control.
  It has no signed-in session: clicking PDF reproduces the friendly error with zero backend API
  requests. A visible sample-preview label explains that real downloads require the signed-in app.
- The actual localhost:3000 dev bundle points to localhost:8000. A local check finds no API listening
  there. Direct fixture rendering in Windows fails to load `libgobject-2.0-0`; the Python package is
  installed but its native runtime is missing. Linux-only verification does not establish local
  Windows export readiness. Run the backend in its Linux image, or install/configure the supported
  Windows native libraries before claiming that local PDF download works.
- No live account, live RLS/provider, deployment, physical-device or offline Tool A check was run.
  These local checks do not establish that the hosted application offers export.

### Denied-download reader refresh, 2026-10-21

- A regression using the real reader hook with network boundaries mocked reproduces stale access
  after a PDF denial without a Realtime event. Before the fix, the peer and owner cases fail because
  the old book/action remains available. The transient refresh-failure case already passes.
- The reader now refetches on 404/409, uses the existing unavailable/approval states, and retains
  retry feedback if the read fails. `pnpm exec vitest run book useJob` passes 77 tests, followed by
  successful `pnpm lint`, `pnpm build`, and `pnpm test` (709 tests in 73 files).
- Live authenticated/RLS behavior and physical-device checks were not rerun. No backend change.
