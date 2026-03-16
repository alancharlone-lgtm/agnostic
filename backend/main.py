import os
import json
import asyncio
import base64
import io
from PIL import Image
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi import Request
from dotenv import load_dotenv
from typing import Any
from py_schemas import ResidentialAgentRequest
from prompts import RESIDENTIAL_PROMPT, LEARNING_PROMPT
import httpx
import logging

# Configurar logging global
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agnostic")

# Load env variables (for gemini API key)
import sys

# Ensure Windows terminal doesn't crash with emojis or special characters
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

app = FastAPI(title="Agnostic API", description="Backend for Agnostic App using Gemini Live")

from google import genai
from google.genai import types
from adk_agents import root_agent as repairs_root_agent
from adk_universal_mentor import root_agent as mentor_root_agent
from adk_direct_repair import root_agent as direct_repair_root_agent
from adk_vision_precision import root_agent as vision_precision_root_agent


# =============================================================================
# TRIPLE-LANE API ISOLATION
# Creamos 3 clientes separados. Si existen claves específicas en .env, las usa.
# Si no, usa la principal, pero al ser instancias diferentes, aíslan los hilos.
# =============================================================================
# explicit keys or env variables
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")

client_live = genai.Client(api_key=GEMINI_API_KEY)
client_safety = genai.Client(api_key=GEMINI_API_KEY)
client_vision = genai.Client(api_key=GEMINI_API_KEY)

# Flash model for parallel REST agents
GEMINI_FLASH_MODEL = "gemini-3.1-flash-lite-preview"

# =============================================================================
# CONNECTION MANAGER — El Cruce de Caminos entre REST y WebSocket
# =============================================================================
def resize_image(image_bytes: bytes, max_size: int = 1024) -> bytes:
    """Resize image to max_size while maintaining aspect ratio and compress."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Maintain aspect ratio
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert to RGB if necessary (e.g. for RGBA)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()
    except Exception as e:
        print(f"❌ Error compressing image: {e}")
        return image_bytes

class ConnectionManager:
    """
    Registra todas las sesiones WebSocket activas por user_id.
    Permite que endpoints REST (ej. /api/seguridad/frame) inyecten
    mensajes en sesiones Gemini Live activas sin interrumpir el flujo.
    """
    def __init__(self):
        # user_id -> {"websocket": WS, "gemini_session": session, "context": {}}
        self.active_sessions: dict = {}

    def register(self, user_id: str, websocket: WebSocket, gemini_session):
        self.active_sessions[user_id] = {
            "websocket": websocket,
            "gemini_session": gemini_session,
            "context": {},
            "latest_frame": None
        }
        print(f"DEBUG CM: Registered session for user '{user_id}'")

    def unregister(self, user_id: str):
        self.active_sessions.pop(user_id, None)
        print(f"DEBUG CM: Unregistered session for user '{user_id}'")

    def store_context(self, user_id: str, key: str, value: Any):
        """Stores a key-value pair in a specific user's session context."""
        session_data = self.active_sessions.get(user_id)
        if session_data:
            if "context" not in session_data:
                session_data["context"] = {}
            session_data["context"][key] = value
            print(f"DEBUG CM: stored context for '{user_id}': {key}=<{type(value).__name__}>")
        else:
            print(f"DEBUG CM WARNING: Cannot store context, session not found for user '{user_id}'")

    async def inject_alert(self, user_id: str, alert_text: str):
        """🚨 Inyecta una ALERTA DE SEGURIDAD con BARGE-IN verbal real."""
        session_data = self.active_sessions.get(user_id)
        if not session_data:
            print(f"DEBUG CM: No active session for user '{user_id}' to inject alert.")
            return
        gemini_session = session_data["gemini_session"]
        ws = session_data["websocket"]
        
        barge_in_message = (
            f"ALERTA DE SEGURIDAD URGENTE. "
            f"Dejá de hablar y decí en voz alta al técnico: {alert_text}. "
            f"Es crítico. Hablá YA."
        )
        try:
            await gemini_session.send(input=barge_in_message, end_of_turn=True)
            print(f"🚨 BARGE-IN SENT: '{alert_text}'")
        except Exception as e:
            print(f"🚨 BARGE-IN ERROR: {e}")
        
        await ws.send_json({"type": "safety_alert", "message": alert_text})
        print(f"🚨 BARGE-IN: Alert injected for '{user_id}': {alert_text}")

    async def inject_context(self, user_id: str, key: str, value: Any):
        """📚 Guarda silenciosamente datos en la recámara del Orquestador (SIN hablarle)."""
        session_data = self.active_sessions.get(user_id)
        if not session_data:
            return
        if "context" not in session_data:
            session_data["context"] = {}
        session_data["context"][key] = value
        print(f"📚 CM: Context stored for '{user_id}': {key} = {str(value)[:80]}...")

    async def emit_telemetry(self, user_id: str, event: str, agent: str, status: str, detail: str = "", duration_ms: int = 0):
        """📊 Emite un evento de telemetría al frontend Flutter para el Judge Mode overlay."""
        session_data = self.active_sessions.get(user_id)
        if not session_data:
            return
        ws = session_data.get("websocket")
        if ws is None:
            return
        import time
        payload = {
            "type": "telemetry",
            "event": event,          # "tool_start", "tool_end", "tool_error", "rag_hit", "firestore_read"
            "agent": agent,          # "Reparaciones", "Logística", "RAG", "Eagle Eye", etc.
            "status": status,        # "running", "done", "error"
            "detail": detail,        # Extra info (ej: "3 resultados encontrados")
            "duration_ms": duration_ms,
            "timestamp": int(time.time() * 1000),
        }
        try:
            await ws.send_json(payload)
        except Exception:
            pass  # Silently ignore if WS is closed

# Instancia global — compartida entre todos los endpoints
manager = ConnectionManager()

# Global buffer for latest frames (survives 1011 errors)
_global_latest_frames = {}

def log_vision_debug(message: str):
    """Helper to log vision-related debug info to a persistent file."""
    try:
        with open("debug_vision.log", "a", encoding="utf-8") as f:
            from datetime import datetime
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except:
        pass

@app.get("/")
def read_root():
    return {"message": "Agnostic API is running"}

# --- TOOL IMPLEMENTATIONS ---

async def safety_guardian_agent(machine: str = "Desconocida", task: str = "general", _frame_snapshot: bytes = None, **kwargs) -> dict:
    """
    Agente de Seguridad Multimodal y General.
    Analiza una imagen usando Gemini 2.5 Flash para confirmar que los riesgos de la tarea están mitigados.
    """
    
    # 1. Sin captura visual: Exigimos una foto para avanzar.
    if not _frame_snapshot:
        return {
            "status": "REQUIERE_EVIDENCIA_VISUAL",
            "protocolo_agil_obligatorio": "El técnico debe enfocar su cámara hacia el dispositivo principal de seguridad.",
            "medida_bloqueante": "NUNCA CREAS EN LA PALABRA DEL TÉCNICO ALAN. Es OBLIGATORIO que él enfoque la cámara al dispositivo de seguridad, y cuando lo haga, LLAMA OTRA VEZ A ESTA HERRAMIENTA. Hasta recibir APROBADO, NO le des instrucciones técnicas de reparación.",
            "lo_que_debes_decir_al_tecnico": f"Alan, veo que estás en {machine}, pero no confío sólo en tu palabra por seguridad. Necesito que enfoques la térmica, válvula o traba de seguridad DIRECTAMENTE con la cámara y me avises así la reviso."
        }
        
    # 2. Con captura visual: Invocamos a Gemini Flash de manera asíncrona.
    try:
        from google.genai import types
        # Convertimos los bytes a una imagen PIL
        image_stream = io.BytesIO(_frame_snapshot)
        pil_img = Image.open(image_stream)
        
        # Prompt generalista de mitigación de riesgo
        audit_prompt = f"""
        Eres un Auditor de Seguridad Industrial/Residencial estricto pero práctico.
        La tarea es: "{task}" en la máquina/equipo: "{machine}".
        
        Misión: Analizar esta imagen para confirmar si la MEDIDA DE SEGURIDAD obligatoria (térmica, llave de paso, traba) se cumple VISUALMENTE.
        
        CRÍTICO: Las cámaras portátiles envían fotos constantemente. Si en esta imagen NO logras identificar claramente un tablero eléctrico, una válvula, una palanca de máquina, o el equipo de seguridad correspondiente a la tarea, DEBES EXIGIR REUBICAR LA CÁMARA.
        
        RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO CON ESTE FORMATO:
        {{
            "status": "APROBADO" | "BLOQUEADO" | "REQUIERE_EVIDENCIA_VISUAL",
            "evidencia_visual": "Qué ves en la foto exactamente.",
            "ppe_exigido": "Si aprobase, indica 'Precaución normal'. Caso contrario, 'Peligro latente'.",
            "lo_que_debes_decir_al_tecnico": "Instrucción final para el orquestador Gemini Live. Si el status NO es APROBADO, el orquestador tiene TERMINANTEMENTE PROHIBIDO confiar en la palabra del usuario y debe detener toda asistencia. Ej:"REQUIERE_EVIDENCIA_VISUAL": 'Alan, sigo sin ver la llave térmica. Mostramela bien claro en la cámara y avisame.'"
        }}
        """
        
        response = await client_safety.aio.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[audit_prompt, pil_img],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        # Parsear la respuesta JSON del modelo
        import json
        audit_result = json.loads(response.text)
        return audit_result

    except Exception as e:
        import traceback
        print(f"🔥 ERROR en safety_guardian_agent audit: {e}")
        traceback.print_exc()
        return {
            "status": "BLOQUEADO_POR_ERROR_SISTEMA",
            "medida_bloqueante": "Error técnico al procesar la imagen de seguridad. Aplica el protocolo estricto manual.",
            "error_interno": str(e)
        }

async def control_phone_flashlight(action: str = "on", user_id: str = "default", **kwargs) -> dict:
    """
    Controla el flash/linterna del teléfono del técnico.
    Úsalo si detectas que la imagen de la cámara está muy oscura o si el técnico lo pide.
    action: 'on' para encender, 'off' para apagar.
    """
    session_data = manager.active_sessions.get(user_id)
    if not session_data:
        return {"error": "No hay sesión activa para controlar el flash"}
    
    ws = session_data["websocket"]
    status_bool = action.lower() == "on"
    
    await ws.send_json({
        "type": "flashlight",
        "action": action.lower()
    })
    
    print(f"🔦 Flashlight command sent to {user_id}: {action.upper()}")
    return {"status": f"Linterna del teléfono {action.upper()}"}


async def handle_vision_result(tipo: str = "", marca: str = "", modelo: str = "", fallas_comunes: list = None, componentes: dict = None, user_id: str = "default", **kwargs) -> dict:
    """Tool interna que Gemini llama para guardar en memoria lo que acaba de ver."""
    result_texto = (
        f"ARTEFACTO IDENTIFICADO VISUALMENTE: {tipo} {marca} {modelo}. "
        f"Fallas más comunes a tener en cuenta: {', '.join(fallas_comunes or [])}."
    )
    print(f"👁️ Vision Agent (Live Tool): {result_texto}")
    
    # Inyectamos en el contexto
    await manager.inject_context(user_id, f"vision_{tipo}", result_texto)
    if componentes:
        await manager.inject_context(user_id, "vision_componentes", componentes)
        
    return {"status": "Guardado en memoria silenciosa", "scheduling": "SILENT"}

