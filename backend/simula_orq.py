import asyncio
import os
import sys

# Inyectamos de forma estricta la variable de entorno para que el SDK de google-genai no colapse
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

from main import consultar_especialistas_hogar

from main import consultar_especialistas_hogar

async def run_simulation():
    print("Iniciando simulador del Orquestador Pedagógico...")
    tarea = "Quiero aprender a cambiar el enchufe de la pared de mi cuarto que hace falso contacto."
    print(f"Tarea simulada: '{tarea}'\n")
    print("Consultando a los especialistas (esto puede tardar unos segundos)...")
    
    # We pass a distinct user_id to avoid conflicting with active sessions
    resultado = await consultar_especialistas_hogar(tarea_usuario=tarea, user_id="simulacion_test")
    
    print("\n" + "="*50)
    print("RESULTADO DEL ORQUESTADOR (DOSSIER PEDAGÓGICO):")
    print("="*50 + "\n")
    print(resultado.get('result', 'No se devolvió resultado.'))
    print("\n" + "="*50)

if __name__ == "__main__":
    asyncio.run(run_simulation())
