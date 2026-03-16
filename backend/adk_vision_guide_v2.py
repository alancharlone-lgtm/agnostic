"""
adk_vision_guide_v2.py
Agente de Guía Visual con arquitectura Multi-Agente y conexión MCP.
CRÍTICO: Todos los agentes se crean dentro de get_vision_agent() (Factory Function)
para evitar el error de Pydantic "Agent already has a parent agent" en llamadas múltiples.

FLUJO DE HANDOFF DIRECTO:
  Orquestador -> Especialista (Analiza) -> Director Visual (Dibuja via MCP)
  Cada especialista tiene al Director Visual como herramienta, elimina el "teléfono descompuesto".
"""
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context

VISION_MODEL = "gemini-3.1-flash-lite-preview"


def get_vision_agent(drawing_tool=None) -> LlmAgent:
    """
    Factory Function: crea una instancia FRESCA del agente de visión y todos sus
    sub-agentes en cada invocación, evitando conflictos de Pydantic entre sesiones.
    drawing_tool: una herramienta (función) opcional para inyectar en el director visual.
    """

    # --- 1. SUB-AGENTE DE RENDERIZADO VISUAL ---
    def create_director():
        return LlmAgent(
            name='director_visual_inpainting',
            model=VISION_MODEL,
            description='Traduce el mapeo técnico en un prompt de edición para renderizar los cables conectados sobre la imagen original.',
            sub_agents=[],
            instruction=(
                'Eres un especialista en prompts de edición de imágenes técnicas.\n'
                'Recibirás el mapeo técnico de conexión de cables.\n\n'
                'TU TAREA (ejecutar en orden):\n'
                '1. Con el mapeo técnico que recibas, redacta un prompt de edición fotorrealista.\n'
                '   Formato: "Mantén el fondo intacto. Dibuja los cables conectándolos EXACTAMENTE: [Mapeo detallado]."\n'
                '   IMPORTANTE: Asegúrate de incluir y respetar todas las instrucciones de ubicación espacial que recibas (ej: "arriba a la izquierda", "en el centro del componente"). No asumas ubicaciones teóricas si el mapeo te da la ubicación visual exacta en la foto.\n'
                '2. EJECUCIÓN CRÍTICA: Llama a la herramienta `generar_guia_visual_nanobanana` con el prompt que redactaste.\n'
                '3. Devuelve el resultado final.'
            ),
            tools=[drawing_tool] if drawing_tool else [], # Inyectado desde el runner en main.py
        )

    # --- 2. SUB-AGENTES DE BÚSQUEDA (ELECTRICIDAD) ---
    _elec_google = LlmAgent(
        name='Especialista_Electrico_Normativo_google_search_agent',
        model=VISION_MODEL,
        description='Performs Google searches on electrical standards.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()],
    )

    _elec_url = LlmAgent(
        name='Especialista_Electrico_Normativo_url_context_agent',
        model=VISION_MODEL,
        description='Fetches content from URLs related to electrical standards.',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context],
    )

    # HANDOFF DIRECTO: cada uno tiene su propia instancia del director
    director_elec = create_director()
    especialista_electrico_normativo = LlmAgent(
        name='especialista_electrico_normativo',
        model=VISION_MODEL,
        description='Determinar la conexión exacta de componentes eléctricos y generar la guía visual.',
        sub_agents=[],
        instruction=(
            'Eres un experto senior en instalaciones eléctricas.\n'
            'Tu misión es: 1) analizar la imagen, 2) mapear los cables, y 3) disparar la generación de la guía visual.\n\n'
            'FILOSOFÍA DE TRABAJO:\n'
            '1. LÓGICA DE EXPERTO: Si las etiquetas (L, N) no se ven pero identificas el componente, '
            'deduce la conexión usando estándares industriales (normas AEA, IEC).\\n'
            '2. PROACTIVIDAD: No rechaces la imagen a menos que sea totalmente ilegible. Si podés intuir '
            'la conexión con un 90%+ de certeza, procedé.\\n'
            '3. PRECISIÓN ESPACIAL VISUAL (CRÍTICO): Si las letras o marcas no son legibles, describe detalladamente DÓNDE ESTÁN los bornes basándote en la pura imagen.\n'
            '   Ejemplo: "Conecta el cable marrón al borne superior izquierdo, arriba de la palanca negra" en vez de decir solo "al borne L".\n'
            '   Debes pasar SIEMPRE esta información espacial para asistir al modelo de dibujo que actuará ciego a letras pequeñas.\n'
            '4. PRECISIÓN DE MAPEO: Mapea cada color de cable a su borne (Fase, Neutro, Tierra) y suma tu ubicación visual espacial garantizada.\n'
            '5. SEGURIDAD: Mantén advertencias de seguridad, pero NO dejes que bloqueen la generación de la guía.\n\n'
            'PASO OBLIGATORIO FINAL (NO OPCIONAL):\n'
            'Una vez que tengas tu mapeo completo, DEBES LLAMAR INMEDIATAMENTE a la herramienta '
            '`director_visual_inpainting`, pasándole:\n'
            '  - El mapeo técnico detallado (ej: "Cable Marrón -> Borne L, Azul -> Borne N").\n'
            'NO DEVUELVAS EL RESULTADO COMO TEXTO. Llama a la herramienta. Esta llamada es OBLIGATORIA.'
        ),
        tools=[
            agent_tool.AgentTool(agent=_elec_google),
            agent_tool.AgentTool(agent=_elec_url),
            agent_tool.AgentTool(agent=director_elec),
        ],
    )

    # --- 3. SUB-AGENTES DE BÚSQUEDA (REFRIGERACIÓN) ---
    _hvac_google = LlmAgent(
        name='Especialista_Refrigeracion_HVAC_google_search_agent',
        model=VISION_MODEL,
        description='Performs Google searches on HVAC and refrigeration.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()],
    )

    _hvac_url = LlmAgent(
        name='Especialista_Refrigeracion_HVAC_url_context_agent',
        model=VISION_MODEL,
        description='Fetches content from URLs related to HVAC and refrigeration.',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context],
    )

    # HANDOFF DIRECTO: el especialista HVAC tiene su propia instancia del director
    director_hvac = create_director()
    especialista_refrigeracion_hvac = LlmAgent(
        name='especialista_refrigeracion_hvac',
        model=VISION_MODEL,
        description='Ingeniero experto en refrigeración y HVAC. Mapea componentes y genera la guía visual.',
        sub_agents=[],
        instruction=(
            'Eres un ingeniero experto en sistemas de refrigeración y HVAC.\n'
            'Tu misión es: 1) analizar la imagen, 2) mapear los bornes, y 3) disparar la generación de la guía visual.\n\n'
            'REGLAS:\n'
            '1. Identifica los bornes. Si es compresor: C (Común), S (Arranque), R (Trabajo).\n'
            '2. PRECISIÓN ESPACIAL VISUAL (CRÍTICO): Describe EXACTAMENTE dónde están físicamente en la foto. No confíes solo en las letras. Ejemplo: "Borne C (el pin superior del triángulo), Borne S (el pin inferior izquierdo)". Es vital para guiar al modelo de inpainting.\n'
            '3. Utiliza la búsqueda para encontrar el diagrama técnico exacto si es necesario.\n'
            '4. SI NO HAY MANUAL EXACTO: Usa el diagrama estándar y aclara que es una guía basada en estándares.\n\n'
            'PASO OBLIGATORIO FINAL (NO OPCIONAL):\n'
            'Una vez que tengas el mapeo completo, DEBES LLAMAR INMEDIATAMENTE a la herramienta '
            '`director_visual_inpainting`, pasándole:\n'
            '  - El mapeo técnico detallado.\n'
            'NO DEVUELVAS EL RESULTADO COMO TEXTO. Llama a la herramienta directamente.'
        ),
        tools=[
            agent_tool.AgentTool(agent=_hvac_google),
            agent_tool.AgentTool(agent=_hvac_url),
            agent_tool.AgentTool(agent=director_hvac),
        ],
    )

    # --- 4. ORQUESTADOR CENTRAL (ROOT) ---
    # Con el handoff directo, el Orquestador sólo necesita despachar al especialista correcto.
    return LlmAgent(
        name='Agnostic_Orquestador_Central',
        model=VISION_MODEL,
        description='Despachante visual principal. Identifica el dominio técnico y deriva al especialista.',
        sub_agents=[],
        instruction=(
            'Eres el Orquestador Central del sistema de asistencia técnica visual.\n\n'
            'TU ÚNICA MISIÓN: Analizar el frame e invocar al especialista correcto.\n\n'
            'FLUJO:\n'
            '1. Analiza la imagen. Identifica el tipo de componente (eléctrico vs refrigeración/HVAC).\n'
            '2. Si es ELÉCTRICO (cables, tomacorrientes, tableros): invoca `especialista_electrico_normativo`.\n'
            '3. Si es REFRIGERACIÓN/HVAC (compresor, capacitor, contactores): invoca `especialista_refrigeracion_hvac`.\n'
            '4. Pasa TODA la información al especialista: el texto descriptivo de la consulta.\n'
            'IMPORTANTE: El especialista se encargará de llamar al dibujante. Tu trabajo termina cuando derives la tarea.'
        ),
        tools=[
            agent_tool.AgentTool(agent=especialista_electrico_normativo),
            agent_tool.AgentTool(agent=especialista_refrigeracion_hvac),
        ],
    )


# Alias para código que importe directamente root_agent
root_agent = get_vision_agent()
