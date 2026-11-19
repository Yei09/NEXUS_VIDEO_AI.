"""Explicit environment-based provider wiring. Nothing is started or downloaded."""
import json, os
from pathlib import Path
from nexus_ai.registry import ModelRegistry
from nexus_ai.director import Director
from nexus_ai.memory import EvolutionMemory
from nexus_ai.adapters.llama_cpp import LlamaCppAdapter
from nexus_ai.adapters.vision import LlamaCppVisionAdapter
from nexus_ai.adapters.comfyui import ComfyUIAdapter

def build_router(memory_root="evolution",policy=None):
    registry=ModelRegistry(); adapters={}
    url=os.environ.get("NEXUS_LLAMA_CPP_URL")
    model=os.environ.get("NEXUS_LLAMA_CPP_MODEL","qwen2.5-1.5b-instruct-gguf")
    if url: adapters[model]=LlamaCppAdapter(url,model)
    vision_url=os.environ.get("NEXUS_LLAMA_CPP_VISION_URL")
    vision_model=os.environ.get("NEXUS_LLAMA_CPP_VISION_MODEL","qwen2.5-vl-3b-gguf")
    if vision_url: adapters[vision_model]=LlamaCppVisionAdapter(vision_url,vision_model)
    comfy_url=os.environ.get("NEXUS_COMFYUI_URL")
    workflow_path=os.environ.get("NEXUS_COMFYUI_WORKFLOW")
    comfy_model=os.environ.get("NEXUS_COMFYUI_MODEL_ID")
    if comfy_url and workflow_path and comfy_model:
        registry.get(comfy_model)
        workflow=json.loads(Path(workflow_path).read_text(encoding="utf-8"))
        adapters[comfy_model]=ComfyUIAdapter(comfy_url,comfy_model,workflow)
    return Director(registry,adapters,memory=EvolutionMemory(memory_root),policy=policy)
