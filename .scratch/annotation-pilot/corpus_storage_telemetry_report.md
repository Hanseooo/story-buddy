# Corpus Storage, Generation Telemetry & Cost Smoke Test Report

**Ticket:** #52 (Issue 08)  
**Objective:** Fine-Tuning the VLM Consistency Judge (Objective 4) Corpus Pre-Flight  
**Status:** Completed (Zero-Cost Verification)

---

## 1. Encoded Byte Distribution (Sample Size: 25 images @ 1024x768)

| Metric | PNG (Lossless) | WebP (Quality=85) | Compression Ratio (WebP vs PNG) |
| :--- | :--- | :--- | :--- |
| **Min** | 1.235 MB (1,294,775 B) | 248.3 KB (254,302 B) | 19.6% |
| **Max** | 1.375 MB (1,441,913 B) | 256.8 KB (262,932 B) | 18.2% |
| **Mean** | 1.321 MB (1,385,043 B) | 252.8 KB (258,918 B) | 18.7% |
| **Median** | 1.316 MB (1,380,182 B) | 252.8 KB (258,824 B) | 18.8% |
| **p95** | 1.372 MB (1,438,211 B) | 255.3 KB (261,416 B) | 18.2% |

**MIME Verification:**
- PNG Magic Bytes (`\\x89PNG\\r\\n\\x1a\\n`): `image/png` (Valid)
- WebP Magic Bytes (`RIFF....WEBP`): `image/webp` (Valid)

---

## 2. Reference Asset De-duplication

In the StoryBuddy pipeline (`char_bible` -> `generate_scene`), canonical character reference images are reused across all scenes of the same story:

* **Estimated Story Count:** 88 stories
* **Canonical Reference Images (1 per story):** 88 assets
* **Output Scene Images:** 619 assets
* **Total Unique Storage Assets:** **707 images**
* **Naive Assets Without Deduplication:** 1326 images
* **Deduplication Storage Savings:** **46.7%** (619 duplicate reference uploads avoided)

---

## 3. Storage & Bandwidth Projections (Full 707-Image Corpus)

| Format | Corpus Total Storage | Annotation Campaign Egress Bandwidth (3 viewers) |
| :--- | :--- | :--- |
| **PNG (Production Source)** | **933.9 MB** (0.91 GB) | **2.74 GB** |
| **WebP (Optimized Delivery)** | **174.6 MB** (0.170 GB) | **0.51 GB** |

*Note: Egress bandwidth is calculated across 2 independent annotators (Annotator A, Annotator B) + 1 adjudicator downloading signed URLs from the private bucket.*

---

## 4. Compute Cost Projections (`fal.ai/qwen-image-edit-2511`)

* **Base fal.ai Unit Cost:** $0.035 / image
* **Base Generation Budget (707 images):** **$24.75 USD**
* **Budget with 10% Retry/Moderation Margin:** **$27.22 USD**

---

## 5. Storage Provider Decision Matrix

| Provider | Free Storage Tier | Free Egress Tier | Status for 707 Corpus | Decision / Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Supabase Storage (PNG)** | 1.0 GB | 2.0 GB / month | ⚠️ Exceeds (0.91 GB / 2.74 GB egress) | Risk of storage/egress limit overages if stored as raw PNG. |
| **Supabase Storage (WebP)** | 1.0 GB | 2.0 GB / month | ✅ Within Limits (174.6 MB / 0.51 GB egress) | Viable if converting generated PNGs to WebP prior to persistent storage. |
| **Cloudflare R2 (S3 API)** | 10.0 GB | **$0.00 Unlimited** | ✅ **Recommended** | Holds uncompressed PNGs with 0 egress cost risk. |

**Final Recommendation:**
Use **Cloudflare R2** as primary/failover storage for large research datasets, or store assets as **WebP (q=85)** in Supabase Storage `private_assets` bucket to stay safely within Supabase Free tier quotas.
