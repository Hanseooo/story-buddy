# ADR-065 — The research docs hub and dataset page are static, and show synthetic material only

**Status:** Accepted (2026-10-10) · settles the open questions in
issues #105 and #106 · adds two public frontend routes · no backend route, no migration, no
`StoryMemory` or `contracts/` change · no Supabase read

**Context:**

Issue #105 asks for a page that links the research documents so group members and panelists do not
browse the repository. Issue #106 asks for a page that shows what the judge was trained and tested
on and how "same character" was decided. Epic #102 requires an ADR before a new route is built, and
allows synthetic (`syn-*`) material only in anything shown.

What the code and data say, checked on 2026-10-10:

- **`/research` is public and its sub-paths are not guarded.** `frontend/middleware.ts` matches
  `/research/metrics` and below only. A new `/research/docs` or `/research/dataset` never enters
  the middleware, so it makes no Supabase call unless the page itself makes one.
- **GitHub does not draw `.drawio` files.** The three files in `docs/diagrams/drawio/` are served
  as `text/plain`. Inferred, not checked in a browser: the repository page shows their XML.
- **The whole held-out test set is donated.** `data/judge/freezes/obj4-v1/manifest.jsonl` has 899
  pairs. Train (484) and validation (86) are all synthetic; test (329) is all donated. This is the
  registered design (`PREREGISTRATION_OBJ4.md` §2).
- **The freeze is local.** `data/judge/` is git-ignored. Its `assets/` folder is 91 MB and holds
  synthetic and donated images side by side.
- **Some totals have no tracked source.** Split sizes, the 47 Different test pairs, the 795
  labelled pairs and the agreement figures are in `research_runbook.md` and `group-guide.md`. The
  class totals (691 Same, 208 Different), the pair types (795 pipeline, 104 constructed) and the
  drift-reason counts exist only in the git-ignored `freeze_report.json`.
- **The rulebook's opening describes one rater.** The 2026-09-23 amendment replaced that with two
  raters and owner adjudication. The rulebook is frozen and is not edited.
- **`research/error.tsx` is written for the metrics page.** It says the metrics could not load and
  offers Log out. A new page under `/research` inherits it.
- **The owner plans to leave Supabase Pro** (#102), so nothing here may depend on Supabase Storage.

**Decision:**

1. **Two public, static routes.** `/research/docs` and `/research/dataset` are server components
   that fetch nothing and read no session. `frontend/middleware.ts` is not changed. Each ships its
   own `error.tsx`, links back to `/research`, and is linked from `/research`.

2. **The hub links to GitHub; it does not render markdown.** Each entry opens
   `https://github.com/Hanseooo/story-buddy/blob/main/<path>` in a new tab. The entries live in one
   array of path, title and the question the file answers. A unit test asserts every listed path
   exists in the repository, so a renamed or deleted document fails the check.

3. **Diagrams are re-saved as `.drawio.svg`.** One file that GitHub draws and draw.io still edits.
   The `.drawio` originals are removed and the documents that cite them are updated.

4. **Every number on the dataset page comes from a tracked file and names it.** The totals that
   today exist only in `freeze_report.json` are first added to the "Dataset handoff" section of
   `research_runbook.md`, as counts over the whole freeze or a whole split.

5. **Donated material appears only as whole-split counts.** The page may say the test set is 329
   pairs from 12 donated stories, 47 of them Different. It shows no donated story id, title, text,
   image, pair id, or any count broken down by story or character. A unit test fails if the page's
   data or an image filename contains `don-`.

6. **Six example pairs are committed, and the page says they were hand-picked.** They are
   synthetic pairs from the train and validation splits of the registered freeze, chosen by the
   owner from a local contact sheet before anything is committed. Each is resized to WebP under
   `frontend/public/research/dataset/` and shown with its adjudicated label, its drift reasons and
   its pair id. The page states that they illustrate the rules and are not a sample, and that no
   test pair is shown.

7. **The labelling section states the procedure that was run.** Two raters, owner adjudication,
   citing the rulebook for the rules and the 2026-09-23 amendment for the procedure.

**Consequences:**

- Both pages work with Supabase down, paused or downgraded, and with the backend down.
- No held-out pair is published, so the test-access policy (`PREREGISTRATION_OBJ4.md` §7) is
  untouched.
- The example images are in a public repository's history for good. Removing one later does not
  unpublish it.
- The examples describe the `obj4-v1` freeze. A new freeze means checking that each pair id still
  exists with the same label.
- The hub depends on the repository staying public and on `main`. A private repository breaks every
  link at once.
- The hub puts `PREREGISTRATION_OBJ4.md` and `research_runbook.md`, which carry donated story IDs,
  one click from the public site. That follows the 2026-10-10 decision in
  `research-changelog.md` (#108) and is recorded here, not changed.
- A diagram is now edited as `.drawio.svg`. Opening it in a plain SVG editor and saving can strip
  the embedded diagram.

**Alternatives considered:**

- **Render the markdown inside the app.** Rejected for now: it needs the Vercel build to see
  `docs/`, which was not checked, and a markdown renderer. GitHub already renders every file and is
  always current.
- **Serve example images from Supabase Storage.** Rejected: the planned plan downgrade, and a paused
  project on defense day.
- **Commit the full synthetic corpus.** Rejected: size, and synthetic and donated images share the
  same folders.
- **A local HTML report of every synthetic pair (#106 option 2).** Not built. It is not on the
  public site and the six examples answer the panel's question. It can be added without changing
  this decision.
- **Link the diagrams through the diagrams.net viewer.** Rejected: an outside service on defense
  day, and the viewer URL was not checked.
- **Keep `.drawio` and commit a separate exported image.** Rejected: two copies of one diagram, and
  the export goes stale.
