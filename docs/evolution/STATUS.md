# Evolution status — multimodel core bootstrap

- Branch: cinematic-reconstruction
- Starting HEAD checked before edits: 87125a96e96d1458120763c0bca3ecfe7cbdc7d5
- Scope: model registry, text/vision/ComfyUI/CLI adapters, nine role profiles, policy router, persistent journal, bounded cycle manager and tests.
- No model weights downloaded; no paid API, billing, subscription, Make, Google Drive or hosted inference activated.
- No recurring workflow enabled; no PR merged.

The tests exercise llama.cpp-compatible text and image HTTP contracts, ComfyUI workflow API contract, and a safe local CLI process against controlled test fixtures. These verify adapter protocol behavior, not real installed AI model inference.

Truthful status:
- llama.cpp text: adapter available and mock HTTP contract tested; real llama-server/model not verified.
- llama.cpp vision: adapter available and mock image-payload contract tested; real vision model not verified.
- ComfyUI: adapter available and mocked workflow contract tested; real server/workflow not configured.
- Local CLI boundary: tested with a temporary test executable; Kokoro executable/weights not verified.
- Qwen and FLUX: weights not downloaded or run.
- Blender/FFmpeg: existing media tools, not AI models.
- Qwen2.5-VL-3B GGUF: candidate catalogued, not installed or benchmarked.

Next objective: run CI; then configure one small local language model endpoint and perform real inference before promoting it to verified.
