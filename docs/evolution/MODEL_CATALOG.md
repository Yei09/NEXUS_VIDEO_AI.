# Model catalog

Machine-readable source: config/ai_models.json.

| Entry | Access / license | Resource note | Integration |
|---|---|---|---|
| Qwen2.5 1.5B Instruct GGUF | Local / Apache-2.0 | ~2.5 GB RAM planning floor; measure actual peak | Text adapter available; model not installed |
| Qwen3-4B | Local / Apache-2.0 | ~7 GB planning floor; not default for low-memory hosts | Not installed |
| Qwen2.5-VL-3B GGUF | Local / Apache-2.0 GGUF distribution | ~8 GB RAM planning floor; measure actual peak | Vision adapter available; model not installed |
| FLUX.1 schnell | Local / Apache-2.0 | Large model; strong GPU recommended | Not installed |
| Kokoro 82M | Local / Apache-2.0 weights | Runtime and voice packs add overhead | Generic CLI boundary only; Kokoro not installed |
| ComfyUI | Local software / GPL-3.0 | Workflow-dependent | Adapter available; server/workflow absent |
| Blender | Local software / GPL-2.0-or-later | Scene-dependent | Existing project renderer |
| FFmpeg | Local software / LGPL/GPL depending build | Codec-dependent | Existing project renderer |

Free-local means no hosted inference bill while running locally; hardware, electricity, storage and bandwidth still consume resources. Hosted API quotas are not assumed. The official Qwen2.5-VL-3B weights page has a research license, so the catalog selects the separate ggml-org GGUF distribution whose model card lists Apache-2.0. Always inspect the exact weights repository before using a different distribution.

Sources: Qwen2.5-1.5B GGUF and Qwen2.5-VL-3B GGUF model cards; llama.cpp server documentation; FLUX.1 schnell model card; Kokoro model card; Blender and FFmpeg license pages.
