#!/usr/bin/env bash
# Quantize a merged HF model to GGUF formats for Ollama / llama.cpp deployment.
#
# Usage:
#   bash scripts/quantize_gguf.sh outputs/medai-merged
#
# Produces:
#   outputs/medai-merged/medai-7b-fp16.gguf  (~14 GB, reference)
#   outputs/medai-merged/medai-7b-q4_k_m.gguf (~4 GB, recommended)
#   outputs/medai-merged/medai-7b-q8_0.gguf  (~7 GB, higher quality)

set -euo pipefail

MERGED_DIR="${1:?Usage: quantize_gguf.sh <merged_model_dir>}"
NAME="${2:-medai-7b}"

if [ ! -d "llama.cpp" ]; then
  echo "[setup] Cloning llama.cpp ..."
  git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
  pip install -q -r llama.cpp/requirements.txt
  (cd llama.cpp && cmake -B build -DLLAMA_CURL=OFF && cmake --build build --config Release -j 4)
fi

LLAMA_BUILD="llama.cpp/build/bin"
[ -x "$LLAMA_BUILD/llama-quantize" ] || { echo "Build llama.cpp first"; exit 1; }

FP16="$MERGED_DIR/$NAME-fp16.gguf"

echo "[convert] HF → GGUF fp16"
python llama.cpp/convert_hf_to_gguf.py "$MERGED_DIR" --outtype f16 --outfile "$FP16"

for QUANT in q4_k_m q8_0; do
  OUT="$MERGED_DIR/$NAME-$QUANT.gguf"
  echo "[quantize] $QUANT → $OUT"
  "$LLAMA_BUILD/llama-quantize" "$FP16" "$OUT" "$QUANT"
done

ls -lh "$MERGED_DIR"/*.gguf
echo
echo "=== Done. Recommended Ollama model: $MERGED_DIR/$NAME-q4_k_m.gguf ==="
echo "Next: ollama create medai -f deploy/ollama/Modelfile"
