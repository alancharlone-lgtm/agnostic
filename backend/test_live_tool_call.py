import asyncio
import os
from google import genai
from google.genai import types

api_key_live = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key_live)

def consultar_orquestador_reparaciones(marca: str, falla_reportada: str, equipo: str = "electrodomestico") -> str:
    print(f"✅ HERRAMIENTA DISPARADA EXITOSAMENTE: {marca}, {falla_reportada}")
    return "Diagnostico simulado: resistencia quemada."

async def main():
    system_instruction = "Eres un asistente técnico. NUNCA respondas directamente a consultas técnicas. OBLIGATORIO: Si el usuario menciona una falla o rotura de un equipo de cualquier marca, DEBES llamar INMEDIATAMENTE a la herramienta consultar_orquestador_reparaciones(marca, falla_reportada, equipo) ANTES de darle cualquier diagnóstico."
    
    tool_declarations = [
        {"function_declarations": [{"name": "consultar_orquestador_reparaciones", "description": "Consulta técnica profunda sobre manuales y fallas."}]}
    ]

    config = types.LiveConnectConfig(
        response_modalities=['AUDIO'],
        system_instruction=types.Content(parts=[types.Part.from_text(text=system_instruction)]),
        tools=tool_declarations
    )
    
    print("Iniciando conexión Live...")
    async with client.aio.live.connect(model="gemini-2.5-flash-native-audio-preview-12-2025", config=config) as session:
        print("Conexión establecida. Enviando prompt de prueba...")
        await session.send(input="Tengo un lavarropas Samsung que no desagota el agua.", end_of_turn=True)
        
        async for response in session.receive():
            if response.server_content and response.server_content.model_turn:
                for part in response.server_content.model_turn.parts:
                    if part.text:
                        print(f"Texto: {part.text}", end="", flush=True)
            
            if response.tool_call:
                print("\n\n>>> GEMINI SOLICITO LLAMAR A UNA HERRAMIENTA! <<<")
                for function_call in response.tool_call.function_calls:
                    print(f"Tool: {function_call.name}, Args: {function_call.args}")
                    break
                break
                
            if response.server_content and response.server_content.turn_complete:
                print("\n\nTurno completado sin llamar a herramientas.")
                break

if __name__ == "__main__":
    asyncio.run(main())
