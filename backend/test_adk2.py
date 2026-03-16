import asyncio
from adk_agents import root_agent

async def examine():
    print("Testing run_async directly...")
    try:
        ag = root_agent.run_async("Test")
        print(f"Type of ag: {type(ag)}")
        async for item in ag:
            print(f"Item: {item}")
    except Exception as e:
        print(f"Error in run_async: {e}")

    # Let's see if Engine works
    try:
        from google.adk.core.engine import Engine
        print("\nTesting Engine...")
        engine = Engine(agent=root_agent)
        # engine might have run, execute, etc. Let's see dir.
        print(f"Engine methods: {[x for x in dir(engine) if not x.startswith('_')]}")
        # Let's try to run it
        if hasattr(engine, 'run'):     
            res = engine.run("Test")
            print(f"Engine.run result: {res}")
        elif hasattr(engine, 'run_async'):
            res = await engine.run_async("Test")
            print(f"Engine.run_async result: {res}")
        elif hasattr(engine, 'execute'):
            res = await engine.execute("Test")
            print(f"Engine.execute result: {res}")
    except Exception as e:
        print(f"Error with Engine: {e}")

if __name__ == "__main__":
    asyncio.run(examine())
