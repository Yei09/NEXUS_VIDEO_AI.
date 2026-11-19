# Local provider setup (opt-in)

The core never downloads weights, starts servers or contacts hosted AI APIs automatically.

## llama.cpp text
1. Install/build llama.cpp yourself on the target machine.
2. Obtain a compatible GGUF only after checking disk/RAM and the exact model-card license.
3. Start llama-server locally, bound to loopback.
4. Set NEXUS_LLAMA_CPP_URL=http://127.0.0.1:8080 and NEXUS_LLAMA_CPP_MODEL=qwen2.5-1.5b-instruct-gguf.
5. Call build_router() and send a text Task. The adapter checks /health and /v1/chat/completions.

## llama.cpp vision
Configure NEXUS_LLAMA_CPP_VISION_URL and NEXUS_LLAMA_CPP_VISION_MODEL=qwen2.5-vl-3b-gguf. Supply a local image_path in the Task. Images are base64-encoded to the configured loopback endpoint only; remote URLs are rejected.

## ComfyUI
1. Install ComfyUI locally and load the model weights manually.
2. Export a workflow in API format, not the regular UI-save format.
3. Set NEXUS_COMFYUI_URL, NEXUS_COMFYUI_WORKFLOW and NEXUS_COMFYUI_MODEL_ID. The model ID must exist in config/ai_models.json, for example flux.1-schnell.
4. Supply explicit node bindings or prompt_node metadata in the Task. The adapter does not guess node IDs.

Do not use Comfy API, Comfy Cloud, Comfy Router or hosted endpoints under the no-billing policy.

## Kokoro
Kokoro weights are open, but runtime packaging and phonemizer dependencies must be reviewed separately. This release does not claim a verified Kokoro CLI integration. CommandAdapter is a generic safe local-process boundary; configure it only after confirming the exact CLI arguments and output format of the selected distribution.

## No cloud fallback
Only localhost/loopback URLs are accepted. There are no hosted API adapters or API keys. If a local service is down, the director reports no available provider rather than switching to a paid endpoint.
