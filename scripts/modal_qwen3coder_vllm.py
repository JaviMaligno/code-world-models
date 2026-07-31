"""Serve Qwen/Qwen3-Coder-30B-A3B-Instruct on Modal, OpenAI-compatible, for paper 2.

Why this exists: the cross-family 2D arm (review 1, point #18) needs exactly this model,
and every HF Inference Providers token available 402'd before the monthly reset. The paper's
committed cells for this arm were served by the HF router; the cells completed through this
server differ in SERVING PATH only — same weights (bf16, straight from the Hub), same
OpenAI-compatible API — and the mixed provenance is recorded in REVIEW-RESPONSE #18 and
REPRO-FACTS rather than hidden. `compat_base_url` is deliberately not part of the campaign
resume key: the treatment is the model, the URL is provenance.

Deploy:   modal deploy scripts/modal_qwen3coder_vllm.py
Then:     HF_TOKEN=unused PYTHONPATH=src python scripts/continuous_danger_synthesis.py \
              mini 3 --instrument patch2d --k1 3 --k2 7 --arm both \
              --compat-model Qwen/Qwen3-Coder-30B-A3B-Instruct \
              --compat-base-url https://<workspace>--qwen3coder-vllm-serve.modal.run/v1
Teardown: modal app stop qwen3coder-vllm     (do this when the cells are done: H100 time
          is the whole cost, and scaledown also stops it after 5 idle minutes)
"""
import subprocess

import modal

MODEL = "Qwen/Qwen3-Coder-30B-A3B-Instruct"
PORT = 8000

app = modal.App("qwen3coder-vllm")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm", "huggingface_hub[hf_transfer]")
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1",
          # debian_slim has no CUDA toolkit; flashinfer's JIT sampler wants nvcc.
          # The torch-native sampler is fine for this workload.
          "VLLM_USE_FLASHINFER_SAMPLER": "0"})
)

# The 61 GB of bf16 weights persist here so a warm restart skips the download.
hf_cache = modal.Volume.from_name("hf-cache-qwen3coder", create_if_missing=True)


@app.function(
    image=image,
    gpu="H100",                       # 80 GB: bf16 30B-A3B (~61 GB) + KV at 16k context
    volumes={"/root/.cache/huggingface": hf_cache},
    timeout=60 * 60,
    scaledown_window=300,             # stops itself after 5 idle minutes
)
@modal.concurrent(max_inputs=8)
@modal.web_server(port=PORT, startup_timeout=30 * 60)
def serve():
    subprocess.Popen(
        [
            "vllm", "serve", MODEL,
            "--host", "0.0.0.0",
            "--port", str(PORT),
            "--max-model-len", "16384",
        ]
    )
