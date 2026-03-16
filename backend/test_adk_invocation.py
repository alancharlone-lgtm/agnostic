
import asyncio
from adk_agents import root_agent

async def test_agent():
    print("Iniciando prueba del agente ADK...")
    try:
        # Probamos el método run_async que detectamos en la inspección
        print("Llamando a run_async...")
        final_text = ""
        async for chunk in root_agent.run_async("Hola, soy un técnico. Tengo una heladera marca Patrick que no enfría. ¿Qué fallas típicas tiene?"):
            if hasattr(chunk, "text"):
                final_text += chunk.text
            elif hasattr(chunk, "message") and hasattr(chunk.message, "content"):
                final_text += chunk.message.content
            else:
                final_text += str(chunk)
            print(f"Recibido chunk: {str(chunk)[:50]}...")
            
        print("\n--- RESPUESTA FINAL DEL AGENTE ---")
        print(final_text)
    except Exception as e:
        print(f"\nError al invocar: {e}")
        print("\nAtributos disponibles en root_agent:")
        print(dir(root_agent))

if __name__ == "__main__":
    asyncio.run(test_agent())
