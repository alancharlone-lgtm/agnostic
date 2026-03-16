"""
RAG Knowledge Base — Base de Conocimiento Colectiva de Técnicos
================================================================
MIGRACIÓN CLOUD-NATIVE (Fase 1):
  - Escritura: Persiste en Google Cloud Firestore (colección repair_knowledge_base)
  - Lectura: Usa Firestore Vector Search nativo (find_nearest) para búsqueda por similitud
  - Fallback: Si Firestore no está disponible, cae a JSON local + cosine similarity manual

Flujo de ESCRITURA:
  1. Recibe la transcripción de una sesión Gemini Live.
  2. Gemini Flash extrae los datos clave en JSON estricto.
  3. Se genera un embedding con gemini-embedding-001.
  4. Se persiste en Firestore (con embedding como Vector field).

Flujo de LECTURA:
  1. Recibe el síntoma actual del técnico.
  2. Genera embedding del síntoma.
  3. Usa Firestore find_nearest (Vector Search) para los 3 casos más similares.
  4. Formatea el resultado para inyección en Gemini Live.
"""

import json
import os
import uuid
import math
import logging
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from google import genai

logger = logging.getLogger("agnostic.rag")

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
EMBEDDING_MODEL = "gemini-embedding-001"
EXTRACTION_MODEL = "gemini-3.1-flash-lite-preview"
KB_FILE_PATH = "repair_knowledge_base.json"
_GCP_PROJECT = os.environ.get("GCP_PROJECT", "stok-7bc5c")
_FIRESTORE_COLLECTION = "repair_knowledge_base"

# Cliente Gemini para extracción y embeddings
_client = None

def _get_client():
    """Lazy-init del cliente Gemini."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


# ─── FIRESTORE ASYNC CLIENT ──────────────────────────────────────────────────
_firestore_client = None

def _get_firestore_client():
    """Lazy-init del cliente async de Firestore."""
    global _firestore_client
    if _firestore_client is None:
        try:
            from google.cloud.firestore import AsyncClient
            _firestore_client = AsyncClient(project=_GCP_PROJECT)
            logger.info("[RAG] Firestore AsyncClient inicializado (project=%s)", _GCP_PROJECT)
        except Exception as e:
            logger.warning("[RAG] Firestore no disponible, usando JSON local: %s", e)
            _firestore_client = None
    return _firestore_client


# ─── MODELO DE DATOS ──────────────────────────────────────────────────────────

class RepairRecord(BaseModel):
    """Registro de una reparación completada exitosamente."""
    id_reparacion: str = Field(default_factory=lambda: str(uuid.uuid4()))
    categoria: str = Field(..., description="Ej: Refrigeración, Tableros Eléctricos, Motores")
    marca_modelo: str = Field(..., description="Ej: Heladera Comercial Gafa, Relé Térmico Siemens")
    sintoma_reportado: str = Field(..., description="Lo que dijo el cliente/técnico al inicio")
    diagnostico_real: str = Field(..., description="El problema técnico real encontrado")
    solucion_aplicada: str = Field(..., description="Paso a paso de cómo se arregló")
    embedding: list[float] = Field(default_factory=list, description="Vector de embedding")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── SYSTEM PROMPT DE EXTRACCIÓN ─────────────────────────────────────────────

EXTRACTION_SYSTEM_PROMPT = """Eres un sistema de extracción de datos de reparaciones técnicas.
Tu ÚNICA función es analizar la transcripción de una sesión de asistencia técnica y extraer los datos clave en formato JSON.

REGLAS INQUEBRANTABLES:
1. Si la sesión NO terminó con una reparación exitosa (el técnico se fue sin resolver, se cortó la conexión, o el problema persiste), DEBES responder exactamente: {"exito": false}
2. Si la sesión SÍ terminó con una reparación exitosa, extrae los datos en el esquema exacto de abajo.
3. NUNCA inventes datos. Si un campo no se mencionó explícitamente en la transcripción, usa "No especificado".
4. El campo "solucion_aplicada" debe ser un resumen paso a paso de lo que el técnico HIZO para resolver el problema, no lo que se le sugirió hacer.
5. La "categoria" debe ser una de: Refrigeración, Tableros Eléctricos, Motores, Lavarropas, Aire Acondicionado, Plomería, Gas, Electrónica, Otro.

