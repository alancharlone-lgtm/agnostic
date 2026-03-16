"""
adk_vision_precision.py
Agente especialista en detección de objetos con alta precisión.
Utiliza modelos de visión avanzados para extraer bounding boxes ceñidos.
"""
from google.adk.agents import LlmAgent
import os

# Usamos el modelo más capaz disponible para visión técnica
VISION_SPECIALIST_MODEL = "gemini-3.1-flash-lite-preview" 

def get_vision_precision_agent() -> LlmAgent:
    """
    Crea una instancia del Agente Especialista 'Eagle Eye'.
    Su única misión es devolver coordenadas exactas de componentes.
    """
    return LlmAgent(
        name='Eagle_Eye_Vision_Specialist',
        model=VISION_SPECIALIST_MODEL,
        description='Especialista en detección milimétrica de componentes en imágenes técnicas.',
        instruction=(
            'Eres "Eagle Eye", un agente de visión artificial de alta precisión para micro-mantenimiento.\n'
            'Recibirás una imagen y el nombre de un componente técnico.\n\n'
            'TU MISIÓN:\n'
            '1. Localiza el componente con precisión quirúrgica.\n'
            '2. El recuadro DEBE ser lo más ceñido posible a los bordes reales del objeto, sin márgenes de seguridad.\n'
            '3. Devuelve los resultados en una escala normalizada de 0 a 1000.\n\n'
            'FORMATO DE RESPUESTA (ESTRICTO JSON):\n'
            'Deberás responder ÚNICAMENTE con un JSON válido:\n'
            '{\n'
            '  "componente": "nombre_del_componente",\n'
            '  "coordenadas": [ymin, xmin, ymax, xmax]\n'
            '}\n\n'
            'Si el componente no es visible o hay ambigüedad total, responde:\n'
            '{"error": "No visible", "motivo": "Explicación breve"}'
        ),
        sub_agents=[],
        tools=[]
    )

root_agent = get_vision_precision_agent()
