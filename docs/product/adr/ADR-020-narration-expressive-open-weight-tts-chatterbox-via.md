# ADR-020 — Narration: expressive open-weight TTS (Chatterbox) via hosted inference; Kokoro-82M as CPU fallback

**Status:** Accepted (2026-07-10) · **revised 2026-07-17** — expressive narration supersedes the Kokoro-only
decision. Kokoro is retained as the fallback, not deleted, so nothing about the mandate or the fallback path
is lost. · **amends ADR-002's read-aloud consequence, ADR-009's worker-RAM budget, and PRD §15/§17**

**Context:** The product needs read-aloud narration (CC-6, PRD §17). The original 2026-07-10 decision chose
**Kokoro-82M** because it runs real-time on the OpenRouter at zero cost. That decision was correct on
compliance and cost, but it **weighed ElevenLabs only on its word-timestamp feature** (correctly: Grade 5–6
readers do not need word-highlighting) and on its proprietary licence — it **never weighed expressive prosody
as a value at all.** Kokoro is flat and neutral by design; that flatness is the price of running on a CPU.

Expressive narration — emotional range, natural prosody, breathing — is what makes read-aloud feel like a
person telling a story rather than a screen reader, which is a real engagement value in a child-facing
product. It is **not a research variable** (no RQ measures narration; see ADR-008), so this is a product-quality
decision, not a claims decision, and it must not be allowed to tempt any new research claim.

The 2025–2026 open-TTS landscape has a hard structural fact: **no open model delivers ElevenLabs-grade
expressivity while running real-time on CPU.** Every genuinely expressive open model (Chatterbox, Orpheus,
Higgs, Dia) is a 0.5B–4B LM that needs a GPU. But "needs a GPU" is not "needs a proprietary vendor":
**ADR-015 explicitly permits hosted inference of open weights** — the same mechanism that makes fal.ai
(images) and OpenRouter (text/VLM) compliant. So an expressive *open* model served as an HTTP call satisfies
the mandate with no exception to argue.

**Decision:** Narrate with **Chatterbox (Resemble AI, MIT)** served via **hosted inference on fal.ai**
(Replicate is a drop-in alternate). The worker calls it over HTTP per page — the **same shape as the image
call** (ADR-001) — with the emotion-intensity dial tuned once to a warm storyteller register and frozen in
config; it writes one MP3 per page to Supabase Storage behind a signed URL, and the frontend is an `<audio>`
tag. **Kokoro-82M (Apache-2.0, CPU, on-worker) is retained as the named zero-cost fallback** for host
outage or if metered cost/latency disappoints; it costs nothing to keep because it is already the worker's
shape. Narration is isolated behind `providers.narrate()` — swapping the model is an env var, the provider one
line (ADR-015).

**Consequences:**
- **Mandate holds, no exception.** Chatterbox is MIT (cleaner than Gemma's community licence) and served as
  hosted inference of open weights — identical in kind to fal.ai images and OpenRouter text. No proprietary
  dependency enters the stack. ElevenLabs is still rejected on ADR-015 grounds.
- ⚠️ **One honest new data flow.** Kokoro ran on the worker, so narration text never left our infrastructure.
  Chatterbox means the child's **already-PII-redacted verbatim text** (ADR-011, ADR-013) now travels to the
  TTS host. This is the **same trust-boundary class** as the image prompts already sent to fal.ai and the
  story text already sent to OpenRouter, so it **does not change the deliberately modest privacy posture**
  (ADR-015: *no privacy guarantee is claimed*). It is recorded here so it is not discovered later, and it is
  **not** a reason to claim, or to weaken, any privacy property.
- **Narration is no longer $0.** ~cents/book of metered TTS (fal.ai Chatterbox, per page), small beside image
  generation ($0.30–0.65/book, ADR-001). Update PRD §15's "Narration is $0" line.
- **Worker RAM eases.** Kokoro is now the fallback, not a resident requirement, so ADR-009's ~2–3 GB worker
  budget relaxes unless the fallback is kept warm.
- Narration is **pre-rendered during the 1–3 min generation**, off the child's critical path, so the added
  per-page HTTP latency is invisible in the reading UX.
- Narration still reads the child's **verbatim redacted text** (ADR-013) — **no new moderation surface**.
- ⚠️ **English-only is unchanged.** No open expressive TTS ships Tagalog/Filipino/Taglish support (Chatterbox
  Multilingual's 23 languages do not include it). Taglish is still read with English phonology. Recorded as a
  limitation; not solved. This is not a regression from Kokoro — both are English-only.
- **Word-level highlighting stays dropped** — Grade 5–6 students read; it is an emergent-reader aid and not a
  research need.

**Alternatives:**
- **Kokoro-82M as primary** (the previous decision) — zero cost, CPU, fully in-infrastructure, but flat and
  neutral. Rejected as the *primary* now that expressive narration is a product goal; **retained as the
  fallback**, so its virtues are not lost.
- **Orpheus 3B (Canopy Labs, Apache-2.0)** — explicit `<laugh>/<sigh>/<gasp>/<breath>` non-verbal tags, the
  most literal match to "natural breathing." The designated alternate if tagged non-verbals become wanted;
  slightly heavier to host (Baseten/Replicate/Together). Chatterbox is preferred first for MIT + the one-line
  fal.ai path + a continuous emotion dial that needs no markup.
- **Higgs Audio v2 (Boson AI, Apache-2.0)** — highest raw expressivity, but 3B/~24 GB and the most expensive
  to serve. Overkill for per-page storybook narration.
- **Self-host Chatterbox on the ADR-019 Modal GPU** — possible, but ADR-019's container is *first on the
  de-scope ladder* and **nothing may hard-depend on it** (ADR-011, ADR-019). Narration therefore uses hosted
  inference, not that container.
- **ElevenLabs** — rejected: proprietary (ADR-015 hardened). Its timestamp advantage buys a feature this age
  band does not need.
- **XTTS-v2 / F5-TTS / Fish-S1** — expressive but non-commercial licences (Coqui CPML / CC-BY-NC); would each
  need an ADR-015 exception Chatterbox does not. Rejected on licence.
- **Web Speech API `SpeechSynthesis`** — the pre-Kokoro decision. Free and zero-dependency, but OS voice
  quality on Android/Windows is poor and `onboundary` support is inconsistent.