ESQUEMA JSON DE SALIDA (cuando exito=true):
{
    "exito": true,
    "categoria": "string",
    "marca_modelo": "string",
    "sintoma_reportado": "string",
    "diagnostico_real": "string",
    "solucion_aplicada": "string"
}

ESQUEMA JSON DE SALIDA (cuando exito=false):
{
    "exito": false
}
"""


# ─── PERSISTENCIA LOCAL FALLBACK ──────────────────────────────────────────────

def _load_knowledge_base_local() -> list[dict]:
    """Carga la base de conocimiento desde el archivo JSON local (fallback)."""
    if not os.path.exists(KB_FILE_PATH):
        return []
    try:
        with open(KB_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def _save_knowledge_base_local(records: list[dict]):
    """Guarda la base de conocimiento en el archivo JSON local (fallback)."""
    with open(KB_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


# ─── UTILIDADES MATEMÁTICAS (para fallback local) ────────────────────────────

def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calcula la similitud del coseno entre dos vectores sin numpy."""
    if len(vec_a) != len(vec_b) or not vec_a:
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a * a for a in vec_a))
    magnitude_b = math.sqrt(sum(b * b for b in vec_b))
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    
    return dot_product / (magnitude_a * magnitude_b)


# ─── FLUJO DE ESCRITURA ──────────────────────────────────────────────────────

async def extract_and_save_repair(session_transcript: str) -> dict:
    """
    Flujo completo de extracción y guardado de una reparación.
    
    1. Llama a Gemini Flash para extraer datos estructurados del transcript.
    2. Genera embedding del síntoma + diagnóstico.
    3. Persiste en Firestore (prioritario) o en archivo JSON local (fallback).
    """
    logger.info("[RAG] Iniciando extracción de reparación...")
    
    client = _get_client()
    
    # ── PASO 1: Extracción de datos con Gemini Flash ──────────────────────
    try:
        response = await client.aio.models.generate_content(
            model=EXTRACTION_MODEL,
            contents=f"TRANSCRIPCIÓN DE SESIÓN:\n\n{session_transcript}",
            config=genai.types.GenerateContentConfig(
                system_instruction=EXTRACTION_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.0,
            )
        )
        
        raw_text = response.text.strip()
        logger.debug("[RAG] Respuesta de extracción: %s", raw_text[:200])
        
        # Parsear JSON
        import re
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if not json_match:
            return {"status": "ERROR", "error": "No se encontró JSON en la respuesta del modelo."}
        
        extracted_data = json.loads(json_match.group())
        
    except json.JSONDecodeError as e:
        logger.error("[RAG] Error parseando JSON de extracción: %s", e)
        return {"status": "ERROR", "error": f"JSON malformado del modelo: {e}"}
    except Exception as e:
        logger.error("[RAG] Error en llamada de extracción: %s", e)
        return {"status": "ERROR", "error": f"Error de API: {e}"}
    
    # ── Validar si fue una reparación exitosa ─────────────────────────────
    if not extracted_data.get("exito", False):
        logger.info("[RAG] Sesión sin reparación exitosa. No se guarda.")
        return {"status": "SKIP", "reason": "La sesión no terminó con una reparación exitosa."}
    
    # ── PASO 2: Generar Embedding ─────────────────────────────────────────
    texto_para_embedding = (
        f"{extracted_data.get('sintoma_reportado', '')} "
        f"{extracted_data.get('diagnostico_real', '')}"
    ).strip()
    
    try:
        embedding_response = await client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=texto_para_embedding,
            config=genai.types.EmbedContentConfig(output_dimensionality=768)
        )
        embedding_vector = embedding_response.embeddings[0].values
        logger.info("[RAG] ✅ Embedding generado (%d dimensiones)", len(embedding_vector))
    except Exception as e:
        logger.error("[RAG] Error generando embedding: %s", e)
        embedding_vector = []
    
    # ── PASO 3: Crear registro y persistir ────────────────────────────────
    record = RepairRecord(
        categoria=extracted_data.get("categoria", "Otro"),
        marca_modelo=extracted_data.get("marca_modelo", "No especificado"),
        sintoma_reportado=extracted_data.get("sintoma_reportado", "No especificado"),
        diagnostico_real=extracted_data.get("diagnostico_real", "No especificado"),
        solucion_aplicada=extracted_data.get("solucion_aplicada", "No especificado"),
        embedding=list(embedding_vector),
    )
    
    record_dict = record.model_dump()
    
    # ── INTENTO 1: Guardar en Firestore ───────────────────────────────────
    db = _get_firestore_client()
    saved_to_cloud = False
    if db is not None:
        try:
            from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
            from google.cloud.firestore_v1 import FieldFilter
            # Firestore necesita el embedding como Vector
            firestore_data = {
                **record_dict,
                "embedding": record_dict["embedding"],  # Firestore lo almacena como array nativo
            }
            await db.collection(_FIRESTORE_COLLECTION).document(record.id_reparacion).set(firestore_data)
            logger.info("[RAG] ☁️ Reparación guardada en Firestore: %s", record.id_reparacion)
            saved_to_cloud = True
        except Exception as e:
            logger.warning("[RAG] Error guardando en Firestore, cayendo a local: %s", e)
    
    # ── FALLBACK: Guardar en JSON local ───────────────────────────────────
    if not saved_to_cloud:
        kb = _load_knowledge_base_local()
        kb.append(record_dict)
        _save_knowledge_base_local(kb)
        logger.info("[RAG] 💾 Reparación guardada localmente: %s", record.id_reparacion)
    
    return {
        "status": "GUARDADO",
        "storage": "Firestore" if saved_to_cloud else "local_json",
        "id_reparacion": record.id_reparacion,
        "categoria": record.categoria,
        "marca_modelo": record.marca_modelo,
    }


