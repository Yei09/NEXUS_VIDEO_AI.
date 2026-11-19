import json
from pathlib import Path
DEFAULT_CATALOG=Path(__file__).resolve().parent.parent/"config"/"ai_models.json"
COST_CLASSES={"free_local","free_limited","api_free_conditional","trial","paid","unavailable"}
class ModelRegistry:
 def __init__(self,path=DEFAULT_CATALOG):
  data=json.loads(Path(path).read_text(encoding="utf-8"))
  if data.get("schema_version")!=1 or not isinstance(data.get("models"),list): raise ValueError("Unsupported registry schema")
  self.models={m["id"]:m for m in data["models"]}
  if len(self.models)!=len(data["models"]): raise ValueError("Duplicate model IDs")
  required=("name","provider","specialty","access_type","hardware","license","availability","free_limits","potential_cost","integration_status","execution_method","last_checked")
  for model in self.models.values():
   missing=[key for key in required if key not in model]
   if missing: raise ValueError(f"{model.get('id')} missing {missing}")
   cost_class=model["potential_cost"].get("class")
   if cost_class not in COST_CLASSES: raise ValueError(f"{model['id']}: unknown cost class {cost_class}")
 def get(self,model_id): return self.models[model_id]
 def list(self,specialty=None):
  items=list(self.models.values())
  if specialty: items=[m for m in items if specialty in m["specialty"]]
  return sorted(items,key=lambda m:m["id"])
