# ADR-085 — Teacher-review pictures may be browser-cached for an hour

**Status:** Accepted (2026-11-25) · the owner decided it after the picture-speed audit in PR #142 ·
supersedes in part ADR-080 Decision 7 (the `no-store` rule for picture reads only) · ADR-080's
authorization, re-check and no-signed-link rules are unchanged · revisit before real children use
the app

## Context

ADR-080 Decision 7 sends every teacher-review picture from the backend with
`Cache-Control: private, no-store`. Each read re-runs authorization twice and downloads from Storage.
Production timings on the Northflank Free plan (PR #142, 2026-11-25): about 6–7 s per picture,
4 at a time, so "The Star in the Rice Field" (9 pictures) takes about 21 s on every visit. Older
books use signed Storage links that the browser keeps for about an hour and load in 0.4–0.7 s on a
revisit. The Needs-help list re-downloads every picture when its tab regains focus.

No child uses StoryBuddy. It is only demoed (owner, 2026-11-25). The owner asked for teacher-review
pictures to behave like older books' pictures.

## Decision

1. **A picture GET whose URL names fixed bytes is sent with
   `Cache-Control: private, max-age=3600` and `Vary: Authorization`.** This covers:
   - `GET /jobs/{id}/images/{asset}?v=<path>` when `v` equals the authorized Storage path.
     A different `v` gets `409 image_changed` with `no-store`, and no `v` gets `no-store`, so a
     stale or unnamed URL is never cached. Each attempt, draw and pencil result has its own path.
   - `GET /teacher/jobs/{id}/moderation-review/images/{asset}`, whose URL already carries
     `review_id` and `subject_version`.
2. **Everything else stays `no-store`:** JSON, errors, PDFs, and the held picture
   (`POST .../moderation-review/reveal`).
3. **The browser fetches those two picture routes with the default cache mode** instead of forcing
   `no-store` (`frontend/lib/signedUrls.ts`, `frontend/components/NeedsHelpQueue.tsx`).
4. **Unchanged:** every request that reaches the server is authorized before and after the
   Storage read. Children never receive signed Storage links.

## Consequences

- A revisit within the hour is instant: bookshelf, gallery, reader, the Books page and the
  Needs-help list on refocus. **A first view is not faster.** It still costs ~7 s per picture.
- **Withdrawal is delayed.** After a teacher withdraws approval or stops a book, a browser that
  already loaded its pictures keeps showing them for up to an hour. ADR-080 already accepted that
  viewed bytes cannot be recalled. This extends "viewed" to "cached for an hour".
- **The copy outlives logout** in that browser's cache. `Vary: Authorization` keeps another login
  from reusing it while browsers honor `Vary`. The access token refreshes about hourly, which also
  ends reuse.
- Teacher context pictures, which may sit next to flagged content, can stay on a teacher's device for
  an hour. The flagged picture itself is never cached.

## Release gate

Before real children use the app, revisit this decision together with ADR-080's ethics re-review:
check whether children share devices, and whether a one-hour withdrawal delay is acceptable. Going
back is two constants (`CACHED_PICTURE` in `backend/app/moderation_hold.py` and the fetch cache
modes), with no migration.

## Alternatives

- **Memory-only cache in the app.** Almost no new privacy cost, but does not survive a reload or a
  new tab. The owner chose the same behavior as older books instead.
- **Speed up the first view** (load book state once, OD-02; a bigger Northflank plan). Still open;
  complementary, not replaced.
- **Signed Storage links for teacher-review pictures.** Rejected again: ADR-080's reason holds
  (bearer links and prefix-wide signing would expose flagged attempts).
