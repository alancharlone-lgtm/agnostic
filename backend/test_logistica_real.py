import os
from dotenv import load_dotenv
load_dotenv()
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
import anyio
import traceback
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

# Importamos el agente directamente de nuestro archivo modificado
from adk_logistica import logistics_root_agent

async def run_test():
    print("Iniciando prueba de logistics_root_agent...")
    
    app = App(name="logistics_app", root_agent=logistics_root_agent)
    runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)
    
    query = "Marca: Drean, Aparato: lavarropas, Repuesto: bomba de desagote, Ubicación del Técnico (GPS): -34.6037,-58.3816"
    print(f"Consulta: {query}\n")
    
    msg = types.Content(role="user", parts=[types.Part.from_text(text=query)])
    
    try:
        final_text = ""
        # iteramos sobre los eventos para ver incluso llamadas a herramientas si es posible
        async for event in runner.run_async(user_id="default", session_id="test_session", new_message=msg):
            # Print ALL events to see exactly what the agent is doing internally
            print(f"EVENT TIPO: {type(event)}")
            
            if hasattr(event, "content") and getattr(event, "content", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        print(f"TEXTO DEL AGENTE: {part.text}")
                        final_text += part.text
                    elif getattr(part, "function_call", None):
                        print(f"LLAMADA A HERRAMIENTA: {part.function_call.name} con args {part.function_call.args}")
                        
        print(f"\nRESULTADO FINAL ACUMULADO:\n{final_text}")
    except Exception as e:
        print(f"Error durante la ejecución: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    anyio.run(run_test)