async def consultar_vision_precision(componente: str, _frame_snapshot: bytes = None, user_id: str = "default", **kwargs) -> dict:
    """
    Agente Especialista de Visión de Alta Precisión (EAGLE EYE).
    Analiza un frame estático para obtener coordenadas milimétricas de un componente.
    """
    msg_start = f"🚀 [EAGLE EYE] Iniciando tarea para: '{componente}' (User: {user_id})"
    print(msg_start)
    log_vision_debug(msg_start)
    try:
        frame_bytes = _frame_snapshot
        if not frame_bytes:
            session_data = manager.active_sessions.get(user_id)
            frame_bytes = session_data.get("latest_frame") if session_data else None
            if frame_bytes:
                print(f"🚀 [EAGLE EYE] Frame obtenido de session_data ({len(frame_bytes)} bytes)")
        
        if not frame_bytes:
            frame_bytes = _global_latest_frames.get(user_id)
            if frame_bytes:
                print(f"🚀 [EAGLE EYE] Frame obtenido de global_buffer ({len(frame_bytes)} bytes)")

        if not frame_bytes:
            logger.warning("[EAGLE EYE] No frame available for analysis")
            return {
                "error": "No hay frame disponible",
                "mensaje_voz": "No pude ver bien la cámara. Asegurate de que esté encendida y apuntando al equipo."
            }
            
        logger.info("[EAGLE EYE] Consultando agente EAGLE EYE vía client directo para: %s", componente)
        
        prompt_text = (
            f'Localiza con máxima precisión el componente: "{componente}".\n'
            'TU MISIÓN: Localiza el componente con precisión quirúrgica.\n'
            'El recuadro DEBE ser lo más ceñido posible a los bordes reales del objeto.\n'
            'Devuelve los resultados en una escala normalizada de 0 a 1000.\n'
            'RESPONDE ÚNICAMENTE CON UN JSON VÁLIDO CON ESTE FORMATO:\n'
            '{"componente": "nombre", "coordenadas": [ymin, xmin, ymax, xmax]}'
        )
        
        from google.genai import types
        import io
        from PIL import Image
        
        image_stream = io.BytesIO(frame_bytes)
        pil_img = Image.open(image_stream)
        
        # client_safety is the global genai.Client for non-live API calls
        response = await client_safety.aio.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=[prompt_text, pil_img],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        final_text = response.text
        print(f"[EAGLE EYE] Raw response: {final_text[:200]}")
        
        import json
        import re
        json_match = re.search(r'\{.*\}', final_text, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "coordenadas" in data:
                    coords = data["coordenadas"]
                    print(f"[EAGLE EYE] ✅ Coordenadas encontradas: {coords}")
                    
                    session_data = manager.active_sessions.get(user_id)
                    if session_data:
                         ws = session_data["websocket"]
                         # 🛠️ CORRECCIÓN DEFINITIVA: El frontend transpone X e Y.
                         # Swapeamos X e Y en el backend para cancelar la transposición del frontend.
                         ymin, xmin, ymax, xmax = coords
                         fixed_coords = [xmin, ymin, xmax, ymax]
                         
                         msg_ws = {
                             "type": "bounding_box",
                             "component": data.get("componente", componente),
                             "coordinates": fixed_coords
                         }
                         print(f"[EAGLE EYE] Sending bounding_box to {user_id}: {coords} → {fixed_coords} (swap applied)")
                         log_vision_debug(f"🚀 [EAGLE EYE] Enviando bounding_box via WS: {msg_ws}")
                         try:
                             await ws.send_json(msg_ws)
                             print("[EAGLE EYE] Bounding box sent to frontend ✅")
                             log_vision_debug("✅ [EAGLE EYE] Mensaje enviado al frontend.")
                         except Exception as ws_err:
                             err_msg = f"[EAGLE EYE] ERROR sending via WS: {ws_err}"
                             print(err_msg)
                             log_vision_debug(err_msg)
                         return {"status": "EXITO"}
                    else:
                        print(f"[EAGLE EYE] No active session found for user '{user_id}'")
                        return {
                            "error": "Sesión no encontrada",
                            "mensaje_voz": "Encontré el componente pero la conexión se interrumpió. Intentá de nuevo."
                        }
                else:
                    print(f"[EAGLE EYE] JSON sin 'coordenadas': {data}")
                    return {
                        "error": "Sin coordenadas en respuesta",
                        "mensaje_voz": f"No pude localizar el {componente} con precisión. Intentá acercar la cámara."
                    }
            except Exception as e:
                print(f"[EAGLE EYE] JSON parse error: {e}")
                return {
                    "error": f"Error parseando respuesta: {e}",
                    "mensaje_voz": "Tuve un problema procesando la imagen. Intentá de nuevo."
                }
        else:
            print("[EAGLE EYE] No JSON found in response")
            return {
                "error": "EAGLE EYE falló",
                "raw_response": final_text,
                "mensaje_voz": f"No pude identificar el {componente} en la imagen. Verificá que la cámara esté enfocada."
            }
    except Exception as e:
        import traceback
        print(f"[EAGLE EYE] Critical crash: {e}")
        traceback.print_exc()
        return {
            "error": str(e),
            "mensaje_voz": "Ocurrió un error en el sistema de visión. El resto de la asistencia sigue disponible."
        }

async def mostrar_componente(componente: str, user_id: str = "default", _frame_snapshot: bytes = None, **kwargs) -> dict:
    """
    Dibuja un recuadro (bounding box) en la pantalla del usuario.
    Se invoca EXCLUSIVAMENTE al AGENTE ESPECIALISTA (Eagle Eye) para buscar con precisión extrema.
    """
    session_data = manager.active_sessions.get(user_id)
    if not session_data:
         return {"error": "No hay sesión activa para mostrar componentes"}
    
    # CASO ÚNICO: Lanzamos el Agente Especialista en segundo plano siempre.
    print(f"[EAGLE EYE] Launching specialist agent for '{componente}' (user: {user_id})")
    log_vision_debug(f"Lanzando Eagle Eye especialista para '{componente}'...")
    asyncio.create_task(consultar_vision_precision(componente, _frame_snapshot, user_id))
    
    return {
        "status": "BUSCANDO CON PRECISIÓN", 
        "result": f"Iniciando escaneo de alta precisión para '{componente}' con el agente Eagle Eye. El recuadro aparecerá en pantalla en unos segundos.",
        "scheduling": "SILENT"
    }

# --- RAG: HERRAMIENTAS DE CONOCIMIENTO COLECTIVO ---

async def consultar_experiencias_tecnicas(sintoma: str = "", categoria: str = "", user_id: str = "default", **kwargs) -> dict:
    """
    Busca en la base de conocimiento colectiva de técnicos experiencias
    previas similares al problema actual. Retorna los 3 casos más relevantes.
    """
    from rag_knowledge_base import search_similar_repairs
    
    query = sintoma
    if categoria:
        query = f"{categoria}: {sintoma}"
    
    print(f"📚 [RAG TOOL] Consultando experiencias para: '{query[:80]}...'")
    
    try:
        result = await search_similar_repairs(query, top_k=3)
        
        if result["status"] == "ENCONTRADO":
            # Inyectar en el contexto de la sesión para que Gemini Live lo tenga
            session_data = manager.active_sessions.get(user_id)
            if session_data:
                await manager.inject_context(user_id, "experiencias_previas", result["contexto_formateado"])
            
            return {
                "status": "ENCONTRADO",
                "experiencias": result["contexto_formateado"],
                "cantidad": len(result["resultados"]),
            }
        else:
            return {
                "status": result["status"],
                "experiencias": result["contexto_formateado"],
            }
    except Exception as e:
        print(f"📚 [RAG TOOL] ❌ Error: {e}")
        return {"status": "ERROR", "error": str(e)}


async def guardar_experiencia_reparacion(transcript: str = "", user_id: str = "default", **kwargs) -> dict:
    """
    Guarda la experiencia de una reparación exitosa en la base de conocimiento colectiva.
    Extrae los datos clave de la transcripción usando Gemini Flash.
    """
    from rag_knowledge_base import extract_and_save_repair
    
    if not transcript or len(transcript.strip()) < 50:
        return {"status": "SKIP", "reason": "Transcript demasiado corto para extraer datos útiles."}
    
    print(f"📚 [RAG TOOL] Guardando experiencia de reparación ({len(transcript)} chars)...")
    
    try:
        result = await extract_and_save_repair(transcript)
        return result
    except Exception as e:
        print(f"📚 [RAG TOOL] ❌ Error guardando: {e}")
        return {"status": "ERROR", "error": str(e)}


async def generar_guia_visual_ensamblaje(tarea: str = "Conexión de componente", contexto: str = "Reparación general", detalles_tecnicos: str = "", user_id: str = "default", _frame_snapshot: bytes = None, **kwargs) -> dict:
    """
    Toma el último frame de la cámara e invoca al nuevo Agente de Guía Visual ADK.
    Este agente coordina a especialistas (electricidad/refrigeración) y al director visual
    para generar una imagen editada profesional a través del servidor MCP.
    _frame_snapshot: si es provisto, se usa en lugar de leer del ConnectionManager (evita race condition en tasks de fondo).
    """
    print(f"🎨 Invocando AGENTE ADK de Guía Visual - Tarea: {tarea} en: {contexto}")
    print(f"🎨 DEBUG sesiones activas: {list(manager.active_sessions.keys())}")
    
    # PRIORIDAD 1: Si el caller ya capturó el frame en el momento del dispatch, lo usamos directamente.
    # Esto evita la race condition donde el task asíncrono se ejecuta después de que la sesión cambia.
    if _frame_snapshot:
        frame_bytes = _frame_snapshot
        print(f"🎨 DEBUG: Usando frame snapshot pre-capturado ({len(frame_bytes)} bytes)")
    else:
        # PRIORIDAD 2: Fallback — leer del ConnectionManager
        session_data = manager.active_sessions.get(user_id)
        print(f"🎨 DEBUG: session_data para '{user_id}': {'encontrado' if session_data else 'NO ENCONTRADO'}")
        if session_data:
            print(f"🎨 DEBUG: latest_frame en session: {'presente' if session_data.get('latest_frame') else 'AUSENTE'}")
        if session_data and session_data.get("latest_frame"):
            frame_bytes = session_data["latest_frame"]
        else:
            # PRIORIDAD 3: Buffer global — sobrevive a reinicios de sesión por error 1011
            frame_bytes = _global_latest_frames.get(user_id)
            if frame_bytes:
                print(f"🎨 GLOBAL BUFFER FALLBACK: Usando frame del buffer global para user '{user_id}' ({len(frame_bytes)} bytes)")
            else:
                return {"error": "No hay un frame de cámara reciente para analizar. El agente visual no puede generar la guía sin una imagen de la cámara."}
    frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')

    # Eliminamos el base64 del texto para que el LLM no intente procesarlo como string
    query_text = (
        f"Analizá esta imagen y generá la guía visual de ensamblaje para:\n"
        f"TAREA: {tarea}\n"
        f"CONTEXTO: {contexto}\n"
        f"DETALLES: {detalles_tecnicos or 'No especificados'}\n\n"
        "INSTRUCCIÓN: El especialista técnico analizará la imagen y luego el Director Visual "
        "llamará a 'generar_guia_visual_nanobanana' para renderizar el resultado."
    )
    
    try:
        from google.adk.apps import App
        from google.adk.runners import Runner
        from google.adk.sessions.in_memory_session_service import InMemorySessionService
        from google.genai import types as genai_types
        import httpx
        import json as _json

        # --- PROXY TOOL LOCAL ---
        # Definida aquí para tener acceso a frame_bytes sin pasarlo por el LLM
        async def generar_guia_visual_nanobanana(prompt_tecnico: str) -> str:
            """
            Llamada directa al servidor MCP de Nano Banana con la foto original completa.
            """
            print(f"🖌️ PROXY TOOL: Llamada iniciada para técnico '{user_id}'")
            print(f"🖌️ PROXY TOOL: Prompt recibido: {prompt_tecnico[:500]}...")
            
            # API Key centralizada
            api_key = GEMINI_API_KEY
            gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={api_key}"
            
            # Snapshot de seguridad del frame enviado (para debugging post-mortem)
            try:
                with open(f"debug_frame_sent_{user_id}.jpg", "wb") as f:
                    f.write(frame_bytes)
            except:
                pass

            img_b64 = base64.b64encode(frame_bytes).decode('utf-8')
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt_tecnico},
                        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
                    ]
                }],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"]
                },
                "safetySettings": [
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
                ]
            }
            
            try:
                print(f"🖌️ PROXY TOOL: Enviando {len(img_b64)} bytes de base64 a Gemini Image API...")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(gemini_url, json=payload)
                    
                    if resp.status_code != 200:
                        err_msg = f"Gemini API Error {resp.status_code}: {resp.text[:1000]}"
                        print(f"🖌️ PROXY TOOL ERROR: {err_msg}")
                        return f"Error al generar imagen: {err_msg}"
                    
                    res_data = resp.json()
                    print(f"🖌️ PROXY TOOL: Respuesta recibida exitosamente (status 200)")
                    
                    candidate = res_data.get("candidates", [{}])[0]
                    parts = candidate.get("content", {}).get("parts", [])
                    res_img_b64 = None
                    text_response = ""
                    
                    for part in parts:
                        if "text" in part:
                            text_response += part["text"]
                        if "inlineData" in part:
                            res_img_b64 = part["inlineData"]["data"]
                    
                    if res_img_b64:
                        print(f"🖌️ PROXY TOOL SUCCESS: ¡Imagen editada de {len(res_img_b64)} bytes recibida!")
                        session_data = manager.active_sessions.get(user_id)
                        if session_data:
                             print(f"🖌️ PROXY TOOL: Despachando imagen vía WebSocket a '{user_id}'...")
                             await session_data["websocket"].send_json({
                                 "type": "visual_guide_image",
                                 "image": res_img_b64,
                                 "text": text_response or "Guía visual generada."
                             })
                             return "Guía visual generada y enviada exitosamente al técnico."
                        else:
                            print(f"🖌️ PROXY TOOL WARNING: No se encontró sesión activa para '{user_id}' al intentar enviar la imagen.")
                            return "Imagen generada satisfactoriamente, pero la sesión técnica se cerró antes de enviarla."
                    else:
                        print("🖌️ PROXY TOOL: Gemini no devolvió 'inlineData' (imagen). Texto recibido: " + text_response[:200])
                        return f"El modelo analizó el caso pero no generó una imagen editada. Razonamiento: {text_response[:300]}"
            except Exception as e_proxy:
                print(f"🖌️ PROXY TOOL CRITICAL ERROR: {str(e_proxy)}")
                import traceback
                traceback.print_exc()
                return f"Error crítico en el generador de imágenes: {str(e_proxy)}"

        from adk_vision_guide_v2 import get_vision_agent
        vision_root_agent = get_vision_agent(drawing_tool=generar_guia_visual_nanobanana)
        
        # Enviamos Part de bytes (multimodal Nativo)
        msg = genai_types.Content(
            role="user", 
            parts=[
                genai_types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg"),
                genai_types.Part.from_text(text=query_text)
            ]
        )

        app = App(name="vision_guide_app", root_agent=vision_root_agent)
        runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)
        
        final_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=f"vision_{user_id}", new_message=msg):
            if hasattr(event, "content") and getattr(event, "content", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_text += part.text
        
        return {"result": final_text or "Guía técnica visual generada y enviada."}
        
    except Exception as e:
        print(f"🎨 ERROR en Agente ADK de Visión: {e}")
        import traceback
        traceback.print_exc()
        return {"error": "error_tecnico_agente", "message": str(e)}



# =============================================================================
# WRAPPER FUNCTIONS FOR ADK AGENTS (invoked from TOOL_MAP)
# =============================================================================

async def consultar_orquestador_reparaciones(query: str = "", user_id: str = "default", **kwargs) -> dict:
    """Wrapper: invoca el Orquestador Principal de Reparaciones (adk_agents.py)."""
    from google.adk.runners import Runner
    from google.adk.apps import App
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types as genai_types
    from adk_agents import get_repairs_agent

    try:
        agent = get_repairs_agent()
        # Enrich query with RAG experiences if available
        rag_context = ""
        try:
            rag_result = await consultar_experiencias_tecnicas(sintoma=query, user_id=user_id)
            if rag_result.get("experiencias"):
                rag_context = "\n\nEXPERIENCIAS PREVIAS DE OTROS TECNICOS:\n" + str(rag_result["experiencias"])
        except Exception:
            pass
        
        full_query = query + rag_context
        msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=full_query)])
        app = App(name="repairs_app", root_agent=agent)
        runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)
        
        final_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=f"repairs_{user_id}", new_message=msg):
            if hasattr(event, "content") and getattr(event, "content", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_text += part.text

        return {"result": final_text or "El orquestador no devolvio respuesta."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "result": f"Error en el orquestador de reparaciones: {e}"}


async def consultar_logistica_repuestos(repuesto: str = "", marca: str = "", equipo: str = "", ubicacion_tecnico: str = "", user_id: str = "default", **kwargs) -> dict:
    """Wrapper: invoca el Coordinador de Logistica (adk_logistica.py)."""
    import re
    from google.adk.runners import Runner
    from google.adk.apps import App
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types as genai_types
    from adk_logistica import get_logistics_agent

    try:
        # Recuperar GPS de la sesion si no viene explicito
        if not ubicacion_tecnico or ubicacion_tecnico == "Desconocida":
            sess = manager.active_sessions.get(user_id, {})
            ctx = sess.get("context", {})
            ubicacion_tecnico = ctx.get("gps_location", "Desconocida")

        query = f"Repuesto: {repuesto}. Marca: {marca}. Equipo: {equipo}. Ubicacion GPS del tecnico: {ubicacion_tecnico}."
        agent = get_logistics_agent()
        msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=query)])
        app = App(name="logistics_app", root_agent=agent)
        runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)

        final_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=f"logistics_{user_id}", new_message=msg):
            if hasattr(event, "content") and getattr(event, "content", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_text += part.text

        # Extraer links de MercadoLibre del texto generado por el agente
        ml_links = re.findall(r'https?://(?:www\.)?mercadolibre\.com[^\s\)\]\,\"\'<>]+', final_text)
        # También buscar links de articulo cortos tipo meli.com
        ml_links += re.findall(r'https?://(?:www\.)?meli\.com[^\s\)\]\,\"\'<>]+', final_text)
        # Limpiar duplicados manteniendo orden
        seen = set()
        unique_links = []
        for l in ml_links:
            if l not in seen:
                seen.add(l)
                unique_links.append(l)

        result = {"result": final_text or "Sin resultados de logistica."}
        if unique_links:
            result["parts_links"] = unique_links[:3]  # máximo 3 links para la UI
            print(f"🛒 LOGISTICA: {len(unique_links)} links ML encontrados → enviando a Flutter: {unique_links[:3]}")

        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "result": f"Error en logistica: {e}"}



