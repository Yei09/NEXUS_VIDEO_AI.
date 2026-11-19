import json, tempfile, unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from nexus_ai.types import Task
from nexus_ai.registry import ModelRegistry
from nexus_ai.adapters.base import BaseAdapter, AdapterError
from nexus_ai.adapters.llama_cpp import LlamaCppAdapter
from nexus_ai.adapters.vision import LlamaCppVisionAdapter
from nexus_ai.adapters.comfyui import ComfyUIAdapter
from nexus_ai.adapters.command import CommandAdapter
from nexus_ai.director import Director
from nexus_ai.agents import Agent, AGENT_ROLES
from nexus_ai.memory import EvolutionMemory
from nexus_ai.evolution import EvolutionCycle

class FakeAdapter(BaseAdapter):
 provider_id="fake"; supported_modalities=("text",)
 def __init__(self,model_id,fail=False): super().__init__(model_id); self.fail=fail
 def health(self): return {"available":True}
 def execute(self,task):
  if self.fail: raise RuntimeError("deliberate test failure")
  return {"text":"REAL_TEST_OUTPUT"}

class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(b'{"status":"ok"}')
 def do_POST(self):
  n=int(self.headers.get("Content-Length","0")); self.server.last_payload=json.loads(self.rfile.read(n))
  body=json.dumps({"model":"test-served-model","choices":[{"message":{"content":"adapter integration works"}}]}).encode()
  self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(body)
 def log_message(self,*args): pass

class ComfyHandler(BaseHTTPRequestHandler):
 def do_GET(self):
  body={"status":"ok"} if self.path=="/system_stats" else {"test-prompt":{"outputs":{"3":{"images":[{"filename":"out.png"}]}}}}
  self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(body).encode())
 def do_POST(self):
  n=int(self.headers.get("Content-Length","0")); self.server.last_payload=json.loads(self.rfile.read(n))
  self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(b'{"prompt_id":"test-prompt"}')
 def log_message(self,*args): pass

