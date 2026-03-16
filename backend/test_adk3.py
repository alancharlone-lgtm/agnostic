import inspect
from adk_agents import root_agent

print("run_async signature:")
print(inspect.signature(root_agent.run_async))
print("\nrun_live signature:")
if hasattr(root_agent, "run_live"):
    print(inspect.signature(root_agent.run_live))