async def consultar_especialistas_hogar(tarea_usuario: str = "", user_id: str = "default", **kwargs) -> dict:
    """Wrapper: invoca el Orquestador Maestro Pedagógico (adk_universal_mentor.py) y devuelve el Dossier completo."""
    from google.adk.runners import Runner
    from google.adk.apps import App
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types as genai_types
    from adk_universal_mentor import root_agent as mentor_root_agent

    try:
        # Enrich with RAG
        rag_context = ""
        try:
            rag_result = await consultar_experiencias_tecnicas(sintoma=tarea_usuario, user_id=user_id)
            if rag_result.get("experiencias"):
                rag_context = "\n\nEXPERIENCIAS PREVIAS DEL EQUIPO:\n" + str(rag_result["experiencias"])
        except Exception:
            pass

        query = f"Tarea del usuario: {tarea_usuario}{rag_context}"
        msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=query)])
        app = App(name="mentor_app", root_agent=mentor_root_agent)
        runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)

        final_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=f"mentor_{user_id}", new_message=msg):
            if hasattr(event, "content") and getattr(event, "content", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_text += part.text

        return {"result": final_text or "El Orquestador no devolvió un Dossier."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "result": f"Error en especialistas hogar: {e}"}


async def consultar_reparacion_directa(tarea_usuario: str = "", user_id: str = "default", **kwargs) -> dict:
    """Wrapper: invoca el agente de Reparacion Directa (adk_direct_repair.py)."""
    from google.adk.runners import Runner
    from google.adk.apps import App
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types as genai_types
    from adk_direct_repair import root_agent as direct_repair_root

    try:
        # Enrich with RAG
        rag_context = ""
        try:
            rag_result = await consultar_experiencias_tecnicas(sintoma=tarea_usuario, user_id=user_id)
            if rag_result.get("experiencias"):
                rag_context = "\n\nEXPERIENCIAS PREVIAS:\n" + str(rag_result["experiencias"])
        except Exception:
            pass

        query = f"Tarea: {tarea_usuario}{rag_context}"
        msg = genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=query)])
        app = App(name="direct_repair_app", root_agent=direct_repair_root)
        runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)

        final_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=f"direct_{user_id}", new_message=msg):
            if hasattr(event, "content") and getattr(event, "content", None):
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final_text += part.text

        return {"result": final_text or "Sin respuesta del agente de reparacion directa."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "result": f"Error en reparacion directa: {e}"}


async def tutor_herramientas(tarea: str = "", user_id: str = "default", **kwargs) -> dict:
    """Indica que herramientas fisicas necesita el usuario para la tarea."""
    tool_mapping = {
        "electri": ["Tester multimetro", "Destornillador philips", "Destornillador plano", "Pinza pelacables", "Cinta aisladora"],
        "plomer": ["Llave stillson", "Cinta teflon", "Sellador de roscas", "Llave francesa"],
        "gas": ["Detector de fugas", "Llave para gas", "Jabon liquido (prueba de burbujas)"],
        "aire": ["Juego de llaves Allen", "Manometro de presion", "Termometro digital"],
        "heladera": ["Tester multimetro", "Destornillador philips", "Pinza de punta"],
        "lavarrop": ["Destornillador philips", "Pinza", "Tester multimetro", "Llave 10mm"],
    }
    
    herramientas = ["Destornillador philips", "Tester multimetro", "Pinza", "Linterna"]
    tarea_lower = tarea.lower()
    for key, tools in tool_mapping.items():
        if key in tarea_lower:
            herramientas = tools
            break
    
    return {
        "tarea": tarea,
        "herramientas_necesarias": herramientas,
        "instruccion": f"Para la tarea '{tarea}', vas a necesitar: {', '.join(herramientas)}. Busca estas herramientas en tu caja antes de empezar."
    }


