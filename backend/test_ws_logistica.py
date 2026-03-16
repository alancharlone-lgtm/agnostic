import asyncio
import websockets
import json
import time

async def simulate_logistics_flow():
    uri = "ws://localhost:8000/ws/gemini-live"
    async with websockets.connect(uri) as websocket:
        print("--- INICIANDO SIMULACIÓN DE LOGÍSTICA ---")
        
        # 1. Inyectar contexto de que ya sabemos qué equipo es (Lavarropas Whirlpool)
        # y que el técnico pregunta por el precio del actuador
        print("\n[Paso 1] Técnico pregunta por el repuesto 'Actuador de cambios'...")
        prompt = {
            "type": "text", 
            "text": "Ok, entiendo el diagnóstico. ¿Tenés stock del 'Actuador de cambios' para este Whirlpool en mi camioneta o en tiendas del Centro?"
        }
        await websocket.send(json.dumps(prompt))
        
        # Esperar un poco para que Gemini procese y decida llamar a la herramienta
        print("Esperando 10s para gatear la herramienta...")
        await asyncio.sleep(10.0)
        
        start_time = time.time()
        tool_called = False
        
        while time.time() - start_time < 30: # 30 segundos de timeout
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                
                if isinstance(message, str):
                    data = json.loads(message)
                    # En nuestro backend, cuando llamamos a una herramienta NON_BLOCKING, 
                    # enviamos un JSON al cliente para que sepa que algo está pasando en el fondo (opcional según implementación)
                    # pero lo más importante es ver el log del servidor.
                    if data.get("type") == "tool_call":
                        print(f"\n>>> 🛠️ HERRAMIENTA DETECTADA: {data.get('name')}")
                        if data.get("name") == "consultar_logistica_repuestos":
                            tool_called = True
                else:
                    # Audio (lo ignoramos en la consola pero contamos los bytes)
                    pass
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error: {e}")
                break

        if tool_called:
            print("\n✅ ÉXITO: El agente de logística fue invocado correctamente por Gemini.")
        else:
            print("\n❌ FALLO: Gemini decidió no llamar a la logística. Revisa los logs del servidor para ver el razonamiento.")

if __name__ == "__main__":
    asyncio.run(simulate_logistics_flow())
