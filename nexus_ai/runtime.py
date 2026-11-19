"""Explicit environment-based local provider wiring with a safe RAM budget."""
import json, os
from pathlib import Path
from nexus_ai.registry import ModelRegistry
from nexus_ai.director import Director
from nexus_ai.memory import EvolutionMemory
from nexus_ai.hardware import snapshot
from nexus_ai.adapters.llama_cpp import LlamaCppAdapter
from nexus_ai.adapters.vision import LlamaCppVisionAdapter
from nexus_ai.adapters.comfyui import ComfyUIAdapter

def build_router(memory_root="evolution",policy=None):
    registry=ModelRegistry(); adapters={}
    measured=snapshot()
    available=measured.get("ram_available_mb")
    safe_ram=max(0,int(available)-2048) if available is not None else 0
    effective={"allow_paid":False,"allow_remote":False,"allow_conditional_api":False,
               "max_cost_usd":0.0,"max_memory_mb":safe_ram,"allowed_licenses":[]}
    if policy:
        effective["max_memory_mb"]=int(policy.get("max_memory_mb",safe_ram))
        effective["allowed_licenses"]=list(policy.get("allowed_licenses",[]))
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
    return Director(registry,adapters,memory=EvolutionMemory(memory_root),policy=effective)
