# 10 — Privacy and consent copy: deletion scope and retention limits

**Source spec:** `docs/specs/storybook-deletion.md` §2 non-goals, §6, §14.7
**Implementation plan:** not required — implement directly.
**Blocked by:** None — can start immediately.
**Status:** ready-for-agent

## What to build

Privacy and consent material that describes deletion honestly: it removes the book from
StoryBuddy-controlled **active** stores, and it does not promise instantaneous erasure everywhere.

The copy must state:

- What is removed: the job row, the book's Storage objects, its LangGraph checkpoints, and its
  Langfuse trace.
- What is not: separately consented research pairs, annotations and research assets.
- What lingers: already-issued signed URLs remain valid for the current one-hour TTL; already-cached
  bytes follow client/CDN cache behavior; Supabase backups, processor logs and upstream model
  providers keep data under their own retention.
- That an approved book also disappears from the class gallery.

Retention periods confirmed in ticket 09 step 8 should be reflected here if that ticket lands first;
otherwise state the categories and revisit the numbers.

## Acceptance criteria

- [ ] Copy states the active-store scope and names the four stores cleared.
- [ ] Copy discloses backup, CDN/cache, Supabase, Langfuse and model-provider retention.
- [ ] Copy makes no instantaneous-erasure promise anywhere.
- [ ] Copy matches the in-product confirmation dialog wording about the class gallery.
