import asyncio
import websockets
import json
import base64
import time

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws/gemini-live?mode=residential&location=Testing"
    try:
        async with websockets.connect(uri) as websocket:
            print("Conectado al servidor WebSocket")
            
            # Simular CEREBRO PREDICTIVO (Inyección silenciosa de contexto visual)
            vision_context = "[CONTEXTO VISUAL PRE-CARGADO] La cámara identificó: lavarropas de marca Whirlpool. OBLIGATORIO: En cuanto tengas la falla, dispara consultar_orquestador_reparaciones."
            await websocket.send(json.dumps({"type": "text", "text": vision_context}))
            print("Contexto visual simulado enviado")
            
            # ESPERAR a que termine de saludar (el proactive_vision_loop)
            print("Esperando 5s para que termine el saludo inicial...")
            time.sleep(5.0)

            # Enviar mensaje de texto para provocar la llamada a la herramienta
            prompt = {"type": "text", "text": "Mi lavarropas no centrifuga. Ayúdame con el diagnóstico experto."}
            await websocket.send(json.dumps(prompt))
            print("Mensaje de texto enviado")
            time.sleep(1)
            
            # Avisar que terminó el turno
            mensaje = {"type": "end_turn"}
            await websocket.send(json.dumps(mensaje))
            print("Mensaje end_turn enviado")
            
            while True:
                try:
                    # Usamos asyncio.wait_for para no quedarnos colgados eternamente
                    response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    
                    if isinstance(response, str):
                        try:
                            data = json.loads(response)
                            print(f"\nRECIBIDO JSON: {data}")
                            if data.get("type") == "tool_call" and data.get("name") == "consultar_orquestador_reparaciones":
                                print("\n\n>>> 🛠️ EL SERVIDOR WS INVOCÓ LA HERRAMIENTA EXITOSAMENTE <<<")
                                break
                        except json.JSONDecodeError:
                            print(f"RECIBIDO TEXTO: {response}")
                    else:
                        print(f"RECIBIDO BINARIO (Audio): {len(response)} bytes")
                        
                except asyncio.TimeoutError:
                    print("\nTimeout esperando respuesta del servidor")
                    break
                    
    except Exception as e:
        print(f"Error de conexión: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
