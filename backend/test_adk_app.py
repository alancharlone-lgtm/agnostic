import asyncio
from adk_agents import root_agent
from google.adk.apps import App

async def run_app():
    print("Iniciando App con root_agent...")
    try:
        app = App(name="test_app", root_agent=root_agent)
        
        # Check if App has a simple run method
        if hasattr(app, "run"):
            print("Llamando a app.run()...")
            # Usually .run() takes a session_id and user input
            res = app.run(session_id="test_1", user_input="Hola, tengo una heladera Patrick que no enfría.")
            print(f"Respuesta de app.run: {res}")
        elif hasattr(app, "run_async"):
            print("Llamando a app.run_async()...") # Just in case
            pass
        elif hasattr(app, "chat"):
            print("Llamando a app.chat()...")
            pass
        else:
            print("Métodos de app:", dir(app))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_app())
