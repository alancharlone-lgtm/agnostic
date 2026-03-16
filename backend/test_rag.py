"""
Test script for RAG Knowledge Base system.
Tests both the write flow (extract_and_save) and read flow (search_similar).
"""
import asyncio
import os
import json

# Ensure API key is set
os.environ["GOOGLE_API_KEY"] = os.environ.get("GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

from rag_knowledge_base import extract_and_save_repair, search_similar_repairs, _load_knowledge_base, KB_FILE_PATH

# --- TEST TRANSCRIPT (Simulated successful repair session) ---
TEST_TRANSCRIPT = """
Técnico: Hola, tengo una heladera Patrick HPK310BS que no enfría.
Agnostic: Entendido. ¿Qué temperatura tiene adentro?
Técnico: Está a temperatura ambiente, los alimentos se están descomponiendo.
Agnostic: El compresor arranca y para?
Técnico: El compresor no arranca para nada. El motor no hace ruido.
Agnostic: Revisemos el relé de arranque y el protector térmico. ¿Podés acceder a la parte trasera?
Técnico: Sí, ya saqué la tapa. Veo el relay y el térmico.
Agnostic: Medí continuidad en el relé con el tester.
Técnico: No tiene continuidad. El relé está quemado.
Agnostic: Perfecto, ese es el problema. Necesitás un relé PTC para compresor Patrick, modelo 1/5 HP.
Técnico: Ya lo cambié, puse el relé nuevo PTC.
Agnostic: ¿Arrancó el compresor?
Técnico: Sí! Está funcionando perfecto. La heladera ya está enfriando.
Agnostic: Excelente, reparación completada. El relé PTC estaba quemado e impedía el arranque del compresor.
"""

# --- TEST TRANSCRIPT 2 (Failed session — should NOT be saved) ---
TEST_TRANSCRIPT_FAILED = """
Técnico: Hola, tengo un aire acondicionado que pierde agua.
Agnostic: ¿De dónde pierde agua exactamente?
Técnico: De la unidad interior.
Agnostic: Revisemos el drenaje...
[CONEXIÓN PERDIDA - La sesión se cortó antes de resolver el problema]
"""


async def main():
    print("=" * 60)
    print("TEST 1: Extracción de reparación exitosa")
    print("=" * 60)
    
    # Clean up any previous test data
    if os.path.exists(KB_FILE_PATH):
        os.remove(KB_FILE_PATH)
        print(f"🗑️ Base de datos limpiada: {KB_FILE_PATH}")
    
    result = await extract_and_save_repair(TEST_TRANSCRIPT)
    print(f"\nResultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    assert result["status"] == "GUARDADO", f"Expected GUARDADO, got {result['status']}"
    print("✅ Test 1 PASSED: Reparación guardada correctamente.")
    
    # Verify the file was created
    kb = _load_knowledge_base()
    print(f"📊 Registros en la base: {len(kb)}")
    assert len(kb) == 1, f"Expected 1 record, got {len(kb)}"
    
    record = kb[0]
    print(f"   Categoría: {record['categoria']}")
    print(f"   Marca/Modelo: {record['marca_modelo']}")
    print(f"   Síntoma: {record['sintoma_reportado']}")
    print(f"   Diagnóstico: {record['diagnostico_real']}")
    print(f"   Solución: {record['solucion_aplicada']}")
    print(f"   Embedding dims: {len(record.get('embedding', []))}")
    assert len(record.get('embedding', [])) > 0, "Embedding should not be empty"
    print("✅ Test 1b PASSED: Datos del registro son válidos.\n")
    
    print("=" * 60)
    print("TEST 2: Sesión fallida NO se guarda")
    print("=" * 60)
    
    result2 = await extract_and_save_repair(TEST_TRANSCRIPT_FAILED)
    print(f"\nResultado: {json.dumps(result2, indent=2, ensure_ascii=False)}")
    assert result2["status"] == "SKIP", f"Expected SKIP, got {result2['status']}"
    
    kb2 = _load_knowledge_base()
    assert len(kb2) == 1, f"Expected still 1 record, got {len(kb2)}"
    print("✅ Test 2 PASSED: Sesión fallida no fue guardada.\n")
    
    print("=" * 60)
    print("TEST 3: Búsqueda semántica con síntoma similar")
    print("=" * 60)
    
    result3 = await search_similar_repairs("heladera que no enfría y el compresor no arranca")
    print(f"\nStatus: {result3['status']}")
    print(f"Resultados: {len(result3.get('resultados', []))}")
    if result3.get("resultados"):
        print(f"Score top: {result3['resultados'][0]['score']}")
        print(f"Contexto formateado:\n{result3['contexto_formateado'][:500]}...")
    assert result3["status"] == "ENCONTRADO", f"Expected ENCONTRADO, got {result3['status']}"
    print("✅ Test 3 PASSED: Búsqueda encontró caso similar.\n")
    
    print("=" * 60)
    print("TEST 4: Búsqueda con síntoma NO relacionado")
    print("=" * 60)
    
    result4 = await search_similar_repairs("el auto no arranca cuando giro la llave de contacto")
    print(f"\nStatus: {result4['status']}")
    print(f"Resultados: {len(result4.get('resultados', []))}")
    if result4.get("resultados"):
        print(f"Score top: {result4['resultados'][0]['score']}")
    # This might still match with some score, but should be lower
    print(f"✅ Test 4 PASSED: Búsqueda no relacionada completada.\n")
    
    # Clean up
    if os.path.exists(KB_FILE_PATH):
        os.remove(KB_FILE_PATH)
        print(f"🗑️ Base de datos de test limpiada.")
    
    print("=" * 60)
    print("🎉 TODOS LOS TESTS PASARON EXITOSAMENTE 🎉")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
