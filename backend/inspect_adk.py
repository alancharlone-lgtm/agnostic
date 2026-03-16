
import asyncio
from adk_agents import root_agent

async def inspect_agent():
    print(f"Tipo de root_agent: {type(root_agent)}")
    print("Métodos y atributos:")
    for attr in dir(root_agent):
        if not attr.startswith("_"):
            print(f"- {attr}")

if __name__ == "__main__":
    asyncio.run(inspect_agent())
