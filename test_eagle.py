import asyncio
import os
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types as genai_types
from backend.adk_vision_precision import root_agent as vision_precision_root_agent

async def main():
    try:
        app = App(name="vision_precision_app", root_agent=vision_precision_root_agent)
        runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)
        
        # Simular un frame
        with open("backend/temp_test.jpg", "wb") as f:
            f.write(b"fake_image_bytes")
        
        frame_bytes = b"fake_image_bytes"
        query = "Localiza con máxima precisión el componente: tornillo."
        image_part = genai_types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg")
        text_part = genai_types.Part.from_text(text=query)
        msg = genai_types.Content(role="user", parts=[image_part, text_part])
        
        print("Calling runner.run_async...")
        final_text = ""
        async for event in runner.run_async(user_id="test_user", session_id="test_session", new_message=msg):
            if hasattr(event, "content") and getattr(event, "content", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_text += part.text
                        
        print("Success!", final_text)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
