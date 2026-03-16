"""
init_gcp.py — Script de migración de datos locales a Google Cloud Firestore
============================================================================

Migra:
  1. repair_knowledge_base.json → Colección 'repair_knowledge_base' en Firestore
     (con embeddings generados via gemini-embedding-001)
  2. my_van_inventory.json → Colección 'van_inventory' en Firestore

Ejecución:
  cd backend
  python init_gcp.py

Requisitos:
  - pip install google-cloud-firestore google-genai
  - gcloud auth application-default login
  - Variable de entorno GOOGLE_API_KEY o GEMINI_API_KEY con tu clave de Gemini
"""

import json
import os
import sys
import asyncio
from pathlib import Path

# Fix Windows terminal encoding for emojis
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

GCP_PROJECT = os.environ.get("GCP_PROJECT", "stok-7bc5c")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
EMBEDDING_MODEL = "gemini-embedding-001"

REPAIR_KB_FILE = Path(__file__).parent / "repair_knowledge_base.json"
VAN_INVENTORY_FILE = Path(__file__).parent / "my_van_inventory.json"


async def migrate_repair_knowledge_base():
    """Migra repair_knowledge_base.json a Firestore con embeddings."""
    from google.cloud.firestore import AsyncClient
    from google import genai

    if not REPAIR_KB_FILE.exists():
        print(f"⚠️  {REPAIR_KB_FILE} no encontrado. Saltando migración de RAG.")
        return 0

    with open(REPAIR_KB_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not records:
        print("⚠️  repair_knowledge_base.json está vacío. Saltando.")
        return 0

    db = AsyncClient(project=GCP_PROJECT)
    client = genai.Client(api_key=GEMINI_API_KEY)
    collection = db.collection("repair_knowledge_base")
    migrated = 0

    print(f"\n📚 Migrando {len(records)} registros de RAG a Firestore...")

    for i, record in enumerate(records, 1):
        doc_id = record.get("id_reparacion", f"auto_{i}")

        # Regenerar embedding forzando limpieza (para usar text-embedding-004 a 768 dims)
        record["embedding"] = []
        embedding = []
        if not embedding:
            texto = f"{record.get('sintoma_reportado', '')} {record.get('diagnostico_real', '')}"
            try:
                from google.genai import types
                resp = await client.aio.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=texto.strip(),
                    config=types.EmbedContentConfig(output_dimensionality=768)
                )
                embedding = list(resp.embeddings[0].values)
                print(f"  🧠 [{i}/{len(records)}] Embedding generado ({len(embedding)} dims) para: {doc_id}")
            except Exception as e:
                print(f"  ❌ [{i}/{len(records)}] Error generando embedding: {e}")
                embedding = []

        firestore_data = {
            "id_reparacion": doc_id,
            "categoria": record.get("categoria", "Otro"),
            "marca_modelo": record.get("marca_modelo", "No especificado"),
            "sintoma_reportado": record.get("sintoma_reportado", ""),
            "diagnostico_real": record.get("diagnostico_real", ""),
            "solucion_aplicada": record.get("solucion_aplicada", ""),
            "embedding": embedding,
            "timestamp": record.get("timestamp", ""),
        }

        try:
            await collection.document(doc_id).set(firestore_data)
            migrated += 1
            print(f"  ☁️  [{i}/{len(records)}] {doc_id} → Firestore ✅")
        except Exception as e:
            print(f"  ❌ [{i}/{len(records)}] Error subiendo {doc_id}: {e}")

    print(f"\n✅ {migrated}/{len(records)} registros de RAG migrados a Firestore.")
    return migrated


async def migrate_van_inventory():
    """Migra my_van_inventory.json a Firestore."""
    from google.cloud.firestore import AsyncClient

    if not VAN_INVENTORY_FILE.exists():
        print(f"\n⚠️  {VAN_INVENTORY_FILE} no encontrado. Creando datos de ejemplo...")
        # Crear datos de ejemplo directamente en Firestore
        sample_inventory = {
            "capacitor 45uf": {"estado": "DISPONIBLE", "cantidad": 12, "ubicacion": "Cajón B3"},
            "termostato whirlpool": {"estado": "DISPONIBLE", "cantidad": 3, "ubicacion": "Cajón A1"},
            "placa electronica samsung": {"estado": "NO DISPONIBLE", "cantidad": 0, "ubicacion": None},
            "compresor lg": {"estado": "DISPONIBLE", "cantidad": 1, "ubicacion": "Cajón C7"},
            "bomba de desagote": {"estado": "NO DISPONIBLE", "cantidad": 0, "ubicacion": None},
            "resistencia calefactora": {"estado": "DISPONIBLE", "cantidad": 5, "ubicacion": "Cajón A3"},
            "termocupla k": {"estado": "DISPONIBLE", "cantidad": 8, "ubicacion": "Cajón B1"},
            "contactor schneider 25a": {"estado": "DISPONIBLE", "cantidad": 2, "ubicacion": "Cajón D2"},
        }
    else:
        with open(VAN_INVENTORY_FILE, "r", encoding="utf-8") as f:
            sample_inventory = json.load(f)

    db = AsyncClient(project=GCP_PROJECT)
    collection = db.collection("van_inventory")
    migrated = 0

    print(f"\n🚛 Migrando {len(sample_inventory)} ítems de inventario a Firestore...")

    for nombre, data in sample_inventory.items():
        doc_id = nombre.replace(" ", "_")
        firestore_data = {
            "nombre": nombre,
            "estado": data.get("estado", "NO DISPONIBLE"),
            "cantidad": data.get("cantidad", 0),
            "ubicacion": data.get("ubicacion"),
        }

        try:
            await collection.document(doc_id).set(firestore_data)
            migrated += 1
            estado_emoji = "✅" if data.get("estado") == "DISPONIBLE" else "❌"
            print(f"  {estado_emoji} {nombre} → Firestore ({data.get('estado')})")
        except Exception as e:
            print(f"  ❌ Error subiendo {nombre}: {e}")

    print(f"\n✅ {migrated}/{len(sample_inventory)} ítems de inventario migrados a Firestore.")
    return migrated


async def main():
    print("=" * 60)
    print("  AGNOSTIC — Migración de Datos Locales a Google Cloud")
    print(f"  Proyecto GCP: {GCP_PROJECT}")
    print("=" * 60)

    if not GEMINI_API_KEY:
        print("\n❌ ERROR: GEMINI_API_KEY o GOOGLE_API_KEY no está configurada.")
        print("   Ejecutá: set GEMINI_API_KEY=tu_clave_aqui")
        sys.exit(1)

    rag_count = await migrate_repair_knowledge_base()
    van_count = await migrate_van_inventory()

    print("\n" + "=" * 60)
    print("  RESUMEN DE MIGRACIÓN")
    print("=" * 60)
    print(f"  📚 RAG Knowledge Base: {rag_count} registros")
    print(f"  🚛 Van Inventory:      {van_count} ítems")
    print(f"  ☁️  Proyecto GCP:       {GCP_PROJECT}")
    print("=" * 60)
    print("\n🎉 ¡Migración completa! Los datos están en Firestore.")
    print("   Ahora podés deployar el backend a Cloud Run con confianza.\n")


if __name__ == "__main__":
    asyncio.run(main())
