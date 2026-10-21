# ADR-072 — Approved classroom books can be downloaded by classmates

**Status:** Accepted (2026-10-21). The owner explicitly approved classroom-peer downloads after
reviewing their permanence and the teacher-facing sharing explanation.
Amends ADR-071 decisions 1 and 3; its renderer, transient storage, safety and approval gates remain.

## Context

ADR-071 initially restricted export to the author. The owner now wants the approved classroom
library to support downloading classmates' books as well as one's own. Downloading produces a
durable copy that cannot be revoked with later unapproval or deletion.

## Decision

1. An active student can download a completed, nonempty, approved and unrejected book in their
   current classroom, whether it is their own book or a classmate's. The author must also be an
   active student in that classroom. Other classrooms, removed accounts, teachers, researchers
   and signed-out users gain no PDF access.
2. Recheck the viewer's membership, the author's membership and approval before returning the
   PDF. A same-class peer's pending/rejected/incomplete book returns 404. An owner's unavailable
   book retains the existing 409 response. Missing/inaccessible books return 404.
3. Reuse the existing teacher approval state. Before approval, explain: **Classmates will be able
   to read and download this book.** Explain that saved copies survive approval withdrawal or
   deletion. Approval continues to be the classroom-sharing gate, not a revocation mechanism.
4. Export only the existing checked title, final moderated illustrations, redacted captions and
   page numbers. Add no author/account identifiers, raw input, public links or stored PDFs.
5. The reader offers the same Download PDF action for authorized own and peer books. It sits in the
   header beside Bookshelf, with the title on its own row below those actions on mobile. Pending own
   books retain the disabled action and approval explanation. Existing auth, RLS, Storage policies,
   schema, API path and response shape remain unchanged.

## Consequences and verification

The authenticated PDF endpoint's authorization is widened to match this policy. Update the reader,
teacher explanation, policy pages and current scope documentation together. Add positive owner/peer
coverage and denial coverage for foreign classrooms, inactive membership, approval withdrawal and
membership withdrawal during rendering. No historical result or Objective 4 decision changes.
Deployment and consent/adviser requirements remain recorded in the export spec and capstone docs.
