"""Producer half of the consistency-judge fine-tune (spec `docs/specs/judge-finetune.md` §5.3).

Offline research tooling, not a pipeline package: nothing under `backend/pipeline/` imports it and
it never runs in a job. `manifest.py` owns the record and its guards, `build_dataset.py` turns
pipeline output plus the `annotations` table into `manifest.jsonl`, `to_llamafactory.py` renders
that into a LLaMA-Factory build artifact, `evaluate.py` scores §7.3's four baselines.

The manifest is the source of truth; everything downstream of it is regenerable.
"""
