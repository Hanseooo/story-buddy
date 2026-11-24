# ADR-086 — Teacher-review pictures are served by backend-signed links

**Status:** Accepted (2026-11-25) · the owner chose it after ADR-085 left first views at ~7 s per
picture · supersedes in part ADR-080 Decision 7 ("authenticated, no-store backend image responses"
for book and character pictures, and "do not expose signed Storage bearer links to children") ·
supersedes in part ADR-085 Decision 4 ("children never receive signed Storage links") and its
rejected alternative · ADR-080's ban on browser Storage access to these job prefixes is unchanged ·
revisit before real children use the app

## Context

Teacher-review books (ADR-080) send every picture through `GET /jobs/{id}/images/{asset}`. Each
request authorizes, loads and rebuilds the saved story, downloads the PNG from Storage, and
authorizes again. On the Northflank Free plan that is ~6–7 s per picture, 4 at a time: "The Star
in the Rice Field" (9 pictures) takes ~21 s on a first view. ADR-085 made repeat views instant but
left first views unchanged. Older books get signed Storage links and load in 0.4–0.7 s.

ADR-080 rejected signed links for two reasons:

1. **Prefix-wide permission.** Browser signing needs Storage permission on the book's whole
   folder, so a browser could sign a guessed path such as a flagged attempt.
2. **Bearer grant.** Anyone holding a signed URL can open it without logging in until it expires,
   and a withdrawal cannot recall it.

Reason 1 only applies when the browser signs. When the backend signs the exact authorized paths
with its own key, the browser keeps no Storage permission on these folders. Reason 2 remains and is
the cost this ADR accepts. No child uses StoryBuddy. It is only demoed (owner, 2026-11-25).

## Decision

1. **One backend call per book returns signed links.** A new authenticated JSON route takes a
   bounded list of asset ids for one job (the same ids the picture route accepts: `scene-*`,
   `ref-*`, `version-*`, `page-version-*`, `page-pencil-*`) and returns, for each asset the caller
   may see, its authorized Storage path and a signed URL. Assets the caller may not see are left
   out, the same as a 404 per picture today. The JSON is `private, no-store`.
2. **Authorization is unchanged and runs once per call, not once per picture.** Each asset passes
   exactly the rules of `authorized_asset` (job state, author, clearance, moderation verdicts,
   chosen versions, page pencils). The saved story is loaded once for the whole list. The check
   runs again after signing and before the response. An asset whose path or epoch changed between
   the two checks is left out.
3. **Only exact authorized paths are signed**, with the backend's service key, for 3600 s, the
   same lifetime older books use. Nothing is signed by prefix and no path comes from the caller.
4. **The browser treats these links like older books' links.** `signPaths` calls the route once per
   teacher-review job, caches each link in sessionStorage until shortly before it expires, and hands
   the URL straight to `<img>`. No blob URLs for these pictures.
5. **Unchanged:**
   - Browser Storage access to teacher-review job folders stays denied (ADR-080 Decision 7).
   - The held picture is only readable through the teacher's reveal POST, never a link.
   - Teacher Needs-help context pictures keep the backend route and ADR-085's one-hour cache.
   - `GET /jobs/{id}/images/{asset}` stays for callers that still use it. PDF export downloads on
     the server.

## Consequences

- **A first view is about as fast as an older book's:** one backend call per book (~1–3 s on the
  Free plan, estimated) and then direct Storage downloads (~0.5 s each, measured on older books).
- **A copied link works for anyone, without logging in, for up to an hour.** This covers anyone the
  URL reaches by copy, screenshot of DevTools, or a shared device's history of open tabs. ADR-085
  kept the copy inside one logged-in browser. This ADR does not.
- **Withdrawal is delayed up to an hour,** the same as ADR-085: an issued link keeps working, and
  sessionStorage keeps reusing it until it is near expiry. A student removed from the classroom
  keeps already-issued links for the same time.
- **The flagged picture and other unapproved attempts stay unreachable.** No link is ever signed
  for them, and the browser still cannot sign.
- The backend no longer streams picture bytes for these reads, which removes most of its load on a
  book view.

## Release gate

Before real children use the app, revisit this decision together with ADR-080's ethics re-review
and ADR-085: whether a one-hour bearer link is acceptable for children's pictures, and whether the
lifetime should be shorter. Going back means `signPaths` using the picture route again; the new
route can stay unused. No migration.

## Alternatives

- **Keep ADR-085 only.** No bearer links, but first views stay at ~7 s per picture. Rejected by the
  owner for the demo.
- **Drop the second authorization check on the picture route.** Keeps the link ban; probably about
  half the per-picture work (not measured), still seconds per picture. Rejected: smaller gain.
- **Browser signing of the folder (older books' path).** Rejected again: ADR-080 reason 1, a
  guessed path could reach a flagged attempt.
- **A bigger Northflank plan.** Complementary. It may shorten the backend call but cannot remove the
  per-picture backend work this ADR removes.
