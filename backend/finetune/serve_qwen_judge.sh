#!/usr/bin/env bash
# Serve the selectable Qwen judge on a rented Vast GPU (judge-selector spec US-06, AC-26).
#
# Derived from `server.json` inside
# data/judge/evaluations/obj4-v1/heldout-1/serving/selected-serving-v1.zip, the command the held-out
# comparison ran with vLLM 0.26.0 (pinned in that zip's inference-requirements-linux.lock).
# Same base model, revision and flags, with exactly these changes:
#   1. --lora-modules serves only seed2_checkpoint140 (seed0/seed1 dropped).
#   2. --host 0.0.0.0 instead of 127.0.0.1.
#   3. --api-key "$VLLM_API_KEY" added; the server refuses requests without that bearer key.
# No structured-output flag is added: vLLM 0.26.0 supports `response_format` json_schema in the
# OpenAI-compatible server by default, backend `auto`
# (https://docs.vllm.ai/en/v0.26.0/features/structured_outputs.html).
#
# Kept as is, on purpose: --override-generation-config caps answers at 256 new tokens. A longer
# SceneVerdict is cut off and fails to parse. The probe (backend/scripts/qwen_judge_probe.py)
# reports that as NOT PARSED (LengthFinishReasonError).
#
# Run on the instance, after the adapter is uploaded to the path below:
#   export VLLM_API_KEY=<a long random string, the same value as QWEN_JUDGE_API_KEY on Northflank>
#   bash serve_qwen_judge.sh
set -euo pipefail

: "${VLLM_API_KEY:?set VLLM_API_KEY before starting the server}"

exec vllm serve Qwen/Qwen3.5-9B \
  --revision c202236235762e1c871ad0ccb60c8ee5ba337b9a \
  --tokenizer-revision c202236235762e1c871ad0ccb60c8ee5ba337b9a \
  --host 0.0.0.0 \
  --port 18081 \
  --dtype bfloat16 \
  --max-model-len 2048 \
  --max-num-seqs 1 \
  --gpu-memory-utilization 0.80 \
  --default-chat-template-kwargs '{"enable_thinking":false}' \
  --limit-mm-per-prompt '{"image":2,"video":0}' \
  --mm-processor-kwargs '{"size":{"shortest_edge":65536,"longest_edge":262144}}' \
  --generation-config vllm \
  --override-generation-config '{"max_new_tokens":256}' \
  --enable-lora \
  --max-lora-rank 16 \
  --max-cpu-loras 3 \
  --api-key "$VLLM_API_KEY" \
  --lora-modules \
  seed2_checkpoint140=/workspace/storybuddy/data/judge/heldout-serving/seed-2/checkpoint-140