async def evaluacion_paso_a_paso(accion: str = "", user_id: str = "default", _frame_snapshot: bytes = None, **kwargs) -> dict:
    """Evalua visualmente si el usuario completo un paso correctamente."""
    if not _frame_snapshot:
        return {
            "status": "REQUIERE_IMAGEN",
            "instruccion": "Necesito ver lo que hiciste. Enfoca la camara al area donde trabajaste para poder evaluar."
        }
    
    try:
        from google.genai import types
        image_stream = io.BytesIO(_frame_snapshot)
        pil_img = Image.open(image_stream)
        
        eval_prompt = f"""
        Eres un instructor tecnico evaluando el trabajo de un aprendiz.
        La accion que debe haber completado es: "{accion}"
        
        Mira esta imagen y evalua:
        1. Se ve evidencia de que la accion fue realizada?
        2. Se hizo correctamente o hay errores visibles?
        3. Hay riesgos de seguridad visibles?
        
        Responde en JSON:
        {{"status": "CORRECTO" | "INCORRECTO" | "NO_VISIBLE",
          "evaluacion": "descripcion de lo que ves",
          "siguiente_paso": "que debe hacer ahora"}}
        """
        
        response = await client_vision.aio.models.generate_content(
            model=GEMINI_FLASH_MODEL,
            contents=[eval_prompt, pil_img],
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        import json
        return json.loads(response.text)
    except Exception as e:
        return {"status": "ERROR", "evaluacion": str(e)}


async def parts_prefetch_agent(brand: str = "", appliance_type: str = "", location: str = "", part_list: list = None, user_id: str = "default", **kwargs) -> dict:
    """Pre-carga precios y disponibilidad de repuestos en segundo plano."""
    if not part_list:
        return {"status": "sin_repuestos", "message": "No se especificaron repuestos para buscar."}
    
    results = []
    for part in part_list:
        results.append({
            "repuesto": part,
            "marca": brand,
            "status": "prefetch_lanzado",
            "nota": f"Búsqueda iniciada para '{part}' de {brand} cerca de {location}."
        })
    
    return {
        "status": "prefetch_completado",
        "equipo": appliance_type,
        "repuestos_buscados": results,
        "message": f"Pre-carga de {len(results)} repuestos iniciada."
    }


def create_work_order(machine: str = "Desconocida", issue: str = "", part_needed: str = "None", **kwargs) -> dict:
    """Mock: genera una orden de trabajo en el sistema ERP."""
    ticket_id = f"WO-{hash(machine + issue) % 10000}"
    status = "Abierta (Pendiente Repuesto)" if part_needed != "None" else "Cerrada"
    return {
        "work_order_id": ticket_id,
        "machine": machine,
        "issue_description": issue,
        "required_parts": part_needed,
        "status": status,
        "message": f"Orden de trabajo {ticket_id} generada."
    }


# =============================================================================
# TOOL_MAP: Mapea nombre de herramienta -> funcion Python
# =============================================================================
TOOL_MAP = {
    "safety_guardian_agent": safety_guardian_agent,
    "handle_vision_result": handle_vision_result,
    "mostrar_componente": mostrar_componente,
    "control_phone_flashlight": control_phone_flashlight,
    "generar_guia_visual_ensamblaje": generar_guia_visual_ensamblaje,
    "consultar_orquestador_reparaciones": consultar_orquestador_reparaciones,
    "consultar_logistica_repuestos": consultar_logistica_repuestos,
    "consultar_experiencias_tecnicas": consultar_experiencias_tecnicas,
    "guardar_experiencia_reparacion": guardar_experiencia_reparacion,
    "consultar_especialistas_hogar": consultar_especialistas_hogar,
    "consultar_reparacion_directa": consultar_reparacion_directa,
    "tutor_herramientas": tutor_herramientas,
    "evaluacion_paso_a_paso": evaluacion_paso_a_paso,
    "create_work_order": create_work_order,
    "parts_prefetch_agent": parts_prefetch_agent,
}

# =============================================================================
# NON_BLOCKING_TOOLS: Herramientas que corren en segundo plano (audio sigue)
# =============================================================================
NON_BLOCKING_TOOLS = {
    "safety_guardian_agent",
    "handle_vision_result",
    "mostrar_componente",
    "generar_guia_visual_ensamblaje",
    "consultar_experiencias_tecnicas",
    "guardar_experiencia_reparacion",
    "parts_prefetch_agent",
    "consultar_orquestador_reparaciones",
    "consultar_logistica_repuestos",
    "consultar_especialistas_hogar",
    "consultar_reparacion_directa",
    "tutor_herramientas",
    "control_phone_flashlight",
    "create_work_order",
}

# =============================================================================
# TOOL_SCHEDULING: Comportamiento de scheduling especial
# =============================================================================
TOOL_SCHEDULING = {
    "safety_guardian_agent": "INTERRUPT",
}


# --- PARALLEL AGENT 1: SAFETY WATCHDOG (NATIVO ASÍNCRONO) ---
async def proactive_vision_loop(session, user_id, mode):
    """
    Envía UN ÚNICO mensaje de activación a Gemini para que salude al técnico.
    Eliminamos los turnos 2A/2B porque cada session.send() adicional
    agrega 1-2 segundos de overhead al inicio (round-trip al modelo).
    La detección visual ocurre de manera natural cuando el técnico habla
    y la cámara envía frames, no necesitamos pre-cargarla.
    """
    print(f"V-LOOP: Iniciando proactive_vision_loop para user {user_id} en modo {mode}")
    
    if mode == "hogar":
        activacion_saludo = (
            "SISTEMA: Nueva sesión iniciada en modo HOGAR. "
            "ACCIÓN OBLIGATORIA: Saluda empáticamente como el Mentor Agnostic. "
            "DEBES preguntarle al usuario de inmediato: '¿Querés que hagamos una Clase de Aprendizaje o prefieres Resolución Directa?' "
            "NO asumas que estamos en un entorno industrial. NO pidas detalles de fallas técnicas hasta que el usuario responda."
        )
    else:
        # Saludo inmediato para Industrial/Residencial
        activacion_saludo = (
            "SISTEMA: Nueva sesión con técnico iniciada. "
            "ACCIÓN: Saludalo de forma breve y empática. "
            "Preguntale qué equipo estamos revisando hoy o cuál es la falla reportada. "
            "IMPORTANTE: Si el técnico ya mencionó una marca y una falla, dispara 'consultar_orquestador_reparaciones' DE INMEDIATO."
        )
    
    try:
        print(f"V-LOOP: Enviando activación de saludo...")
        await session.send(input=activacion_saludo, end_of_turn=True)
    except Exception as e:
        print(f"V-LOOP Error en saludo: {e}")



# --- HYBRID WORKER: CEREBRO PREDICTIVO (Vision-Only + SILENT Injection) ---
async def cerebro_predictivo_worker(session, frame_bytes: bytes, user_id: str):
    """
    Worker Ligero: Solo identifica el aparato y la marca en el primer frame.
    
    FLUJO:
    1. Usa client_vision (carril rápido, REST) para identificar equipo y marca.
    2. Inyecta esa info en Gemini Live SILENCIOSAMENTE para que sepa con
       qué aparato está tratando ANTES de que el técnico hable.
    
    El Orquestador ADK se llama DESPUÉS, cuando Gemini Live tiene:
    equipo + marca + falla_reportada. Lo dispara como NON_BLOCKING, 
    lo que significa que Gemini responde al técnico mientras el ADK trabaja.
    
    COSTO EN LATENCIA DE VOZ: CERO.
    """
    print(f"🔮 CEREBRO PREDICTIVO: Iniciando análisis visual para user '{user_id}'...")

    # ─── PASO 1: Carril Visión (Flash REST) — Identificar equipo y marca ──────
    equipo = "electrodoméstico"
    marca = "marca desconocida"
    try:
        response_vision = await asyncio.to_thread(
            client_vision.models.generate_content,
            model=GEMINI_FLASH_MODEL,
            contents=[
                types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg"),
                types.Part.from_text(text=(
                    "Analiza esta imagen. Identifica el electrodoméstico o equipo visible y su marca. "
                    "Responde ÚNICAMENTE con un JSON válido, sin explicaciones. "
                    "Formato exacto requerido: {\"equipo\": \"nombre del equipo\", \"marca\": \"nombre de la marca\"}. "
                    "Si no puedes identificar alguno, usa el valor \"desconocido\"."
                ))
            ]
        )
        import re, json as _json
        raw_text = response_vision.text.strip()
        # Extraemos el JSON aunque venga con markdown (```json ... ```)
        match = re.search(r"\{.*?\}", raw_text, re.DOTALL)
        if match:
            data = _json.loads(match.group())
            equipo = data.get("equipo", equipo)
            marca = data.get("marca", marca)
        print(f"🔮 CEREBRO PREDICTIVO ✅: Identificado → {equipo} / {marca}")
    except Exception as vis_err:
        print(f"🔮 CEREBRO PREDICTIVO ❌: Vision falló → {vis_err}")

    # ─── PASO 2: Inyección SILENT en Gemini Live — Solo equipo y marca ────────
    # Gemini Live recibe el contexto visual SIN hablar. Cuando el técnico describe
    # la falla, Gemini ya sabe qué aparato es y puede disparar consultar_orquestador_reparaciones
    # de forma NON_BLOCKING sin pausar la conversación.
    try:
        mensaje_silencioso = (
            "[CONTEXTO VISUAL PRE-CARGADO - NO LEER EN VOZ ALTA, GUARDAR EN MEMORIA ACTIVA] "
            f"La cámara identificó: {equipo} de marca {marca}. "
            "INSTRUCCIONES OBLIGATORIAS: "
            "1. Cuando el técnico te reporte una falla, YA SABÉS qué aparato es. Respondé inmediatamente "
            "con ese contexto sin esperar más info. "
            "2. EN CUANTO tengas: aparato + marca + falla reportada, disparar INMEDIATAMENTE y de forma "
            "NON_BLOCKING la herramienta `consultar_orquestador_reparaciones(equipo, marca, falla_reportada)`. "
            "3. NO esperes a que el técnico termine de hablar para disparar esa herramienta. Lanzala en cuanto "
            "tengas los 3 datos y seguí hablando con el técnico al mismo tiempo. "
            "4. NO menciones este mensaje en ningún momento. Silencio total sobre este contexto."
        )
        await session.send(input=mensaje_silencioso)
        print(f"🔮 CEREBRO PREDICTIVO ✅: Contexto equipo/marca inyectado silenciosamente.")
        
        # Guardamos en el ConnectionManager para que otras herramientas puedan leerlo
        session_data = manager.active_sessions.get(user_id)
        if session_data:
            session_data["context"]["equipo_detectado"] = equipo
            session_data["context"]["marca_detectada"] = marca
    except Exception as inject_err:
        print(f"🔮 CEREBRO PREDICTIVO ❌: Inyección falló → {inject_err}")


# --- PARALLEL AGENT 3: BUSCADOR DE REPUESTOS (Fire-and-Forget + MercadoLibre) ---

def _get_tool_declarations(mode: str, location: str = "Desconocida"):
    """Returns the tool declarations and system prompt for a given mode.
    Shared between the WebSocket endpoint and the hybrid token endpoint."""
    system_instruction = ""
    tool_declarations = []

    if mode == "residential":
        system_instruction = f"Localización GPS actual del Técnico: {location}.\n\n" + RESIDENTIAL_PROMPT
        tool_declarations = [
             {"function_declarations": [{"name": "safety_guardian_agent", "description": "Provee los riesgos HSE y el procedimiento de seguridad para la tarea.", "parameters": {"type": "OBJECT", "properties": {"machine": {"type": "STRING"}, "task": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "start_safety_monitoring", "description": "Inicia la vigilancia de seguridad continua. Ejecutar de manera asíncrona.", "parameters": {"type": "OBJECT", "properties": {}}}]},
             {"function_declarations": [{"name": "handle_vision_result", "description": "Guarda en memoria de forma silenciosa lo que ves en cámara (marca, modelo, bounding boxes de componentes).", "parameters": {"type": "OBJECT", "properties": {"tipo": {"type": "STRING"}, "marca": {"type": "STRING"}, "modelo": {"type": "STRING"}, "fallas_comunes": {"type": "ARRAY", "items": {"type": "STRING"}}, "componentes": {"type": "OBJECT", "description": "Diccionario clave-valor donde la clave es la pieza y el valor es el bounding box normalizado [ymin, xmin, ymax, xmax]. Ej: {'rele': [200, 100, 300, 400]}."}}}}]},
             {"function_declarations": [{"name": "mostrar_componente", "description": "Dibuja un bounding box resaltando el componente en la pantalla del técnico. Úsalo PROACTIVAMENTE cuando quieras señalar algo visible en la cámara. Si no conoces la ubicación exacta, omite 'coordenadas' para activar al especialista de alta precisión.", "parameters": {"type": "OBJECT", "properties": {"componente": {"type": "STRING"}, "coordenadas": {"type": "ARRAY", "items": {"type": "INTEGER"}, "description": "OPCIONAL. Recuadro [ymin, xmin, ymax, xmax] normalizado a 1000. Si se omite, se buscará con precisión térmica."}}}}]},
             {"function_declarations": [{"name": "control_phone_flashlight", "description": "Controla la linterna LED del teléfono del usuario.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "enum": ["on", "off"]}}}}]},
             {"function_declarations": [{"name": "generar_guia_visual_ensamblaje", "description": "Genera una imagen editada sobre la vista real para mostrar cómo conectar/ensamblar algo.", "parameters": {"type": "OBJECT", "properties": {"tarea": {"type": "STRING"}, "contexto": {"type": "STRING"}, "detalles_tecnicos": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "consultar_orquestador_reparaciones", "description": "Consulta técnica profunda sobre manuales y fallas.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}}]},
             {"function_declarations": [{"name": "consultar_logistica_repuestos", "description": "Orquestador Logístico Principal. Busca repuestos en inventario, tiendas cercanas, calcula rutas y precios reales.", "parameters": {"type": "OBJECT", "properties": {"repuesto": {"type": "STRING"}, "marca": {"type": "STRING"}, "equipo": {"type": "STRING"}, "ubicacion_tecnico": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "consultar_experiencias_tecnicas", "description": "Busca en la BASE DE CONOCIMIENTO COLECTIVA de técnicos. Encuentra reparaciones previas similares al problema actual para enriquecer el diagnóstico con experiencia real del equipo. Llamar SIEMPRE que tengas un síntoma o falla reportada.", "parameters": {"type": "OBJECT", "properties": {"sintoma": {"type": "STRING", "description": "Descripción del problema o síntoma actual"}, "categoria": {"type": "STRING", "description": "OPCIONAL. Categoría del equipo: Refrigeración, Tableros Eléctricos, Motores, etc."}}}}]},
             {"function_declarations": [{"name": "guardar_experiencia_reparacion", "description": "Guarda la experiencia de esta reparación en la base de conocimiento colectiva. Llamar SOLO cuando la reparación fue EXITOSA y el técnico confirma que el equipo funciona.", "parameters": {"type": "OBJECT", "properties": {"transcript": {"type": "STRING", "description": "Resumen completo de la sesión: síntoma, diagnóstico, pasos realizados y resultado final."}}}}]},
        ]
    elif mode == "hogar":
        system_instruction = f"Localización GPS actual del Aprendiz: {location}.\n\n" + LEARNING_PROMPT
        tool_declarations = [
             # safety_guardian_agent temporalmente desactivado en hogar para estabilidad de sesión
             {"function_declarations": [{"name": "tutor_herramientas", "description": "Indica qué herramientas buscar en la caja.", "parameters": {"type": "OBJECT", "properties": {"tarea": {"type": "STRING"}}, "required": ["tarea"]}}]},
             {"function_declarations": [{"name": "evaluacion_paso_a_paso", "description": "Evalúa visualmente si el usuario completó el paso correctamente.", "parameters": {"type": "OBJECT", "properties": {"accion": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "handle_vision_result", "description": "Guarda en memoria de forma silenciosa lo que ves en cámara (artefacto, fallas, coords de componentes).", "parameters": {"type": "OBJECT", "properties": {"tipo": {"type": "STRING"}, "marca": {"type": "STRING"}, "modelo": {"type": "STRING"}, "fallas_comunes": {"type": "ARRAY", "items": {"type": "STRING"}}, "componentes": {"type": "OBJECT", "description": "Diccionario clave-valor donde la clave es la pieza y el valor es el bounding box normalizado [ymin, xmin, ymax, xmax]. Ej: {'rele': [200, 100, 300, 400]}."}}}}]},
             {"function_declarations": [{"name": "parts_prefetch_agent", "description": "Pre-carga precios y disponibilidad de repuestos.", "parameters": {"type": "OBJECT", "properties": {"brand": {"type": "STRING"}, "appliance_type": {"type": "STRING"}, "location": {"type": "STRING"}, "part_list": {"type": "ARRAY", "items": {"type": "STRING"}}}}}]},
             {"function_declarations": [{"name": "control_phone_flashlight", "description": "Controla la linterna LED del teléfono del usuario.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "enum": ["on", "off"]}}}}]},
             {"function_declarations": [{"name": "mostrar_componente", "description": "Dibuja un bounding box resaltando un componente en la pantalla del usuario. Úsalo PROACTIVAMENTE cuando quieras señalar algo visible en la cámara como referencia visual. Si no conoces la ubicación exacta, omite 'coordenadas' para activar al especialista de alta precisión.", "parameters": {"type": "OBJECT", "properties": {"componente": {"type": "STRING"}, "coordenadas": {"type": "ARRAY", "items": {"type": "INTEGER"}, "description": "OPCIONAL. Recuadro [ymin, xmin, ymax, xmax] normalizado a 1000. Si se omite, se buscará con precisión térmica."}}}}]},
             {"function_declarations": [{"name": "generar_guia_visual_ensamblaje", "description": "Genera una imagen editada sobre la vista real para mostrar cómo conectar/ensamblar algo.", "parameters": {"type": "OBJECT", "properties": {"tarea": {"type": "STRING"}, "contexto": {"type": "STRING"}, "detalles_tecnicos": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "consultar_orquestador_reparaciones", "description": "Consulta técnica profunda sobre manuales y fallas.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}}]},
             {"function_declarations": [{"name": "consultar_especialistas_hogar", "description": "Modo Profesor: Activa especialistas para aprendizaje socrático.", "parameters": {"type": "OBJECT", "properties": {"tarea_usuario": {"type": "STRING"}}, "required": ["tarea_usuario"]}}]},
             {"function_declarations": [{"name": "consultar_reparacion_directa", "description": "Modo Órdenes: Activa especialistas para resolución técnica rápida.", "parameters": {"type": "OBJECT", "properties": {"tarea_usuario": {"type": "STRING"}}, "required": ["tarea_usuario"]}}]},
             {"function_declarations": [{"name": "consultar_logistica_repuestos", "description": "Orquestador Logístico Principal. Busca repuestos en inventario, tiendas cercanas, calcula rutas y precios reales.", "parameters": {"type": "OBJECT", "properties": {"repuesto": {"type": "STRING"}, "marca": {"type": "STRING"}, "equipo": {"type": "STRING"}, "ubicacion_tecnico": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "create_work_order", "description": "Genera la orden de trabajo en el sistema ERP.", "parameters": {"type": "OBJECT", "properties": {"machine": {"type": "STRING"}, "issue": {"type": "STRING"}, "part_needed": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "consultar_experiencias_tecnicas", "description": "Busca en la BASE DE CONOCIMIENTO COLECTIVA de técnicos. Encuentra reparaciones previas similares al problema actual para enriquecer el diagnóstico con experiencia real del equipo.", "parameters": {"type": "OBJECT", "properties": {"sintoma": {"type": "STRING", "description": "Descripción del problema o síntoma actual"}, "categoria": {"type": "STRING", "description": "OPCIONAL. Categoría del equipo."}}}}]},
             {"function_declarations": [{"name": "guardar_experiencia_reparacion", "description": "Guarda la experiencia de esta reparación en la base de conocimiento colectiva. Llamar SOLO cuando la reparación fue EXITOSA.", "parameters": {"type": "OBJECT", "properties": {"transcript": {"type": "STRING", "description": "Resumen completo de la sesión: síntoma, diagnóstico, pasos realizados y resultado final."}}}}]},
        ]

    # Multimodal Live API (v1alpha) preference: 
    # A single tool object containing all function declarations.
    final_tools = [{"function_declarations": [td["function_declarations"][0] for td in tool_declarations]}]
    
    return system_instruction, final_tools


@app.get("/api/ephemeral-token")
async def get_ephemeral_token(mode: str = "residential", location: str = "Desconocida"):
    """
    🔐 Generates an ephemeral token for Flutter to connect directly to Gemini Live.
    The real API key NEVER leaves this server.
    """
    import inspect
    try:
        # Client with v1alpha for ephemeral token support
        token_client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={'api_version': 'v1alpha'}
        )

        # Generate single-use ephemeral token
        token_response = await token_client.aio.auth_tokens.create(
            config={"uses": 1}
        )
        print(f"DEBUG TOKEN OBJECT: {token_response}")

        # Get system prompt and tool declarations for the requested mode
        system_instruction, tool_declarations = _get_tool_declarations(mode, location)

        print(f"DEBUG HYBRID: Ephemeral token generated for mode={mode}")

        return {
            "token": token_response.name,  # "auth_tokens/abc123..."
            "system_prompt": system_instruction,
            "model": "gemini-2.0-flash-exp",
            "tool_declarations": tool_declarations
        }
    except Exception as e:
        print(f"ERROR generating ephemeral token: {e}")
        # Fallback: return the API key directly (for compatibility)
        system_instruction, tool_declarations = _get_tool_declarations(mode, location)
        return {
            "token": GEMINI_API_KEY,
            "system_prompt": system_instruction,
            "model": "gemini-2.0-flash-exp",
            "tool_declarations": tool_declarations,
            "fallback": True
        }


@app.post("/api/execute-tool")
async def execute_tool_http(request: Request):
    """
    📷 Hybrid Architecture: Executes tools via HTTP with Snapshot-on-Demand.
    Flutter sends the tool call + attached HD frame snapshot.
    """
    import inspect as _inspect
    import time

    data = await request.json()
    tool_name = data.get("name")
    tool_args = data.get("args", {})
    user_id = data.get("user_id", "default")
    frame_b64 = data.get("frame_base64")  # 📷 HD snapshot from Flutter

    if not tool_name:
        return {"error": "Missing 'name' parameter"}

    if tool_name not in TOOL_MAP:
        return {"error": f"Tool '{tool_name}' not found in TOOL_MAP"}

    start_t = time.time()
    print(f"🔀 HYBRID TOOL START: {tool_name}({list(tool_args.keys())}) user={user_id}")

    try:
        # Inject user_id
        final_args = {**tool_args, "user_id": user_id}

        # 📷 Inject frame snapshot for vision tools
        VISION_TOOLS = {
            "mostrar_componente", "generar_guia_visual_ensamblaje",
            "handle_vision_result", "evaluacion_paso_a_paso",
            "safety_guardian_agent", "consultar_vision_precision"
        }
        if tool_name in VISION_TOOLS and frame_b64:
            final_args["_frame_snapshot"] = base64.b64decode(frame_b64)
            print(f"📷 HYBRID SNAPSHOT: Frame attached for '{tool_name}' ({len(final_args['_frame_snapshot'])} bytes)")

        # Execute the tool
        if _inspect.iscoroutinefunction(TOOL_MAP[tool_name]):
            result = await TOOL_MAP[tool_name](**final_args)
        else:
            result = await asyncio.to_thread(TOOL_MAP[tool_name], **final_args)

        end_t = time.time()
        duration = end_t - start_t
        print(f"🔀 HYBRID TOOL END: {tool_name} ({duration:.2f}s)")

        # Normalize result
        if isinstance(result, dict):
            response_data = dict(result)
        else:
            response_data = {"result": str(result)}

        # Clean internal fields
        response_data.pop("scheduling", None)
        response_data["_duration_ms"] = int(duration * 1000)

        return response_data

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"🔀 HYBRID TOOL ERROR: {tool_name}: {e}")
        return {"error": str(e), "message": "Tool execution failed on backend."}


# --- LIVE WEBSOCKET ENDPOINT (ORIGINAL — sin cambios) ---
@app.websocket("/ws/gemini-live")
async def gemini_live_websocket(
    websocket: WebSocket, 
    mode: str = "residential", 
    location: str = "Desconocida",
    emergency_machine: str = None,
    emergency_issue: str = None,
    session_id: str = None,
    user_id: str = "default"  # ID for ConnectionManager cross-injection
):
    """
    WebSocket endpoint that bridges the Mobile App and Gemini Live API.
    `mode` should be 'industrial' or 'residential'
    """
    await websocket.accept()
    print(f"DEBUG IN: Incoming WebSocket connection successfully accepted for user: {user_id}, mode: {mode}")

    # Determine Model Config based on mode
    tool_declarations = []
    system_instruction = ""
    
    # State Recovery Injection
    recovered_memory = ""
    if session_id:
        try:
            with open(f"memory_{session_id}.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if data["notes"]:
                    recovered_memory = "\n\n[MEMORIA RECUPERADA POR DESCONEXIÓN DE RED RECIENTE]:\n"
                    for i, note in enumerate(data["notes"]):
                        recovered_memory += f"- {note}\n"
                    recovered_memory += "RETOMA EXACTAMENTE DONDE LO DEJASTE USANDO ESTA MEMORIA. NO REINICIES LA CONVERSACIÓN NI PIDAS DISCULPAS.\n\n"
        except FileNotFoundError:
            pass

    if mode == "residential":
        system_instruction = f"Localización GPS actual del Técnico: {location}.\n\n" + RESIDENTIAL_PROMPT
        # ALL entries must be dicts — never bare function references.
        # NOTE: start_safety_monitoring is declared but the real loop is DISABLED in the handler.
        tool_declarations = [
             {"function_declarations": [{"name": "safety_guardian_agent", "description": "Provee los riesgos HSE y el procedimiento de seguridad para la tarea.", "parameters": {"type": "OBJECT", "properties": {"machine": {"type": "STRING"}, "task": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "start_safety_monitoring", "description": "Inicia la vigilancia de seguridad continua. Ejecutar de manera asíncrona."}]},
             {"function_declarations": [{"name": "handle_vision_result", "description": "Guarda en memoria de forma silenciosa lo que ves en cámara (marca, modelo, bounding boxes de componentes).", "parameters": {"type": "OBJECT", "properties": {"tipo": {"type": "STRING"}, "marca": {"type": "STRING"}, "modelo": {"type": "STRING"}, "fallas_comunes": {"type": "ARRAY", "items": {"type": "STRING"}}, "componentes": {"type": "OBJECT", "description": "Diccionario clave-valor donde la clave es la pieza y el valor es el bounding box normalizado [ymin, xmin, ymax, xmax]. Ej: {'rele': [200, 100, 300, 400]}."}}}}]},
             {"function_declarations": [{"name": "mostrar_componente", "description": "Dibuja un bounding box resaltando el componente en la pantalla del técnico. Úsalo PROACTIVAMENTE cuando quieras señalar algo visible en la cámara. Si no conoces la ubicación exacta, omite 'coordenadas' para activar al especialista de alta precisión.", "parameters": {"type": "OBJECT", "properties": {"componente": {"type": "STRING"}, "coordenadas": {"type": "ARRAY", "items": {"type": "INTEGER"}, "description": "OPCIONAL. Recuadro [ymin, xmin, ymax, xmax] normalizado a 1000. Si se omite, se buscará con precisión térmica."}}}}]},
             {"function_declarations": [{"name": "control_phone_flashlight", "description": "Controla la linterna LED del teléfono del usuario.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "enum": ["on", "off"]}}}}]},
             {"function_declarations": [{"name": "generar_guia_visual_ensamblaje", "description": "Genera una imagen editada sobre la vista real para mostrar cómo conectar/ensamblar algo.", "parameters": {"type": "OBJECT", "properties": {"tarea": {"type": "STRING"}, "contexto": {"type": "STRING"}, "detalles_tecnicos": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "consultar_orquestador_reparaciones", "description": "Consulta técnica profunda sobre manuales y fallas.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}}]},
             {"function_declarations": [{"name": "consultar_logistica_repuestos", "description": "Orquestador Logístico Principal. Busca repuestos en inventario, tiendas cercanas, calcula rutas y precios reales.", "parameters": {"type": "OBJECT", "properties": {"repuesto": {"type": "STRING"}, "marca": {"type": "STRING"}, "equipo": {"type": "STRING"}, "ubicacion_tecnico": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "consultar_experiencias_tecnicas", "description": "Busca en la BASE DE CONOCIMIENTO COLECTIVA de técnicos. Encuentra reparaciones previas similares al problema actual para enriquecer el diagnóstico con experiencia real del equipo. Llamar SIEMPRE que tengas un síntoma o falla reportada.", "parameters": {"type": "OBJECT", "properties": {"sintoma": {"type": "STRING", "description": "Descripción del problema o síntoma actual"}, "categoria": {"type": "STRING", "description": "OPCIONAL. Categoría del equipo: Refrigeración, Tableros Eléctricos, Motores, etc."}}}}]},
             {"function_declarations": [{"name": "guardar_experiencia_reparacion", "description": "Guarda la experiencia de esta reparación en la base de conocimiento colectiva. Llamar SOLO cuando la reparación fue EXITOSA y el técnico confirma que el equipo funciona.", "parameters": {"type": "OBJECT", "properties": {"transcript": {"type": "STRING", "description": "Resumen completo de la sesión: síntoma, diagnóstico, pasos realizados y resultado final."}}}}]},
        ]
        
    elif mode == "hogar":
        system_instruction = f"Localización GPS actual del Aprendiz: {location}.\n\n" + LEARNING_PROMPT
        # ALL entries must be dicts — never bare function references.
        # NOTE: start_safety_monitoring is declared but the real loop is DISABLED in the handler.
        tool_declarations = [
             {"function_declarations": [{"name": "safety_guardian_agent", "description": "Evalúa los riesgos HSE de la tarea para el usuario inexperto.", "parameters": {"type": "OBJECT", "properties": {"machine": {"type": "STRING"}, "task": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "start_safety_monitoring", "description": "Inicia la vigilancia de seguridad continua. Ejecutar de manera asíncrona.", "parameters": {"type": "OBJECT", "properties": {}}}]},
             {"function_declarations": [{"name": "tutor_herramientas", "description": "Indica qué herramientas buscar en la caja.", "parameters": {"type": "OBJECT", "properties": {"tarea": {"type": "STRING"}}, "required": ["tarea"]}}]},
             {"function_declarations": [{"name": "evaluacion_paso_a_paso", "description": "Evalúa visualmente si el usuario completó el paso correctamente.", "parameters": {"type": "OBJECT", "properties": {"accion": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "handle_vision_result", "description": "Guarda en memoria de forma silenciosa lo que ves en cámara (artefacto, fallas, coords de componentes).", "parameters": {"type": "OBJECT", "properties": {"tipo": {"type": "STRING"}, "marca": {"type": "STRING"}, "modelo": {"type": "STRING"}, "fallas_comunes": {"type": "ARRAY", "items": {"type": "STRING"}}, "componentes": {"type": "OBJECT", "description": "Diccionario clave-valor donde la clave es la pieza y el valor es el bounding box normalizado [ymin, xmin, ymax, xmax]. Ej: {'rele': [200, 100, 300, 400]}."}}}}]},
             {"function_declarations": [{"name": "parts_prefetch_agent", "description": "Pre-carga precios y disponibilidad de repuestos.", "parameters": {"type": "OBJECT", "properties": {"brand": {"type": "STRING"}, "appliance_type": {"type": "STRING"}, "location": {"type": "STRING"}, "part_list": {"type": "ARRAY", "items": {"type": "STRING"}}}}}]},
             {"function_declarations": [{"name": "control_phone_flashlight", "description": "Controla la linterna LED del teléfono del usuario.", "parameters": {"type": "OBJECT", "properties": {"action": {"type": "STRING", "enum": ["on", "off"]}}}}]},
             {"function_declarations": [{"name": "mostrar_componente", "description": "Dibuja un bounding box resaltando un componente en la pantalla del usuario. Úsalo PROACTIVAMENTE cuando quieras señalar algo visible en la cámara como referencia visual.", "parameters": {"type": "OBJECT", "properties": {"componente": {"type": "STRING", "description": "Nombre del componente"}}}}]},
             {"function_declarations": [{"name": "generar_guia_visual_ensamblaje", "description": "Genera una imagen editada sobre la vista real para mostrar cómo conectar/ensamblar algo.", "parameters": {"type": "OBJECT", "properties": {"tarea": {"type": "STRING"}, "contexto": {"type": "STRING"}, "detalles_tecnicos": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "consultar_orquestador_reparaciones", "description": "Consulta técnica profunda sobre manuales y fallas.", "parameters": {"type": "OBJECT", "properties": {"query": {"type": "STRING"}}, "required": ["query"]}}]},
             {"function_declarations": [{"name": "consultar_especialistas_hogar", "description": "Modo Profesor: Activa especialistas para aprendizaje socrático.", "parameters": {"type": "OBJECT", "properties": {"tarea_usuario": {"type": "STRING"}}, "required": ["tarea_usuario"]}}]},
             {"function_declarations": [{"name": "consultar_reparacion_directa", "description": "Modo Órdenes: Activa especialistas para resolución técnica rápida.", "parameters": {"type": "OBJECT", "properties": {"tarea_usuario": {"type": "STRING"}}, "required": ["tarea_usuario"]}}]},
             {"function_declarations": [{"name": "consultar_logistica_repuestos", "description": "Orquestador Logístico Principal. Busca repuestos en inventario, tiendas cercanas, calcula rutas y precios reales.", "parameters": {"type": "OBJECT", "properties": {"repuesto": {"type": "STRING"}, "marca": {"type": "STRING"}, "equipo": {"type": "STRING"}, "ubicacion_tecnico": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "create_work_order", "description": "Genera la orden de trabajo en el sistema ERP.", "parameters": {"type": "OBJECT", "properties": {"machine": {"type": "STRING"}, "issue": {"type": "STRING"}, "part_needed": {"type": "STRING"}}}}]},
             {"function_declarations": [{"name": "consultar_experiencias_tecnicas", "description": "Busca en la BASE DE CONOCIMIENTO COLECTIVA de técnicos. Encuentra reparaciones previas similares al problema actual para enriquecer el diagnóstico con experiencia real del equipo.", "parameters": {"type": "OBJECT", "properties": {"sintoma": {"type": "STRING", "description": "Descripción del problema o síntoma actual"}, "categoria": {"type": "STRING", "description": "OPCIONAL. Categoría del equipo."}}}}]},
             {"function_declarations": [{"name": "guardar_experiencia_reparacion", "description": "Guarda la experiencia de esta reparación en la base de conocimiento colectiva. Llamar SOLO cuando la reparación fue EXITOSA.", "parameters": {"type": "OBJECT", "properties": {"transcript": {"type": "STRING", "description": "Resumen completo de la sesión: síntoma, diagnóstico, pasos realizados y resultado final."}}}}]},
        ]
        
    # No modificamos la estructura básica para evitar corromper los esquemas de Gemini API.
    # El status 'NON_BLOCKING' se maneja solo a nivel de nuestro código (TOOL_MAP).

    # Minimal config — native audio preview only accepts a subset of fields
    # Do NOT add: generation_config, input_audio_transcription, output_audio_transcription
    # Any unsupported field causes a 1008 Policy Violation WebSocket close
    config = types.LiveConnectConfig(
        response_modalities=['AUDIO'],
        system_instruction=types.Content(parts=[types.Part.from_text(text=system_instruction)]),
        tools=tool_declarations if tool_declarations else None,
    )

    MAX_GEMINI_RETRIES = 5
    gemini_retry_count = 0

    while gemini_retry_count < MAX_GEMINI_RETRIES:
      try:
        if gemini_retry_count > 0:
            print(f"🔄 AUTO-RECONEXIÓN: Intento {gemini_retry_count}/{MAX_GEMINI_RETRIES} de reconexión a Gemini Live...")
            await asyncio.sleep(1)  # Brief pause before retry
        # Connect to the google genai Live API using the dedicated client_live
        # Using the exact model from the documentation
        async with client_live.aio.live.connect(model="gemini-2.5-flash-native-audio-preview-12-2025", config=config) as session:
            print(f"DEBUG: Session opened with Gemini Live. Mode: {mode}, User: {user_id}")
            
            # Register in ConnectionManager so REST endpoints can cross-inject
            manager.register(user_id, websocket, session)
            
            # 📍 Store GPS from WebSocket URL immediately into session context for tool access
            manager.store_context(user_id, "gps_location", location)
            print(f"DEBUG GPS: Stored location for session '{user_id}': {location}")
            
            # user_id is injected directly in execute_tool_and_respond()
            # No need to redefine TOOL_MAP here — avoids lambda/asyncio nested loop bugs
            
            # Manda el loop proactivo asíncrono. Gemini guardará fotos en memoria durante 3 segs 
            # de forma totalmente silenciosa antes de que el usuario haga la pregunta importante.
            asyncio.create_task(proactive_vision_loop(session, user_id, mode))
            
            print("DEBUG: Session ready. Proactive Vision started in background.")

            session_alive = asyncio.Event()
            session_alive.set()

            async def receive_from_client():
                """Receives JSON data (audio/image) from mobile and sends to Gemini."""
                input_audio_buffer = bytearray()
                packet_count = 0
                _prediction_dispatched = False  # 🔮 Fired only once per session
                try:
                    while session_alive.is_set():
                        message_text = await websocket.receive_text()
                        try:
                            import json
                            import base64
                            data_dict = json.loads(message_text)
                            modality = data_dict.get("type")
                            b64_data = data_dict.get("data")

                            if modality:
                                # audio/image have 'data', text has 'text'
                                if modality in ["audio", "image"] and b64_data:
                                    raw_bytes = base64.b64decode(b64_data)
                                    
                                    if modality == "audio":
                                        packet_count += 1
                                        if packet_count % 50 == 0:
                                            print("DEBUG IN: Audio flowing (~10 seconds worth of chunks)...")
                                            
                                        input_audio_buffer.extend(raw_bytes)
                                        # Send to Gemini in chunks of ~100ms (3200 bytes at 16kHz 16-bit)
                                        # Smaller = faster response, but not too small to avoid flooding
                                        if len(input_audio_buffer) >= 3200:
                                            await session.send_realtime_input(audio={
                                                "data": bytes(input_audio_buffer), 
                                                "mime_type": "audio/pcm;rate=16000"
                                            })
                                            input_audio_buffer.clear()
                                            
                                    elif modality == "image":
                                        # Send vision frame in real-time
                                        print("DEBUG IN: Received vision frame from camera")
                                        # SIEMPRE guardar en el buffer global (sobrevive a reinicios de sesión)
                                        _global_latest_frames[user_id] = raw_bytes
                                        session_data = manager.active_sessions.get(user_id)
                                        if session_data:
                                            session_data["latest_frame"] = raw_bytes
                                        await session.send_realtime_input(media={
                                            "mime_type": "image/jpeg",
                                            "data": raw_bytes
                                        })
                                        
                                        if not _prediction_dispatched:
                                            _prediction_dispatched = True
                                            print("🔮 CEREBRO PREDICTIVO: Primer frame detectado. Lanzando análisis predictivo...")
                                            asyncio.create_task(
                                                cerebro_predictivo_worker(session, raw_bytes, user_id)
                                            )
                                            
                                elif modality == "text" and data_dict.get("text"):
                                    # Support for text input (useful for testing and accessibility)
                                    text_input = data_dict.get("text")
                                    print(f"DEBUG IN: Received text message: {text_input}")
                                    # Use send_client_content which includes turn_complete=True by default
                                    await session.send_client_content(
                                        turns=[types.Content(role="user", parts=[types.Part.from_text(text=text_input)])],
                                        turn_complete=True
                                    )
                                    
                                elif modality == "end_turn":
                                    print("DEBUG IN: User ended turn (Mic Closed). Signaling Gemini...")
                                    if len(input_audio_buffer) > 0:
                                        await session.send_realtime_input(audio={
                                            "data": bytes(input_audio_buffer), 
                                            "mime_type": "audio/pcm;rate=16000"
                                        })
                                        input_audio_buffer.clear()
                                    # The Gemini Live API automatically responds when it has enough context.
                                    # Sending an empty `end_of_turn` frame crashes the current API preview with code 1008.
                                    pass
                        except Exception as e:
                            import traceback
                            print(f"DEBUG CRITICAL: Error sending to Gemini (Session closed or 1011). Stopping audio loop: {e}")
                            session_alive.clear()
                            break

                except WebSocketDisconnect:
                    print("DEBUG: Mobile client disconnected.")
                except Exception as e:
                    import traceback
                    print(f"DEBUG ERROR in receive_from_client: {e}")
                    traceback.print_exc()

            async def receive_from_gemini():
                """Listens to Gemini responses and forwards audio/tools to app."""
                audio_buffer = bytearray()
                try:
                    while session_alive.is_set():
                        async for response in session.receive():
                            # Transcripciones exactas en tiempo real
                            if response.server_content:
                                if getattr(response.server_content, "input_transcription", None):
                                    print(f"DEBUG TRANSCRIPT INPUT: {response.server_content.input_transcription.text}")
                                if getattr(response.server_content, "output_transcription", None):
                                    print(f"DEBUG TRANSCRIPT OUTPUT: {response.server_content.output_transcription.text}")

                            # Handle Model Output (Audio & Text)
                            if response.server_content and response.server_content.model_turn:
                                for part in response.server_content.model_turn.parts:
                                    if part.text:
                                        print(f"DEBUG TRANSCRIPT: {part.text}", end="", flush=True)
                                    if part.inline_data and part.inline_data.data:
                                        audio_buffer.extend(part.inline_data.data)
                                        
                                        # Send chunks of ~250ms (8000 bytes at 24kHz) for smooth playback
                                        # Small enough for low latency, big enough to avoid choppy audio
                                        if len(audio_buffer) >= 8000:
                                            try:
                                                await websocket.send_bytes(bytes(audio_buffer))
                                                audio_buffer.clear()
                                            except Exception as w_err:
                                                print(f"DEBUG: WS send error (client likely gone): {w_err}")
                                                audio_buffer.clear()

                            # --- BARGE-IN: Detect when user interrupts Gemini ---
                            if response.server_content and getattr(response.server_content, 'interrupted', False):
                                print("DEBUG BARGE-IN: User interrupted Gemini! Clearing audio buffer and signaling Flutter.")
                                audio_buffer.clear()  # Drop any unsent audio
                                try:
                                    await websocket.send_json({"type": "interrupted"})
                                except Exception:
                                    pass

                            # Flush audio if turn finishes or a tool is called
                            is_turn_complete = response.server_content and response.server_content.turn_complete
                            is_tool_call = response.tool_call is not None
                            
                            if is_turn_complete or is_tool_call:
                                if len(audio_buffer) > 0:
                                    try:
                                        await websocket.send_bytes(bytes(audio_buffer))
                                        audio_buffer.clear()
                                    except Exception as w_err:
                                        print(f"DEBUG: WS send error during flush: {w_err}")

                            # Handle Tool Calls (with Ambient Intelligence: NON_BLOCKING support)
                            if response.tool_call:
                                print(f"\n\n*** GEMINI QUIERE LLAMAR A UNA HERRAMIENTA: {response.tool_call} ***\n\n")
                                for function_call in response.tool_call.function_calls:
                                    name = function_call.name
                                    args = function_call.args
                                    
                                    # Intercept native async tools con funciones de alto nivel
                                    if name == "start_safety_monitoring":
                                        # SAFETY LOOP DISABLED: Return immediate OK response instead of launching loop
                                        print(f"DEBUG: start_safety_monitoring called but loop is DISABLED. Returning passive ack.")
                                        passive_ack = types.FunctionResponse(
                                            id=function_call.id,
                                            name="start_safety_monitoring",
                                            response={"status": "monitoring_passive", "message": "Vigilancia en modo pasivo. Sin interrupciones automáticas activas."}
                                        )
                                        await session.send(input=types.LiveClientToolResponse(function_responses=[passive_ack]))
                                        continue
                                        
                                    is_background = name in NON_BLOCKING_TOOLS
                                    scheduling = TOOL_SCHEDULING.get(name)
                                    block_type = 'NON_BLOCKING (Siguiendo hablando...)' if is_background else 'BLOCKING (Pausa para esperar...)'
                                    print(f"\nDEBUG TOOL START: {name}({args}) [{block_type}]")
                                    
                                    # 📊 TELEMETRY: Emit tool start event to Flutter Judge Mode
                                    _AGENT_LABELS = {
                                        "consultar_orquestador_reparaciones": "🔧 Reparaciones ADK",
                                        "consultar_logistica_repuestos": "🚛 Logística",
                                        "consultar_experiencias_tecnicas": "📚 RAG Firestore",
                                        "guardar_experiencia_reparacion": "💾 RAG Write",
                                        "generar_guia_visual_ensamblaje": "🖼️ Visual Guide",
                                        "mostrar_componente": "🦅 Eagle Eye",
                                        "safety_guardian_agent": "🛡️ Safety Guardian",
                                        "consultar_especialistas_hogar": "🏠 Mentor Hogar",
                                        "consultar_reparacion_directa": "⚡ Reparación Directa",
                                        "control_phone_flashlight": "💡 Flashlight",
                                    }
                                    _agent_label = _AGENT_LABELS.get(name, f"⚙️ {name}")
                                    await manager.emit_telemetry(
                                        user_id, "tool_start", _agent_label,
                                        "running", f"{block_type}")
                                    
                                    print(f"🔍 DEBUG POINT A: Tool '{name}' lookup in TOOL_MAP...")
                                    if name in TOOL_MAP:
                                        print(f"🔍 DEBUG POINT B: Tool '{name}' found. Defining execute_tool_and_respond...")

                                        async def execute_tool_and_respond(t_name, t_args, t_id, t_is_bg, t_sched, frame_snap=None):
                                            import time, inspect, traceback
                                            start_t = time.time()
                                            try:
                                                # Inject user_id cleanly — replaces the broken lambda wrappers
                                                final_args = {**t_args, "user_id": user_id}
                                                
                                                # 📷 FRAME SNAPSHOT INJECTION: Para herramientas visuales que necesitan el frame
                                                # capturamos en el momento del dispatch (no cuando el task corre en background)
                                                if frame_snap is not None:
                                                    final_args["_frame_snapshot"] = frame_snap
                                                
                                                if inspect.iscoroutinefunction(TOOL_MAP[t_name]):
                                                    res = await TOOL_MAP[t_name](**final_args)
                                                else:
                                                    res = await asyncio.to_thread(TOOL_MAP[t_name], **final_args)
                                                end_t = time.time()
                                                print(f"DEBUG TOOL END: {t_name} (Duración: {end_t - start_t:.2f}s)")
                                                
                                                response_data = dict(res) if isinstance(res, dict) else {"result": str(res)}
                                                
                                                # Limpiar scheduling espurios metidos internamente por el agente viejo
                                                if "scheduling" in response_data:
                                                    del response_data["scheduling"]
                                                
                                                # NOTE: 'scheduling' is NOT passed here. It caused 1008 policy violation
                                                # on the native audio model. The tool sends its result directly via WS.
                                                if not t_is_bg:
                                                    await session.send(input=types.LiveClientToolResponse(
                                                        function_responses=[
                                                            types.FunctionResponse(
                                                                name=t_name,
                                                                response=response_data,
                                                                id=t_id
                                                            )
                                                        ]
                                                    ))
                                                
                                                # Si la herramienta era INTERRUPT, forzamos al cliente a cortar el habla
                                                if t_sched == "INTERRUPT":
                                                    print(f"DEBUG BARGE-IN: Tool {t_name} finished (INTERRUPT). Signaling Flutter to cut audio.")
                                                    audio_buffer.clear()
                                                    try:
                                                        await websocket.send_json({"type": "interrupted"})
                                                    except Exception as e:
                                                        print(f"DEBUG: Error sending interrupt signal: {e}")
                                                
                                                await websocket.send_json({"type": "tool_call", "name": t_name, "result": res, "background": t_is_bg})
                                                # 📊 TELEMETRY: Tool completed
                                                _t_agent = _AGENT_LABELS.get(t_name, f"⚙️ {t_name}") if '_AGENT_LABELS' in dir() else t_name
                                                await manager.emit_telemetry(
                                                    user_id, "tool_end", _t_agent,
                                                    "done", f"{end_t - start_t:.1f}s",
                                                    duration_ms=int((end_t - start_t) * 1000))
                                                
                                                return res
                                            except Exception as tool_err:
                                                print(f"DEBUG ERROR executing tool {t_name}: {tool_err}")
                                                traceback.print_exc()
                                                error_res = {"error": str(tool_err), "message": "The tool call failed. Check arguments."}
                                                if not t_is_bg:
                                                    await session.send(input=types.LiveClientToolResponse(
                                                        function_responses=[
                                                            types.FunctionResponse(name=t_name, response=error_res, id=t_id)
                                                        ]
                                                    ))
                                                return error_res
                                        
                                        # Si la tool es de background, ejecutamos el código asíncronamente en una tarea para no bloquear el receive loop
                                        print(f"🔍 DEBUG POINT C: is_background={is_background} for tool '{name}'")
                                        if is_background:
                                            # 📷 SNAPSHOT del frame AHORA, en el hilo principal, antes de que el task corra
                                            # Esto garantiza que herramientas visuales siempre tengan imagen disponible
                                            VISION_TOOLS = {"generar_guia_visual_ensamblaje", "mostrar_componente", "handle_vision_result", "evaluacion_paso_a_paso", "safety_guardian_agent"}
                                            captured_frame = None
                                            if name in VISION_TOOLS:
                                                snap_data = manager.active_sessions.get(user_id)
                                                if snap_data and snap_data.get("latest_frame"):
                                                    captured_frame = snap_data["latest_frame"]
                                                    print(f"📷 SNAPSHOT: Frame capturado del manager para '{name}' ({len(captured_frame)} bytes)")
                                                else:
                                                    # Fallback: buffer global (sobrevive a reinicios de sesión por error 1011)
                                                    captured_frame = _global_latest_frames.get(user_id)
                                                    if captured_frame:
                                                        print(f"📷 SNAPSHOT FALLBACK: Usando frame del buffer global para '{name}' ({len(captured_frame)} bytes)")
                                                    else:
                                                        print(f"⚠️ SNAPSHOT WARNING: No hay frame disponible ni en manager ni en buffer global para '{name}'")
                                            
                                            # 🔥 BACKGROUND TOOLS: Para herramientas asíncronas, enviamos ACK inmediato a Gemini
                                            # para que no espere y cause timeout 1011 (Deadline Exceeded).
                                            # El trabajo real sigue en un task totalmente desvinculado del session loop.
                                            print(f"🔥 BACKGROUND TOOL: Enviando ACK inmediato anti-1011 a Gemini para '{name}' y lanzando tarea oculta...")
                                            # 1. ACK inmediato al session de Gemini — no espera al resultado
                                            BACKGROUND_ACK_MSG = {
                                                "generar_guia_visual_ensamblaje": "Generando guía visual en segundo plano, te muestro la imagen en instantes.",
                                                "consultar_orquestador_reparaciones": "Consultando al orquestador de reparaciones, te tendré el diagnóstico en instantes.",
                                                "consultar_logistica_repuestos": "Consultando logística de repuestos en segundo plano.",
                                                "consultar_especialistas_hogar": "Consultando a mis especialistas de investigación y seguridad, dame un momento para prepararte el mejor camino.",
                                                "consultar_reparacion_directa": "Preparando el protocolo de reparación rápida con mis especialistas, un momento.",
                                                "safety_guardian_agent": "Analizando las condiciones de seguridad en pantalla, dame un milisegundo.",
                                                "mostrar_componente": "Marcando componentes en la pantalla...",
                                                "handle_vision_result": "Procesando hallazgos visuales...",
                                                "parts_prefetch_agent": "Buscando repuestos preventivamente...",
                                                "consultar_experiencias_tecnicas": "Buscando experiencias de técnicos anteriores...",
                                                "guardar_experiencia_reparacion": "Guardando reparación...",
                                                "control_phone_flashlight": "Accionando linterna...",
                                                "tutor_herramientas": "Preparando inventario de herramientas..."
                                            }
                                            ack_msg = BACKGROUND_ACK_MSG.get(name, "Procesando en segundo plano...")
                                            try:
                                                await session.send(input=types.LiveClientToolResponse(
                                                    function_responses=[
                                                        types.FunctionResponse(
                                                            name=name,
                                                            response={"status": "procesando", "mensaje": ack_msg},
                                                            id=function_call.id
                                                        )
                                                    ]
                                                ))
                                            except Exception as ack_err:
                                                print(f"🔥 ERROR enviando ACK: {ack_err}")
                                            
                                            # 2. Lanzar el trabajo pesado en un task sepárate (SIN enviar FunctionResponse al final)
                                            async def heavy_background_worker(h_name, h_args, h_uid, h_frame):
                                                import traceback
                                                import asyncio
                                                import inspect
                                                print(f"🔥 BACKGROUND WORKER iniciado para '{h_name}'")
                                                try:
                                                    final_heavy_args = {**h_args, "user_id": h_uid}
                                                    if h_frame is not None:
                                                        final_heavy_args["_frame_snapshot"] = h_frame
                                                        
                                                    tool_func = TOOL_MAP[h_name]
                                                    # Ejecutar en hilo separado para herramientas ADK que bloquean el Event Loop
                                                    if inspect.iscoroutinefunction(tool_func):
                                                        # FIXED: Run async tools directly - NEVER create new event loop in thread
                                                        res = await tool_func(**final_heavy_args)
                                                    else:
                                                        res = await asyncio.to_thread(tool_func, **final_heavy_args)
                                                        
                                                    print(f"🔥 BACKGROUND WORKER finalizó '{h_name}': {res}")
                                                    
                                                    # --- FEEDBACK LOOP: Enviar el resultado real del agente ADK de vuelta a Gemini Live ---
                                                    # Como ya enviamos un ACK (FunctionResponse), Gemini ya cerró ese turno.
                                                    # Para que Gemini "sepa" lo que encontraron los especialistas, inyectamos el resultado como un input de texto.
                                                    try:
                                                        output_text = res.get("result", str(res)) if isinstance(res, dict) else str(res)
                                                        feedback_prompt = f"REPORTE DE ESPECIALISTAS ADK ({h_name}): {output_text}\n\nInstrucción: Usa esta información técnica real para guiar al usuario ahora."
                                                        print(f"🔥 FEEDBACK LOOP: Inyectando reporte de especialistas en la sesión de Gemini...")
                                                        # CRITICO: Solo inyectar si la sesion Gemini sigue viva.
                                                  # Los background workers pueden terminar despues de que Gemini cerro (1011).
                                                  # session.send() en sesion muerta dispara error 1008 (policy violation).
                                                        if not session_alive.is_set():
                                                            print(f"🔥 FEEDBACK LOOP SKIP: Sesion cerrada. Descartando resultado de {h_name}.")
                                                        else:
                                                            await session.send(input=types.LiveClientContent(
                                                                turns=[types.Content(role="user", parts=[types.Part.from_text(text=feedback_prompt)])],
                                                                turn_complete=True
                                                            ))
                                                            print(f"🔥 FEEDBACK LOOP SUCCESS: Reporte inyectado en sesion activa.")
                                                    except Exception as f_err:
                                                        print(f"🔥 FEEDBACK LOOP ERROR: No se pudo inyectar el resultado en la sesión: {f_err}")

                                                    # Notificar al cliente móvil del resultado (la imagen ya fue enviada por la tool misma)
                                                    try:
                                                        h_session_data = manager.active_sessions.get(h_uid)
                                                        if h_session_data:
                                                            await h_session_data["websocket"].send_json({"type": "tool_background_complete", "name": h_name})
                                                    except Exception:
                                                        pass
                                                except Exception as hw_err:
                                                    print(f"🔥 BACKGROUND WORKER error en '{h_name}': {hw_err}")
                                                    traceback.print_exc()
                                            
                                            print(f"DEBUG: Lanzando {name} como AsyncTask injectivo de fondo...")
                                            asyncio.create_task(heavy_background_worker(name, args, user_id, captured_frame))
                                            
                                        else:
                                            # Caso contrario esperamos (bloqueamos Gemini y nuestro WebSocket local)
                                            await execute_tool_and_respond(name, args, function_call.id, is_background, scheduling)
                        

                        print("DEBUG CRITICAL: Session turn generator ended. Yielding control to wait for next turn...")
                except Exception as e:
                    import traceback
                    print(f"DEBUG ERROR in receive_from_gemini (Gemini session died): {e}")
                    session_alive.clear()
                    traceback.print_exc()


            # Run ONLY TWO tasks concurrently:
            # 1. receive_from_client: Mobile -> Gemini (audio + video frames)
            # 2. receive_from_gemini: Gemini -> Mobile (audio + tool calls)
            # 3. proactive_ambient_loop: (DESACTIVADO POR PRUEBAS)
            await asyncio.gather(
                receive_from_client(), 
                receive_from_gemini(),
                # proactive_ambient_loop()
            )

      except Exception as e:
          err_str = str(e)
          print(f"DEBUG CRITICAL: Error in Live Session Block: {e}")
          # Auto-reconnect on transient Gemini errors (1011 Internal error / Deadline expired)
          if "1011" in err_str or "Internal error" in err_str or "Deadline expired" in err_str or "unavailable" in err_str.lower():
              gemini_retry_count += 1
              if gemini_retry_count < MAX_GEMINI_RETRIES:
                  print(f"🔄 Gemini 1011 detectado. Reconectando sesión... ({gemini_retry_count}/{MAX_GEMINI_RETRIES})")
                  try:
                      await websocket.send_json({"type": "reconnecting", "attempt": gemini_retry_count})
                  except Exception:
                      pass
                  continue  # retry the while loop
              else:
                  print(f"🔄 Max reintentos alcanzado ({MAX_GEMINI_RETRIES}). Cerrando sesión.")
          break  # Non-retriable error or max retries reached
      else:
          break  # Session ended cleanly (phone disconnected), no retry needed

    # Final cleanup
    manager.unregister(user_id)
    try:
        await websocket.close()
        print("DEBUG: Local WebSocket closed cleanly.")
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
