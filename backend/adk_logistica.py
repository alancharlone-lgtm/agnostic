"""
adk_logistica.py  
Agente de logística con herramientas nativas ADK.

ARQUITECTURA:
  - Root agent con: consultar_inventario_camioneta, buscar_tiendas_maps,
    buscar_en_mercadolibre, calcular_tiempo_ruta, + validador_web (AgentTool)
  - validador_web es un sub-agente separado con SOLO url_context (requerido
    porque la API de Gemini no permite mezclar url_context con herramientas custom)
  - Sin McpToolset → sin bug de anyio/cancel_scope
  
MIGRACIÓN CLOUD-NATIVE (Fase 1):
  - consultar_inventario_camioneta ahora lee de Firestore async
  - Fallback a mock hardcodeado si Firestore no responde
"""

import os
import json
import logging
from pathlib import Path

import httpx
from google.adk.agents import LlmAgent
from google.adk.tools import url_context, agent_tool, google_search

logger = logging.getLogger("agnostic.logistica")

_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")
_GCP_PROJECT = os.environ.get("GCP_PROJECT", "stok-7bc5c")

# ─── FIRESTORE ASYNC CLIENT (Lazy Init) ──────────────────────────────────────
_firestore_client = None

def _get_firestore_client():
    """Lazy-init del cliente async de Firestore."""
    global _firestore_client
    if _firestore_client is None:
        try:
            from google.cloud.firestore import AsyncClient
            _firestore_client = AsyncClient(project=_GCP_PROJECT)
            logger.info("[LOGISTICA] Firestore AsyncClient inicializado (project=%s)", _GCP_PROJECT)
        except Exception as e:
            logger.error("[LOGISTICA] Error inicializando Firestore: %s", e)
            _firestore_client = None
    return _firestore_client


# ─── MOCK FALLBACK (en caso de que Firestore no esté disponible) ───────────
_INVENTARIO_MOCK = {
    "capacitor 45uf": {"estado": "DISPONIBLE", "cantidad": 12, "ubicacion": "Cajón B3"},
    "termostato whirlpool": {"estado": "DISPONIBLE", "cantidad": 3, "ubicacion": "Cajón A1"},
    "placa electronica samsung": {"estado": "NO DISPONIBLE", "cantidad": 0, "ubicacion": None},
    "compresor lg": {"estado": "DISPONIBLE", "cantidad": 1, "ubicacion": "Cajón C7"},
    "bomba de desagote": {"estado": "NO DISPONIBLE", "cantidad": 0, "ubicacion": None},
}

# =============================================================================
# HERRAMIENTA: INVENTARIO DE CAMIONETA (Firestore Async + Mock Fallback)
# =============================================================================

async def consultar_inventario_camioneta(repuesto: str, id_tecnico: str = "default") -> dict:
    """
    Consulta si un repuesto está disponible en el inventario de la camioneta del técnico.
    Primero busca en Google Cloud Firestore. Si Firestore no está disponible, usa mock local.
    Devuelve estado (DISPONIBLE / NO DISPONIBLE), cantidad y ubicación en la camioneta.

    Args:
        repuesto: Nombre del repuesto a buscar (ej: "bomba de desagote", "termostato Whirlpool")
        id_tecnico: ID del técnico. Usar 'default' si no se especifica.
    """
    clave = repuesto.lower().strip()
    
    # ── INTENTO 1: Firestore Cloud ────────────────────────────────────────
    db = _get_firestore_client()
    if db is not None:
        try:
            # Buscar en colección van_inventory por nombre del repuesto
            query = db.collection("van_inventory").where("nombre", "==", clave)
            docs = []
            async for doc in query.stream():
                docs.append(doc.to_dict())
            
            if docs:
                item = docs[0]
                logger.info("[LOGISTICA] ☁️ Firestore hit: '%s' → %s", clave, item.get("estado"))
                return {
                    "repuesto": repuesto,
                    "id_tecnico": id_tecnico,
                    "fuente": "Google Cloud Firestore",
                    "estado": item.get("estado", "NO DISPONIBLE"),
                    "cantidad": item.get("cantidad", 0),
                    "ubicacion": item.get("ubicacion"),
                    "mensaje": (
                        f"El repuesto '{repuesto}' está disponible en camioneta: {item.get('ubicacion')}."
                        if item.get("estado") == "DISPONIBLE"
                        else f"El repuesto '{repuesto}' NO está disponible en la camioneta."
                    ),
                }
            else:
                logger.debug("[LOGISTICA] Firestore: '%s' no encontrado en colección", clave)
        except Exception as e:
            logger.warning("[LOGISTICA] Firestore query failed, falling back to mock: %s", e)

    # ── FALLBACK: Mock hardcodeado ────────────────────────────────────────
    resultado = _INVENTARIO_MOCK.get(clave, {
        "estado": "NO DISPONIBLE", "cantidad": 0, "ubicacion": None
    })

    return {
        "repuesto": repuesto,
        "id_tecnico": id_tecnico,
        "fuente": "inventario_local_mock",
        "estado": resultado["estado"],
        "cantidad": resultado.get("cantidad", 0),
        "ubicacion": resultado.get("ubicacion"),
        "mensaje": (
            f"El repuesto '{repuesto}' está disponible en camioneta: {resultado['ubicacion']}."
            if resultado["estado"] == "DISPONIBLE"
            else f"El repuesto '{repuesto}' NO está disponible en la camioneta."
        ),
    }


