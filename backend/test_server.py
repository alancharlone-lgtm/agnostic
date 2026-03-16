import os
from dotenv import load_dotenv
load_dotenv()
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
import sys
sys.stdout.reconfigure(encoding='utf-8')

from fastapi import FastAPI
import uvicorn
from main import consultar_logistica_repuestos

app = FastAPI()

@app.get("/test_logistica")
async def test_logistica(repuesto: str = "bomba de desagote", marca: str = "Drean", equipo: str = "lavarropas"):
    print(f"Probando repuesto: {repuesto}, marca: {marca}, equipo: {equipo}")
    try:
        resultado = await consultar_logistica_repuestos(repuesto=repuesto, marca=marca, equipo=equipo, ubicacion_tecnico="-34.6037,-58.3816")
        return resultado
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
