import inspect
from adk_agents import root_agent

sig = inspect.signature(root_agent.run_async)
for name, param in sig.parameters.items():
    print(f"Param: {name}")
    try:
        if isinstance(param.annotation, str):
            print(f" Annotation (str): {param.annotation}")
        else:
            print(f" Annotation: {param.annotation}")
            print(f" Module: {param.annotation.__module__}")
            print(f" Attributes: {dir(param.annotation)}")
    except Exception as e:
        print(f" Error: {e}")