# =============================================================================
# SUB-AGENTE VALIDADOR WEB
# Separado del root agent porque la API de Gemini no permite mezclar
# built-in tools (url_context) con herramientas custom en el mismo agente.
# El root agent lo invoca como AgentTool.
# =============================================================================
_validador_web = LlmAgent(
    name="validador_web",
    model="gemini-3.1-flash-lite-preview",
    description=(
        "Visita la URL de una tienda y verifica si su página web menciona "
        "el repuesto buscado, precios o catálogo de productos."
    ),
    instruction=(
        "Sos el Validador Web. Recibís una URL de tienda y el nombre de un repuesto. "
        "Visitá la URL con `url_context`. "
        "Determiná si la página menciona explícitamente el repuesto, productos similares, "
        "o un catálogo de precios. "
        "Respondé solo con una de estas dos frases:\n"
        "- 'VALIDADA: [razón breve de por qué creés que tienen el repuesto]'\n"
        "- 'SIN_CONFIRMACIÓN: La página no menciona el repuesto ni productos similares.'"
    ),
    tools=[url_context],
)

# =============================================================================
# SUB-AGENTE BUSCADOR DE PRECIOS (google_search nativo — evita bloqueos anti-bot)
# Separado porque la API de Gemini no permite mezclar google_search con tools custom.
# =============================================================================
_buscador_precios = LlmAgent(
    name="buscador_precios",
    model="gemini-3.1-flash-lite-preview",
    description=(
        "Busca precios reales en internet para un repuesto usando Google Search. "
        "Devuelve precios encontrados en ARS con el nombre de la tienda."
    ),
    instruction=(
        "Sos el Buscador de Precios. Recibirás le nombre de un repuesto y la marca. "
        "Buscá en Google: '[repuesto marca] precio ARS argentina comprar'. "
        "Extraé los primeros 3-5 resultados con precio en pesos argentinos. "
        "Respondé SOLAMENTE con este formato, un resultado por línea:\n"
        "PRECIO: $X ARS - Tienda: [nombre] - Producto: [descripción breve]\n"
        "Si no encontrás precios concretos, respondé: SIN_PRECIOS_ENCONTRADOS"
    ),
    tools=[google_search],
)

# =============================================================================
# ROOT AGENT: ORQUESTADOR LOGÍSTICO CON HERRAMIENTAS NATIVAS + AGENTE WEB
# =============================================================================

# Cache solo el MCPToolset (es stateless), NO el agente (tiene state interno)
_cached_mcp_toolset = None