# ─── FLUJO DE LECTURA ────────────────────────────────────────────────────────

async def search_similar_repairs(current_symptom: str, top_k: int = 3) -> dict:
    """
    Busca reparaciones similares en la base de conocimiento.
    
    Intenta Firestore Vector Search (find_nearest) primero.
    Si falla, cae a búsqueda local por cosine similarity.
    """
    logger.info("[RAG] Buscando experiencias similares para: '%s'", current_symptom[:80])
    
    client = _get_client()
    
    # ── PASO 1: Generar embedding del síntoma actual ──────────────────────
    try:
        embedding_response = await client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=current_symptom,
            config=genai.types.EmbedContentConfig(output_dimensionality=768)
        )
        query_embedding = list(embedding_response.embeddings[0].values)
        logger.info("[RAG] Embedding de consulta generado (%d dims)", len(query_embedding))
    except Exception as e:
        logger.error("[RAG] Error generando embedding de consulta: %s", e)
        return {
            "status": "ERROR_EMBEDDING",
            "resultados": [],
            "contexto_formateado": f"Error al generar embedding: {e}",
        }
    
    # ── PASO 2A: Firestore Vector Search (PRIORITARIO) ────────────────────
    db = _get_firestore_client()
    if db is not None:
        try:
            from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
            from google.cloud.firestore_v1.vector import Vector
            
            collection_ref = db.collection(_FIRESTORE_COLLECTION)
            
            vector_query = collection_ref.find_nearest(
                vector_field="embedding",
                query_vector=Vector(query_embedding),
                distance_measure=DistanceMeasure.COSINE,
                limit=top_k,
            )
            
            top_results = []
            async for doc in vector_query.stream():
                data = doc.to_dict()
                # Firestore COSINE distance: 0 = identical, 2 = opposite
                # Convertir a similarity: 1 - (distance / 2)
                distance = getattr(doc, 'distance', None) or 0.0
                score = 1.0 - (distance / 2.0)
                if score >= 0.5:  # MIN_SCORE
                    top_results.append((score, data))
            
            if top_results:
                logger.info("[RAG] ☁️ Firestore Vector Search: %d resultados encontrados", len(top_results))
                return _format_results(top_results, source="Firestore Vector Search")
            else:
                logger.info("[RAG] Firestore Vector Search: sin resultados con score >= 0.5")
                
        except Exception as e:
            logger.warning("[RAG] Firestore Vector Search falló, cayendo a local: %s", e)
    
    # ── PASO 2B: FALLBACK — Búsqueda local por cosine similarity ──────────
    return _search_local_fallback(query_embedding, top_k)


