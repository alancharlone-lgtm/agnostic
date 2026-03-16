
import asyncio
import os
import sys
import base64
from google.genai import types
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

# Configurar API Key
os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

async def simulate_vision_agent():
    print("Starting Vision Agent Simulation (Agnostic ADK)...")
    
    try:
        from adk_vision_guide_v2 import root_agent
        
        # 1. Create ADK App
        app = App(name="vision_guide_app", root_agent=root_agent)
        runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)
        
        # 2. Simulate camera frame
        dummy_frame_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        img_data = base64.b64decode(dummy_frame_b64)
        
        # 3. Build prompt as main.py does
        detalles_tecnicos = "Compresor Tecumseh universal de 1/4 HP, conectar bornes C, S, R"
        prompt_text = (
            f"Analizá esta imagen y generá la guía visual de ensamblaje para: {detalles_tecnicos}.\n"
            f"INSTRUCCIÓN PARA EL DIRECTOR VISUAL: El base64 de esta foto para la herramienta MCP es:\n"
            f"--- START BASE64 ---\n{dummy_frame_b64}\n--- END BASE64 ---\n"
            "Usá este base64 exacto cuando llames a 'generar_guia_visual_nanobanana'."
        )
        
        parts = [
            types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
            types.Part.from_text(text=prompt_text)
        ]
        msg = types.Content(role="user", parts=parts)
        
        print("Sending multimodal message to Root Agent...")
        
        # 4. Run and capture events
        final_text = ""
        found_tool_call = False
        
        async for event in runner.run_async(user_id="test_user", session_id="test_session", new_message=msg):
            # Check for tool call
            if hasattr(event, "tool_call") and event.tool_call:
                print(f"TOOL CALL DETECTED: {event.tool_call.name}")
                found_tool_call = True
            
            # Check for tool call result
            if hasattr(event, "tool_call_result") and event.tool_call_result:
                print(f"TOOL CALL RESULT RECEIVED: {event.tool_call_result.name}")
            
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if part.text:
                        print(f"AGENT: {part.text}")
                        final_text += part.text

        print("\n--- SIMULATION SUMMARY ---")
        if found_tool_call:
            print("SUCCESS: The orchestrator correctly determined it should call the visual tool.")
        else:
            print("WARNING: The agent did not call the tool. Check image processing.")
        
        print(f"Final text: {final_text[:100]}...")
        
    except Exception as e:
        print(f"ERROR IN SIMULATION: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simulate_vision_agent())
