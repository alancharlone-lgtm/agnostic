import os
import asyncio
from google.adk.runners import Runner, InMemorySessionService
from adk_logistica import _validador_web

os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

async def test_ml_scraping():
    print("Testing if Validador Web can read MercadoLibre...")
    # URL de búsqueda de Google (normal internet search)
    ml_url = "https://www.google.com/search?q=precio+bomba+desagote+lavarropas+samsung+mercadolibre"
    
    prompt = f"Entrá a esta URL de Google: {ml_url} y decime los precios que veas para el repuesto en los resultados de MercadoLibre o cualquier otra tienda."
    
    runner = Runner(
        app_name="test_app",
        agent=_validador_web,
        session_service=InMemorySessionService(),
        auto_create_session=True
    )
    
    from google.genai import types
    msg = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    
    async for event in runner.run_async(user_id="test", session_id="test_scraping", new_message=msg):
        msg_obj = getattr(event, "model_message", None) or getattr(event, "agent_message", None)
        if msg_obj and msg_obj.content:
            for part in msg_obj.content.parts:
                if part.text:
                    print(part.text)

if __name__ == "__main__":
    asyncio.run(test_ml_scraping())
