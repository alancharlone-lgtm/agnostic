import asyncio
import os
from dotenv import load_dotenv

# Mocking the environment for the agent
load_dotenv()
if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

from adk_agents import get_repairs_agent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

async def test_agent():
    print("Iniciando Runner ADK...")
    app = App(name="repairs_app", root_agent=get_repairs_agent())
    runner = Runner(
        app=app,
        session_service=InMemorySessionService(),
        auto_create_session=True
    )
    
    query = "Equipo: lavarropas, Marca: Whirlpool, Falla: no centrifuga. Si no encuentras el manual, busca las fallas típicas en la web y dime qué piezas debo revisar y cuáles son los repuestos necesarios."
    print(f"Consultando Agente con: {query}")
    
    msg = types.Content(role="user", parts=[types.Part.from_text(text=query)])
    
    final_text = ""
    async for event in runner.run_async(user_id="default", session_id="default", new_message=msg):
        if hasattr(event, "content") and getattr(event, "content", None):
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final_text += part.text
            
    print("\n--- RESPUESTA DEL AGENTE ---")
    print(final_text)
    print("----------------------------")

if __name__ == "__main__":
    asyncio.run(test_agent())
