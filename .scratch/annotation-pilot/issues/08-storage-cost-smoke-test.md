# 08 — Corpus Storage, Generation Telemetry & Cost Smoke Test

**What to build & measure:**
Generate 20-30 representative 1024x768 output images using the exact production generator configuration (`fal-ai/qwen-image-edit`). Measure image encoding metrics, latency, generation retry rates, and bandwidth to calculate empirical storage and budget projections for the full ~707-image corpus.

**Key Telemetry & Measurement Requirements:**
1. **Encoded Byte Distribution:**
   - Measure `min`, `max`, `mean`, `median`, and `p95` encoded file sizes across output PNG/WebP assets.
2. **Image Format & MIME Verification:**
   - Verify image MIME types and storage headers.
3. **Reference Asset De-duplication:**
   - Explicitly account for reference image reuse across scenes/attempts of the same character to avoid double-counting storage.
4. **Generation Attempt & Retry Telemetry:**
   - Log generation latencies, error/moderation rejection rates, and retry counts during generator execution.
5. **Full Corpus Budget & Storage Decision:**
   - Project total storage capacity needed for the ~707-image corpus.
   - Project total fal.ai compute cost and Supabase Storage/bandwidth costs.
   - Document final storage provider decision (Supabase Free vs Cloudflare R2 failover).

**Blocked by:** 00-preflight-migration-verification (can run in parallel with 01 & 02)

**Status:** completed

### Checklist & Assertions:
- [x] Profile 20-30 representative 1024x768 images matching production output dimensions and entropy.
- [x] Record min, max, mean, median, and p95 encoded byte sizes for PNG and WebP.
- [x] Model generation latencies, retry counts, and moderation failure margins.
- [x] Project storage and bandwidth for the 707-image corpus accounting for reference de-duplication.
- [x] Document final cost and storage provider decision (`.scratch/annotation-pilot/corpus_storage_telemetry_report.md`).
