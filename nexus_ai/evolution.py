import uuid
from nexus_ai.memory import EvolutionMemory

class EvolutionCycle:
    """One bounded cycle per invocation; no loops, schedules or autonomous code mutation."""
    def __init__(self,memory=None): self.memory=memory or EvolutionMemory()
    def begin(self,objective):
        if not isinstance(objective,str) or not objective.strip(): raise ValueError("objective required")
        state=self.memory.load_state()
        if state.get("status")=="RUNNING": raise RuntimeError("A cycle is already marked RUNNING")
        cycle_id=str(uuid.uuid4())
        state.update({"status":"RUNNING","current_cycle":cycle_id,"objective":objective,
                      "last_result":None,"next_objective":None})
        self.memory.save_state(state)
        self.memory.record("cycle_started",{"cycle_id":cycle_id,"objective":objective})
        return cycle_id
    def finish(self,cycle_id,result,next_objective):
        state=self.memory.load_state()
        if state.get("status")!="RUNNING" or state.get("current_cycle")!=cycle_id:
            raise RuntimeError("Cycle ID does not match active cycle")
        state.update({"status":"READY","last_result":result,"next_objective":next_objective,"current_cycle":None})
        self.memory.save_state(state)
        self.memory.record("cycle_finished",{"cycle_id":cycle_id,"result":result,"next_objective":next_objective})
        return state
    def fail(self,cycle_id,error,next_objective):
        state=self.memory.load_state()
        if state.get("status")!="RUNNING" or state.get("current_cycle")!=cycle_id:
            raise RuntimeError("Cycle ID does not match active cycle")
        state.update({"status":"FAILED","last_error":str(error),"next_objective":next_objective,"current_cycle":None})
        self.memory.save_state(state)
        self.memory.record("cycle_failed",{"cycle_id":cycle_id,"error":str(error),"next_objective":next_objective})
        return state
    def recover_interrupted(self):
        """Call explicitly after confirming the previous process is no longer running."""
        state=self.memory.load_state()
        if state.get("status")!="RUNNING": return state
        cycle_id=state.get("current_cycle")
        state.update({"status":"INTERRUPTED","current_cycle":None,
                      "last_error":"Process ended before cycle completion; inspect artifacts before retrying"})
        self.memory.save_state(state)
        self.memory.record("cycle_interrupted",{"cycle_id":cycle_id,"next_objective":state.get("objective")})
        return state