def _search_local_fallback(query_embedding: list[float], top_k: int) -> dict:
    """Búsqueda local por cosine similarity (fallback si Firestore no está disponible)."""
    kb = _load_knowledge_base_local()
    
    if not kb:
        logger.info("[RAG] Base de conocimiento local vacía.")
        return {
            "status": "SIN_DATOS",
            "resultados": [],
            "contexto_formateado": "No hay experiencias previas registradas en la base de conocimiento.",
        }
    
    records_with_embeddings = [r for r in kb if r.get("embedding") and len(r["embedding"]) > 0]
    
    if not records_with_embeddings:
        return {
            "status": "SIN_EMBEDDINGS",
            "resultados": [],
            "contexto_formateado": "Los registros existentes no tienen embeddings generados.",
        }
    
    scored_records = []
    for record in records_with_embeddings:
        score = _cosine_similarity(query_embedding, record["embedding"])
        scored_records.append((score, record))
    
    scored_records.sort(key=lambda x: x[0], reverse=True)
    
    MIN_SCORE = 0.5
    top_results = [
        (score, record)
        for score, record in scored_records[:top_k]
        if score >= MIN_SCORE
    ]
    
    if not top_results:
        logger.info("[RAG] Ningún resultado local superó el umbral de similitud (0.5).")
        return {
            "status": "SIN_SIMILARES",
            "resultados": [],
            "contexto_formateado": "No se encontraron experiencias previas lo suficientemente similares.",
        }
    
    logger.info("[RAG] 💾 Búsqueda local: %d resultados encontrados", len(top_results))
    return _format_results(top_results, source="local_json")


def _format_results(top_results: list[tuple], source: str = "unknown") -> dict:
    """Formatea los resultados para inyección en Gemini Live."""
    formatted_blocks = []
    resultados_lista = []
    
    for i, (score, record) in enumerate(top_results, 1):
        block = (
            f"━━━ CASO HISTÓRICO #{i} (Relevancia: {score:.0%}) ━━━\n"
            f"📋 Categoría: {record.get('categoria', 'N/A')}\n"
            f"🔧 Equipo: {record.get('marca_modelo', 'N/A')}\n"
            f"💬 Síntoma Original: {record.get('sintoma_reportado', 'N/A')}\n"
            f"🔍 Diagnóstico Real: {record.get('diagnostico_real', 'N/A')}\n"
            f"✅ Solución Aplicada: {record.get('solucion_aplicada', 'N/A')}\n"
            f"📅 Fecha: {record.get('timestamp', 'N/A')}\n"
        )
        formatted_blocks.append(block)
        resultados_lista.append({
            "score": round(score, 3),
            "categoria": record.get("categoria"),
            "marca_modelo": record.get("marca_modelo"),
            "sintoma": record.get("sintoma_reportado"),
            "diagnostico": record.get("diagnostico_real"),
            "solucion": record.get("solucion_aplicada"),
        })
    
    contexto_final = (
        "[EXPERIENCIAS REALES DE TÉCNICOS — BASE DE CONOCIMIENTO COLECTIVA]\n"
        f"(Fuente: {source})\n"
        "Los siguientes casos fueron resueltos exitosamente por otros técnicos del equipo. "
        "Úsalos como referencia para guiar tu diagnóstico actual, pero SIEMPRE verifica "
        "que el contexto aplique al caso específico del técnico.\n\n"
        + "\n".join(formatted_blocks)
    )
    
    return {
        "status": "ENCONTRADO",
        "source": source,
        "resultados": resultados_lista,
        "contexto_formateado": contexto_final,
    }
