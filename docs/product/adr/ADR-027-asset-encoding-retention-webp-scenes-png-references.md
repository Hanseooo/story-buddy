# ADR-027 — Asset encoding & retention: WebP scenes, PNG references, PDFs on demand

**Status:** Accepted (2026-07-28) · **confirms ADR-006** (Supabase for Postgres/Auth/Storage/Realtime) after an
explicit vendor-lock review · bounded by ADR-004 (≤2 canonical refs) and ADR-020 (narration audio)

**Context:** A vendor-lock review asked whether Supabase Storage should be replaced by Cloudflare R2 or S3, and
Supabase Auth by Clerk. The review's trigger was the Supabase free tier's **1 GB storage / 5 GB monthly egress**
ceiling. Reading the code showed the ceiling is not a vendor limit being hit — it is an encoding default never
chosen. `backend/pipeline/generate_scene.py:13-17` uploads the raw PNG bytes fal returns, unmodified.

A 1024×1024 fal image is ~1.2–2 MB as PNG and ~120–200 KB as quality-82 WebP; flat illustrated art compresses
better than photographs, so 8–10× is a conservative floor. Against the realistic pilot (N≈8–15, ADR-017; ~900
images) PNG consumes **~1.35 GB** and breaches the free tier mid-study, while WebP consumes ~160 MB. Against the
stated cost model (200 books/month, ADR-015) PNG accumulates ~3.6 GB/month and would exhaust even the 100 GB Pro
tier in roughly two years.

**Egress decides this, not storage.** 5 GB/month is ~3,300 PNG views versus ~28,000 WebP views. More importantly
a 12-page book at PNG is an ~18 MB page load delivered to Grade 5–6 students on Philippine school connections —
a UX failure before it is a billing one. R2's zero-egress pricing would have *concealed* this rather than fixed
it, which is the strongest argument against treating the problem as a vendor choice.

**Decision:**

1. **Scenes are stored as WebP (quality ≈82).** Preferred mechanism: request the encoding from fal via an
   `output_format` key in the args dict `providers._run_fal` already forwards (`providers.py:88-95`) — zero new
   dependency, zero OpenRouter. **Unverified whether fal exposes this**; if it does not, encode on the worker
   with **Pillow** (new backend dependency, accepted here rather than deferred to a build session).
2. **Canonical character references stay PNG.** They are the conditioning input every scene depends on
   (ADR-007), ADR-004 caps them at 2 per book, and `providers.upload_reference` already sends PNG to fal. Saving
   ~3 MB per book is not worth introducing recompression artifacts into the identity mechanism.
3. **PDF exports are generated on demand, never stored.** A 12-page illustrated PDF exceeds the combined size of
   its source images. If generation latency proves unacceptable, cache with a TTL and regenerate on miss.
4. **Storage, Auth, Postgres and Realtime remain Supabase.** ADR-006 stands unamended.
5. **Phase 0.5 records actual encoded byte sizes** for scenes and references. The probes generate exactly this
   data; the ratios above are estimates until they run.

**Consequences:**
- The free tier becomes sufficient for the pilot, and the Pro tier becomes sufficient for the life of the
  artifact. Storage stops being a de-scope risk.
- Book page weight drops ~8–10×, which is a delivery improvement for the study population independent of cost.
- `generate_scene.py`'s path template (`{job_id}/scene-1.png`) and its test assertion in
  `tests/test_generate_scene_node.py:28` both change extension. Any Phase-1 work touching that node inherits
  this.
- Possibly one new backend dependency (Pillow), contingent on the fal `output_format` check.
- **Consequences to build** (not this session): the encoding change and its test; the fal `output_format`
  verification; the on-demand PDF path in the Phase-2 export node.

**Alternatives:**
- **Cloudflare R2 for images** (10 GB free, zero egress) — rejected. Compression removes the need, and R2 costs
  a capability the current design depends on: `frontend/app/book/[jobId]/page.tsx:29-31` mints signed URLs
  **client-side** under the anon key, with RLS as the authorizer. S3 presigning requires a secret key that
  cannot ship to a browser, so R2 forces a new FastAPI minting endpoint and moves asset authorization from a
  database policy into application code — a downgrade on a child-safety path (CC-4). Revisit only if measured
  volume defeats compression.
- **Supabase Pro at $25/month with no compression** — rejected. It adds ~30% to the $60–110/month budget
  (ADR-015) to avoid a change that is smaller than this ADR, and leaves the page-weight problem untouched.
- **Clerk for auth** — rejected, and it is a worse fit than the incumbent rather than a neutral swap. ADR-017
  mandates nickname + teacher-set passwords with no email, no self-serve signup and no recovery, which is
  precisely the product surface Clerk exists to provide. It would also split the JWT issuer from the Postgres
  instance enforcing RLS, making authorization correctness depend on template configuration in a second
  vendor's dashboard, and it stores user records outside the project's own database — strictly *more* lock-in
  than Supabase Auth, whose GoTrue is Apache-2.0 and self-hostable.
- **AWS for the whole stack (S3 + Cognito)** — rejected on ops surface for a solo build on a ~1 month timeline;
  consistent with `docs/capstone/hardware_and_hosting.md` §5b's existing rejection of Bedrock.
- **Lossless WebP for scenes** — rejected: roughly 2–3× the size of quality-82 for a difference invisible in
  rendered storybook art.
