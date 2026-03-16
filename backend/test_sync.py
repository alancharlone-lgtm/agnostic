import os
from dotenv import load_dotenv
load_dotenv()
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
import sys
sys.stdout.reconfigure(encoding='utf-8')

from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from adk_logistica import logistics_root_agent

def run_test():
    import sys
    print("Iniciando prueba de logistics_root_agent SINCRONA...", flush=True)
    app = App(name="logistics_app", root_agent=logistics_root_agent)
    runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)
    msg = types.Content(role="user", parts=[types.Part.from_text(
        text="Marca: Drean, Aparato: lavarropas, Repuesto: bomba de desagote, Ubicación del Técnico (GPS): -34.6037,-58.3816"
    )])
    
    try:
        final_text = ""
        for event in runner.run(user_id="default", session_id="test_session", new_message=msg):
            # Mostrar info de cada evento para debug
            agent_name = getattr(event, 'author', '???')
            is_final = getattr(event, 'is_final_response', lambda: False)()
            if hasattr(event, 'content') and event.content:
                for part in event.content.parts:
                    if getattr(part, 'text', None):
                        print(f"[{agent_name}] {part.text[:200]}", flush=True)
                        if is_final:
                            final_text += part.text
                    if getattr(part, 'function_call', None):
                        fc = part.function_call
                        print(f"[{agent_name}] TOOL CALL: {fc.name}({dict(fc.args)})", flush=True)
                    if getattr(part, 'function_response', None):
                        fr = part.function_response
                        resp_str = str(fr.response)[:300]
                        print(f"[{agent_name}] TOOL RESP: {fr.name} -> {resp_str}", flush=True)
        print("\n\n=== RESPUESTA FINAL ===")
        print(final_text or "(sin texto final)")
        print("\nFIN")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()
