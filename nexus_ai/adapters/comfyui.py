import json, time, urllib.request, urllib.error
from nexus_ai.adapters.base import BaseAdapter, ProviderUnavailable, AdapterError, require_loopback_url

class ComfyUIAdapter(BaseAdapter):
    provider_id="comfyui"
    supported_modalities=("image","video","audio")
    def __init__(self,base_url,model_id,workflow,timeout_seconds=900):
        super().__init__(model_id,timeout_seconds)
        if not isinstance(workflow,dict) or not workflow: raise ValueError("API workflow JSON required")
        self.base_url=require_loopback_url(base_url); self.workflow=workflow
    def _request(self,path,payload=None,timeout=10):
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(self.base_url+path,data=data,headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                raw=response.read(); return json.loads(raw.decode()) if raw else {}
        except (urllib.error.URLError,TimeoutError,OSError) as exc: raise ProviderUnavailable(f"ComfyUI unavailable: {exc}") from exc
        except (ValueError,UnicodeDecodeError) as exc: raise AdapterError(f"Invalid ComfyUI response: {exc}") from exc
    def health(self):
        self._request("/system_stats",timeout=5)
        return {"available":True,"provider":self.provider_id,"model_id":self.model_id}
    def execute(self,task):
        workflow=json.loads(json.dumps(self.workflow))
        for node_id,values in task.inputs.get("bindings",{}).items():
            if node_id not in workflow or not isinstance(values,dict): raise AdapterError(f"Invalid node binding: {node_id}")
            workflow[node_id].setdefault("inputs",{}).update(values)
        node=task.inputs.get("prompt_node")
        if node:
            if str(node) not in workflow: raise AdapterError("prompt_node missing from workflow")
            workflow[str(node)].setdefault("inputs",{})[task.inputs.get("prompt_field","text")]=task.prompt
        queued=self._request("/prompt",{"prompt":workflow},timeout=10); prompt_id=queued.get("prompt_id")
        if not prompt_id: raise AdapterError("ComfyUI returned no prompt_id")
        deadline=time.monotonic()+min(task.timeout_seconds,self.timeout_seconds)
        while time.monotonic()<deadline:
            history=self._request("/history/"+prompt_id,timeout=10); item=history.get(prompt_id)
            if item and item.get("outputs"): return {"prompt_id":prompt_id,"outputs":item["outputs"]}
            time.sleep(2)
        raise ProviderUnavailable("ComfyUI job timed out: "+prompt_id)
