import asyncio
from adk_agents import root_agent
from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

async def run_runner():
    print("Iniciando Runner con App...")
    try:
        app = App(name="test_app", root_agent=root_agent)
        session_service = InMemorySessionService()
        runner = Runner(app=app, session_service=session_service, auto_create_session=True)
        
        msg = types.Content(role="user", parts=[types.Part.from_text(text="Hola, soy un técnico. Tengo una heladera Patrick que no enfría.")])
        
        print("Llamando a runner.run_async()...")
        final_text = ""
        async for event in runner.run_async(user_id="user1", session_id="ses1", new_message=msg):
            # Print the event to understand its structure
            print(f"Event: {event}")
            if hasattr(event, "content") and event.content:
                for part in event.content.parts:
                    if part.text:
                        final_text += part.text

        print(f"\nRespuesta final extraída: {final_text}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_runner())
