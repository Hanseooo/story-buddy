# 01 — Meaningful Visual Pilot Fixtures & Robust Seeding

**What to build:**
Replace the dummy 1x1 blank base64 seeding script with a robust Python generator (`backend/scripts/generate_visual_pilot.py` and updated `backend/scripts/pilot_annotate_seed.py`) using `Pillow` to draw 34 meaningful visual fixtures (17 pairs). These must cover PASS cases with varied pose/expression/lighting, and specific FAIL cases targeting the closed taxonomy (`wrong_colour`, `wrong_clothing`, `wrong_body_feature`, `different_face`, `wrong_species`, `character_absent`).

**Key Architectural Invariants:**
1. **Opaque Storage Paths:** Paths must strictly follow `research/pilot/<uuid>/a.png` and `research/pilot/<uuid>/b.png`. Filenames and paths must never include "ref", "scene", test case tags, or failure labels.
2. **External Ground-Truth Manifest:** Expected answers/labels for the 17 pilot pairs must reside ONLY in a test-side fixture manifest (`EXPECTED_PILOT_LABELS`), completely separated from DB columns, storage paths, and frontend payloads.
3. **Randomized UUID `char_id`s:** Replace sequential IDs (`char_1`) with opaque UUID-like identifiers to prevent pattern recognition.
4. **Atomic / Fail-Loud Seeding:** Raise exceptions immediately on any storage upload error. If DB insert fails, clean up and roll back uploaded objects.
5. **Mark Pilot Data:** Insert with `is_pilot = true` to ensure export isolation.

**Blocked by:** 00-preflight-migration-verification

**Status:** ready-for-agent

### Checklist & Assertions:
- [ ] Create `backend/scripts/generate_visual_pilot.py` using Pillow to generate 34 distinct 512x512 PNG images (17 pairs) representing canonical and scene variations.
- [ ] Ensure opaque path formatting (`research/pilot/<uuid>/a.png`, `b.png`) and UUID `char_id`s.
- [ ] Define test-side `EXPECTED_PILOT_LABELS` manifest in test fixtures without leaking into DB/API.
- [ ] Update `pilot_annotate_seed.py` to upload fixtures to `private_assets` with atomic error handling (raise on failure, clean up orphans).
- [ ] Insert 17 pairs into `research_pairs` with `is_pilot = true` and `status = 'pending'`.
- [ ] Write unit/integration tests verifying image generation, opaque path generation, and seed atomicity.
