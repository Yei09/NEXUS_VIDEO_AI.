import os, shutil, subprocess
from nexus_ai.adapters.base import BaseAdapter, ProviderUnavailable, AdapterError

class CommandAdapter(BaseAdapter):
    """Safe explicit local CLI adapter; does not assume a particular vendor command."""
    provider_id="local-command"
    supported_modalities=("speech","audio","code","audit","video")
    def __init__(self,executable,model_id,args=None,timeout_seconds=120):
        super().__init__(model_id,timeout_seconds); self.executable=executable; self.args=list(args or [])
    def health(self):
        path=shutil.which(self.executable)
        return {"available":bool(path),"executable":path,"provider":self.provider_id,"model_id":self.model_id}
    def execute(self,task):
        executable=shutil.which(self.executable)
        if not executable: raise ProviderUnavailable("Executable not installed: "+self.executable)
        output=task.inputs.get("output_path")
        if not output: raise AdapterError("output_path required")
        command=[executable,*self.args,"--text",task.prompt,"--output",str(output)]
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=min(task.timeout_seconds,self.timeout_seconds),check=False)
        except subprocess.TimeoutExpired as exc: raise ProviderUnavailable("Local command timed out") from exc
        if result.returncode: raise AdapterError(f"Command exited {result.returncode}: {result.stderr[-1000:]}")
        if not os.path.isfile(output) or os.path.getsize(output)==0: raise AdapterError("No non-empty output file created")
        return {"output_path":str(output),"stdout":result.stdout[-2000:]}
