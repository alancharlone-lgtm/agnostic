import asyncio
import os
import sys
import io

# Fix Windows terminal encoding so emojis don't crash the output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from dotenv import load_dotenv

# Mocking the environment for the agent
load_dotenv()
if not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

from adk_logistica import get_logistics_agent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

async def test_logistics():
    print("Iniciando Runner Logística ADK...")
    app = App(name="logistics_app", root_agent=get_logistics_agent())
    runner = Runner(
        app=app,
        session_service=InMemorySessionService(),
        auto_create_session=True
    )
    
    query = "Repuesto: Actuador de cambios, Marca: Whirlpool, Equipo: lavarropas, Ubicación: Centro"
    print(f"Consultando Logística con: {query}")
    
    msg = types.Content(role="user", parts=[types.Part.from_text(text=query)])
    
    final_text = ""
    async for event in runner.run_async(user_id="default", session_id="default", new_message=msg):
        if hasattr(event, "content") and getattr(event, "content", None):
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final_text += part.text
            
    print("\n--- RESPUESTA DE LOGÍSTICA ---")
    print(final_text)
    print("------------------------------")

if __name__ == "__main__":
    asyncio.run(test_logistics())
