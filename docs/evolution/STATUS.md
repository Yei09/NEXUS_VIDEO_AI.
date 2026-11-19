# Evolution status — multimodel core bootstrap

- Branch: cinematic-reconstruction
- Starting HEAD checked before edits: 87125a96e96d1458120763c0bca3ecfe7cbdc7d5
- Core implementation commit: 03d0114fc0beede22e6afc490541e4d71da298cd
- Latest CI run: 44446326553 — success; tested implementation commit ce6fea5908a5f36cef45c7537042764c8c1e9fbe (same code tree; later commit only records CI evidence).
- CI: compileall passed, model catalog JSON passed, 18 unit/contract tests passed in 1.571 seconds, hardware snapshot captured.
- No model weights downloaded; no paid API, billing, subscription, Make, Google Drive or hosted inference activated.
- No recurring workflow enabled; no PR merged.

Adapter contract tests passed for llama.cpp text, llama.cpp vision image payload, ComfyUI workflow API, and a safe local command executable. Router selection, fallback behavior, policy constraints, nine agent roles, memory recovery and bounded cycle recovery were also tested. These verify software contracts, not real AI model inference.

Truthful integration status:
- llama.cpp text: adapter available and mock HTTP contract tested; real llama-server/model not verified.
- llama.cpp vision: adapter available and mock image-payload contract tested; real vision model not verified.
- ComfyUI: adapter available and mocked workflow contract tested; real server/workflow not configured.
- Local CLI boundary: tested with temporary fixture executable; Kokoro executable/weights not verified.
- Qwen and FLUX: weights not downloaded or run.
- Blender/FFmpeg: existing media tools, not AI models.
- Qwen2.5-VL-3B GGUF: candidate catalogued, not installed or benchmarked.

Next objective: measure the user's actual development machine, then configure one small local language model and perform a real inference before promoting it to verified.
