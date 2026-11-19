# NEXUS VIDEO AI — Multimodel core

## Boundary
The cinematic renderer remains independent. nexus_ai owns metadata, normalized tasks/results, adapters, routing, agent roles and an append-only journal. Blender scene construction and FFmpeg assembly do not import model SDKs.

## Provider lifecycle
Catalog record -> adapter -> explicit local configuration -> health check -> real input/output test -> verified status. Class presence alone is not integration.

## Adapters
- LlamaCppAdapter: local OpenAI-compatible text/code/planning/audit.
- LlamaCppVisionAdapter: local OpenAI-compatible image payload using data URLs.
- ComfyUIAdapter: local API workflow for image/video/audio.
- CommandAdapter: explicit local executable boundary; no shell invocation.

## Agents
Nine role profiles have separate responsibilities and may share a model. Every result identifies provider and model. The director only selects registered adapters which pass health and policy checks.

## Cost policy
Paid models rejected by default, estimated task cost capped at USD 0, no hosted fallback. Hosted Comfy API is excluded.

## Persistence
evolution/history.jsonl is append-only; evolution/state.json is atomically replaced; recovery validates both.

## Limitations
No weights are downloaded. No external model is marked verified. ComfyUI needs a real local server and API workflow. Kokoro needs a verified CLI/runtime. No real image/video/speech/audio/vision inference is yet proven. Vision has an adapter contract but no configured model. Blender and FFmpeg are media tools, not AI models.
