import asyncio
import os
import sys
import multiprocessing

# Ensure backend directory is in path
sys.path.append(os.path.abspath("."))

from dotenv import load_dotenv
load_dotenv()
if "GEMINI_API_KEY" not in os.environ:
    os.environ["GEMINI_API_KEY"] = "mock_key_for_test"
if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "mock_key_for_test")

import asyncio
import os
import sys
import logging
import multiprocessing

logging.basicConfig(level=logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.INFO)

sys.path.append(os.path.abspath("."))
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

def run_test_logistics():
    from google.adk.apps import App
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types
    import importlib
    import adk_logistica
    
    print("\n" + "="*50)
    print("TESTING LOGISTICS AGENT (Coronel Charlone)")
    print("="*50)
    
    importlib.reload(adk_logistica)
    # Patch the bad import inside the module just for the test
    adk_logistica.SseServerParams = adk_logistica.SseConnectionParams = __import__('google.adk.tools.mcp_tool.mcp_toolset', fromlist=['SseConnectionParams']).SseConnectionParams
    
    original_get = adk_logistica.get_logistics_agent
    def patched_get():
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
        adk_logistica._cached_mcp_toolset = MCPToolset(
            connection_params=adk_logistica.SseConnectionParams(url="https://agnostic-mcp-server-532234202617.us-central1.run.app/sse")
        )
        return original_get()
    agent = patched_get()
    
    app = App(name="logistics_test_app", root_agent=agent)
    runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)
    
    prompt = """
    Marca: Samsung
    Aparato: Lavarropas
    Repuesto buscado: bomba de desagote de lavarropas samsung
    Ubicación del técnico (lat, lng): -32.9468, -60.6393
    Localidad: Rosario, Santa Fe
    """
    print(f"Buscando: {prompt.strip()}")
    msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    
    async def run_agent():
        response_text = ""
        print("\n>>>> INICIANDO AGENTE DE LOGÍSTICA <<<<\n")
        try:
            async for event in runner.run_async(user_id="test", session_id="test_logistics", new_message=msg):
                author = getattr(event, "author", "unknown")
                msg_obj = getattr(event, "model_message", None) or getattr(event, "agent_message", None)
                
                if msg_obj and hasattr(msg_obj, "content") and msg_obj.content:
                    for part in getattr(msg_obj.content, "parts", []):
                        if getattr(part, "text", None):
                            text = part.text.strip()
                            if text:
                                print(f"[{author.upper()}] {text}")
                                if author == "Coordinador_de_Logistica_de_Campo" or author == "unknown":
                                    response_text += text + "\n"
                        if getattr(part, "function_call", None):
                            print(f"[{author.upper()}] 📞 LLAMADA A FUNCIÓN: {part.function_call.name} ({part.function_call.args})")
                
                # Print tool calls and results
                if getattr(event, "tool_message", None) and getattr(event.tool_message, "content", None):
                    for part in getattr(event.tool_message.content, "parts", []):
                        if getattr(part, "function_response", None):
                            f_name = part.function_response.name
                            f_resp = part.function_response.response
                            resp_str = str(f_resp)
                            if len(resp_str) > 300: resp_str = resp_str[:300] + "..."
                            print(f"[HERRAMIENTA] ✅ RESPUESTA {f_name}: {resp_str}")
        except Exception:
            # If we hit the cancel scope bug, we might still have response_text
            pass
        
        # Guardar en archivo persistente para que no se pierda por el crash de salida
        with open("last_logistics_report.txt", "w", encoding="utf-8") as f:
            f.write(response_text)
            
        return response_text
        
    try:
        response = asyncio.run(run_agent())
        print("\n" + "="*50)
        print("REPORTE FINAL DE LOGÍSTICA")
        print("="*50)
        print(response)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n--- ERROR LOGÍSTICA ---\n{type(e).__name__}: {e}")

if __name__ == "__main__":
    run_test_logistics()

