# ADR-032 — Moderation Models: API calls instead of local models due to RAM constraints

**Status:** Accepted

**Context:** The Northflank worker container has a 512MB memory limit. The primary text classifier (`Qwen3-Guard-Gen-0.6B`) requires ~2.4GB of RAM in `float32`, and the NSFW image classifier (`Falconsai/nsfw_image_detection`) requires ~344MB. Loading these locally via HuggingFace `transformers` causes the worker to hit a massive Out-Of-Memory limit, swapping heavily and pegging the CPU, which triggers a 180s job timeout and worker kill. Increasing the container limit to 4GB+ is unnecessary overhead if the models can be accessed via APIs.

**Decision:** Swap the local `Qwen3-Guard-Gen-0.6B` and `Falconsai` models for API calls (via OpenRouter or another suitable provider). Remove the local `transformers` loading step from `backend/providers.py` to keep the worker footprint lean. The exact OpenRouter models chosen for these roles will be determined in implementation.

**Consequences:**
- The worker stays within the 512MB RAM budget, preventing OOM kills and hanging jobs.
- API latency is introduced for moderation, but avoids local loading and swapping overhead (which was infinite).
- Keeps the architecture serverless-friendly and cheaper to host.

**Alternatives:**
- **Increase Northflank worker RAM to 4GB+** — rejected due to unnecessary ongoing hosting costs when APIs provide the same function for fractions of a cent per call.
- **Quantize local models (int8/fp16)** — rejected; even quantized, the 0.6B guard pushes or exceeds the 512MB bound alongside LangGraph and Presidio.
