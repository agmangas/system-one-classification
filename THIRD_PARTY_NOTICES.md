# Third-party notices

The Von image (the default tags) bundles the following software and model weights:

- **Von 1.3.5 inference code and Von 1.2 weights**, copyright 2026 Victor Hugo Panisa, Apache License 2.0. Source: https://github.com/wfzyx/von ; weights: https://huggingface.co/wfzyx/von . The service uses the upstream model without training or changing its weights.
- **ModernBERT-large**, copyright 2022 MosaicML Examples authors, Apache License 2.0. Source: https://huggingface.co/answerdotai/ModernBERT-large . Von weights are derived from this base model.

The SLM image (the `-slm` tags) bundles:

- **llama.cpp v0.5.0 (build b11146)**, copyright 2023-2026 The ggml authors, MIT License. Source: https://github.com/ggml-org/llama.cpp ; binaries from the `ghcr.io/ggml-org/llama.cpp:server-b11146` image.
- **Qwen3.5-4B**, copyright 2026 Alibaba Cloud, Apache License 2.0. Source: https://huggingface.co/Qwen/Qwen3.5-4B ; the bundled Q4_K_M GGUF quantisation comes from https://huggingface.co/unsloth/Qwen3.5-4B-GGUF . The service uses the model without training or changing its weights.
- **Bonsai-4B**, copyright 2026-present Prism ML, Inc., Apache License 2.0, built from Qwen3-4B, copyright 2024 Alibaba Cloud, Apache License 2.0. Source: https://huggingface.co/prism-ml/Bonsai-4B-gguf ; its notice is in `licenses/BONSAI-NOTICE.txt`. Created using Bonsai by Prism ML. The service uses the model without training or changing its weights.

The corresponding license texts are included in `licenses/`. This service is independently maintained and is not endorsed by Von, Answer.AI, TypeSafe, the ggml authors, Alibaba Cloud, Unsloth or Prism ML.