def get_logistics_agent():
    """
    Factory para crear el agente raíz. Se crea una instancia FRESCA del LlmAgent
    en cada invocación para evitar state leakage entre búsquedas.
    El MCPToolset SÍ se cachea porque es stateless y su inicialización es costosa.
    """
    global _cached_mcp_toolset
    
    if _cached_mcp_toolset is None:
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
        from google.adk.tools.mcp_tool.mcp_toolset import SseConnectionParams
        _cached_mcp_toolset = MCPToolset(
            connection_params=SseConnectionParams(
                url="https://agnostic-mcp-server-cl75dspfdq-uc.a.run.app/sse",
                timeout=15.0  # Extra time for Cloud Run cold-start wake-up
            )
        )
        logger.info("[LOGISTICA] MCPToolset inicializado y cacheado.")

    # Instancia FRESCA del agente en cada llamada — evita state leakage
    agent_tools = [
        consultar_inventario_camioneta,            # Cloud Firestore async + mock fallback
        _cached_mcp_toolset,                       # Remote MCP tools (maps, ruta)
        agent_tool.AgentTool(agent=_validador_web),    # Valida stock en webs de tiendas
        agent_tool.AgentTool(agent=_buscador_precios), # Busca precios reales en internet
    ]

    logistics_root_agent = LlmAgent(
        name="Coordinador_de_Logistica_de_Campo",
        model="gemini-3.1-flash-lite-preview",
        description=(
            "Agente de logística de campo. Dado un repuesto y la ubicación GPS del técnico, "
            "verifica la camioneta (Google Cloud Firestore), busca tiendas físicas cercanas, "
            "obtiene el precio de referencia en MercadoLibre y calcula las rutas más rápidas."
        ),
        instruction=(
            "Sos el Coordinador de Logística de Campo. Recibirás: Marca, Aparato, Repuesto y "
            "Ubicación GPS (lat,lng) del técnico. Ejecutá este flujo en 4 pasos:\n\n"
            "━━━ PASO 1: CAMIONETA ━━━\n"
            "Llamá a `consultar_inventario_camioneta` con el nombre del repuesto.\n"
            "→ Si DISPONIBLE: Informá y terminá.\n"
            "→ Si NO DISPONIBLE: Continuá con PASO 2.\n\n"
            "━━━ PASO 2: TIENDAS FÍSICAS (Maps con radio expansivo) ━━━\n"
            "Llamá a `buscar_tiendas_maps` del MCP server con radio_km=3.\n"
            "Revisá `instruccion_agente` en la respuesta:\n"
            "  - Si con_web > 0: Para cada tienda con `website`, "
            "llamá al agente `validador_web` con la URL y el nombre del repuesto. "
            "Recopilá el estado (VALIDADA / SIN_CONFIRMACIÓN) de cada una.\n"
            "  - Si con_web = 0: Repetí con radio_km=15, 50, 200 y hasta un máximo de 700km para zonas muy remotas.\n"
            "Guardá la lista de tiendas con sus estados y coordenadas para el PASO 4.\n\n"
            "━━━ PASO 3: PRECIO REAL DESDE LA WEB (con Google Search) ━━━\n"
            "Llamá al agente `buscador_precios` con el nombre del repuesto y la marca.\n"
            "El agente usará Google Search para buscar precios reales.\n"
            "Guardá los precios encontrados para el reporte final.\n\n"
            "━━━ PASO 4: RUTAS ━━━\n"
            "Para cada tienda de la lista del PASO 2 con coordenadas (lat/lng), "
            "llamá a `calcular_tiempo_ruta` del MCP server con las coordenadas del técnico y de la tienda.\n"
            "Ordená de menor a mayor tiempo de viaje.\n\n"
            "━━━ REPORTE FINAL ━━━\n"
            "Respondé con:\n"
            "1. 🚛 Camioneta: disponible / no disponible.\n"
            "2. 🏪 Opción más rápida física: [Tienda] a [X] min — stock [CONFIRMADO / SIN CONFIRMAR].\n"
            "3. 💰 Precio online más barato: $X ARS en [Tienda] — [Producto].\n"
            "4. 📋 Lista de precios encontrados en la web.\n"
            "5. ⚠️ Alerta si diferencia de precio físico vs online > 30%.\n\n"
            "REGLA DE ORO: Si alguna herramienta falla, DECÍLO. NUNCA inventes datos."
        ),
        tools=agent_tools,
    )
    
    return logistics_root_agent