class CoreTests(unittest.TestCase):
 def test_task_validation(self):
  with self.assertRaises(ValueError): Task("text","").validate()
  with self.assertRaises(ValueError): Task("text","x",timeout_seconds=99999).validate()
  Task("text","valid").validate()
 def test_registry_schema_and_cost_classes(self):
  r=ModelRegistry(); self.assertGreaterEqual(len(r.models),8)
  for m in r.list():
   self.assertIn(m["potential_cost"]["class"],("free_local","free_limited","api_free_conditional","trial","paid","unavailable"))
   for k in ("name","provider","specialty","access_type","hardware","license","availability","free_limits","potential_cost","integration_status","execution_method","last_checked"): self.assertIn(k,m)
 def test_uninstalled_models_not_marked_integrated(self):
  r=ModelRegistry()
  self.assertEqual(r.get("flux.1-schnell")["integration_status"],"not_installed_not_tested")
  self.assertEqual(r.get("kokoro-82m")["integration_status"],"not_installed_not_tested")
 def test_adapter_success_identifies_model(self):
  result=FakeAdapter("unit-model").run(Task("text","hello"))
  self.assertTrue(result.ok); self.assertEqual(result.model_id,"unit-model")
  self.assertEqual(result.output["text"],"REAL_TEST_OUTPUT")
 def test_adapter_handles_runtime_error(self):
  result=FakeAdapter("broken",True).run(Task("text","hello"))
  self.assertFalse(result.ok); self.assertIn("deliberate",result.error)
 def test_wrong_modality_rejected(self):
  with self.assertRaises(AdapterError): FakeAdapter("x").run(Task("image","hello"))
 def test_director_dispatches_and_records_model(self):
  registry=ModelRegistry(); model=registry.get("qwen2.5-1.5b-instruct-gguf"); model["specialty"]=["text"]
  result=Director(registry,{model["id"]:FakeAdapter(model["id"])}).dispatch(Task("text","test"))
  self.assertTrue(result.ok); self.assertEqual(result.model_id,model["id"]); self.assertIn("selection_score",result.metadata)
 def test_director_falls_back_only_to_registered_healthy_adapter(self):
  registry=ModelRegistry()
  primary=registry.get("qwen3-4b"); primary["specialty"]=["text"]
  backup=registry.get("qwen2.5-1.5b-instruct-gguf"); backup["specialty"]=["text"]
  result=Director(registry,{primary["id"]:FakeAdapter(primary["id"],True),backup["id"]:FakeAdapter(backup["id"])}).dispatch(Task("text","test"))
  self.assertTrue(result.ok); self.assertEqual(result.model_id,backup["id"])
  self.assertEqual(result.metadata["fallback_attempts"][0]["model_id"],primary["id"])
 def test_no_fabricated_fallback(self):
  result=Director(ModelRegistry(),{}).dispatch(Task("image","scene"))
  self.assertFalse(result.ok); self.assertEqual(result.metadata["fallback_count"],0)
 def test_nine_agent_roles_and_scope(self):
  self.assertEqual(len(AGENT_ROLES),9); self.assertIn("vision",AGENT_ROLES["cinematic_evaluator"])
  with self.assertRaises(ValueError): Agent("screenwriter",None).run("x",modality="image")
 def test_memory_recovery(self):
  with tempfile.TemporaryDirectory() as d:
   mem=EvolutionMemory(d); mem.record("test",{"status":"ok"}); self.assertEqual(mem.recover()["events_validated"],1)
 def test_evolution_cycle_is_bounded(self):
  with tempfile.TemporaryDirectory() as d:
   cycle=EvolutionCycle(EvolutionMemory(d)); cid=cycle.begin("one bounded improvement")
   with self.assertRaises(RuntimeError): cycle.begin("concurrent cycle")
   state=cycle.finish(cid,{"tests":"pass"},"next task")
   self.assertEqual(state["status"],"READY"); self.assertEqual(state["next_objective"],"next task")
 def test_evolution_cycle_recovers_interrupted_run(self):
  with tempfile.TemporaryDirectory() as d:
   EvolutionCycle(EvolutionMemory(d)).begin("interrupted task")
   state=EvolutionCycle(EvolutionMemory(d)).recover_interrupted()
   self.assertEqual(state["status"],"INTERRUPTED"); self.assertIsNone(state["current_cycle"])
 def test_loopback_only_policy(self):
  with self.assertRaises(ValueError): LlamaCppAdapter("https://example.com","remote")
 def test_llama_cpp_http_contract(self):
  server=HTTPServer(("127.0.0.1",0),Handler); thread=Thread(target=server.serve_forever,daemon=True); thread.start()
  try:
   adapter=LlamaCppAdapter(f"http://127.0.0.1:{server.server_port}","unit-model")
   self.assertTrue(adapter.health()["available"]); result=adapter.run(Task("text","hello"))
   self.assertTrue(result.ok,result.error); self.assertEqual(result.output["text"],"adapter integration works")
  finally: server.shutdown(); thread.join(timeout=2); server.server_close()
 def test_vision_adapter_image_payload_contract(self):
  server=HTTPServer(("127.0.0.1",0),Handler); thread=Thread(target=server.serve_forever,daemon=True); thread.start()
  try:
   with tempfile.TemporaryDirectory() as d:
    image=Path(d)/"sample.png"; image.write_bytes(b"test-image-payload")
    adapter=LlamaCppVisionAdapter(f"http://127.0.0.1:{server.server_port}","vision-unit-model")
    result=adapter.run(Task("vision","Describe frame",inputs={"image_path":str(image)}))
    self.assertTrue(result.ok,result.error)
    content=server.last_payload["messages"][0]["content"]
    self.assertEqual(content[0]["text"],"Describe frame")
    self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/png;base64,"))
  finally: server.shutdown(); thread.join(timeout=2); server.server_close()
 def test_comfyui_workflow_api_contract(self):
  server=HTTPServer(("127.0.0.1",0),ComfyHandler); thread=Thread(target=server.serve_forever,daemon=True); thread.start()
  try:
   adapter=ComfyUIAdapter(f"http://127.0.0.1:{server.server_port}","flux.1-schnell",{"1":{"inputs":{}}},timeout_seconds=5)
   self.assertTrue(adapter.health()["available"])
   result=adapter.run(Task("image","cinematic corridor",inputs={"prompt_node":"1","prompt_field":"text"}))
   self.assertTrue(result.ok,result.error); self.assertEqual(result.output["prompt_id"],"test-prompt")
   self.assertEqual(server.last_payload["prompt"]["1"]["inputs"]["text"],"cinematic corridor")
  finally: server.shutdown(); thread.join(timeout=2); server.server_close()
 def test_command_adapter_executes_local_process(self):
  with tempfile.TemporaryDirectory() as d:
   executable=Path(d)/"fake_tts"
   executable.write_text("#!/usr/bin/env python3\nimport sys\np=sys.argv[sys.argv.index('--output')+1]\nopen(p,'wb').write(b'audio')\n",encoding="utf-8")
   executable.chmod(0o755); output=Path(d)/"voice.wav"
   adapter=CommandAdapter(str(executable),"fake-kokoro",timeout_seconds=5)
   self.assertTrue(adapter.health()["available"]); result=adapter.run(Task("speech","hello",inputs={"output_path":str(output)}))
   self.assertTrue(result.ok,result.error); self.assertEqual(output.read_bytes(),b"audio")

if __name__=="__main__": unittest.main()
