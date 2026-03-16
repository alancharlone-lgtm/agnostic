from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context


def get_repairs_agent():
    """
    Factory function que crea una instancia FRESCA del agente de reparaciones
    y todos sus sub-agentes en cada invocación.
    CRÍTICO: Los sub-agentes DEBEN instanciarse aquí adentro para evitar el
    error de Pydantic 'Agent already has a parent agent' en llamadas múltiples.
    """
    # --- Sub-agentes del Buscador Interno ---
    _buscador_google = LlmAgent(
        name='Buscador_Interno_Manuales_google_search_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in performing Google searches.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()],
    )
    _buscador_url = LlmAgent(
        name='Buscador_Interno_Manuales_url_context_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in fetching content from URLs.',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context],
    )
    buscador_interno_manuales = LlmAgent(
        name='buscador_interno_manuales',
        model='gemini-3.1-flash-lite-preview',
        description=(
            'Úsalo SIEMPRE como tu PRIMERA OPCIÓN cuando necesites buscar manuales oficiales, códigos de error o diagramas de reparación. Este agente busca EXCLUSIVAMENTE en la base de datos privada e interna de la empresa.'
        ),
        sub_agents=[],
        instruction='Eres el experto en documentación interna. Tu tarea es buscar en los manuales oficiales de la empresa usando la marca, el modelo y el síntoma proporcionado.\nSi encuentras la solución, enumera los pasos de forma clara y técnica.\nSi no encuentras información sobre ese modelo exacto en tu base de datos, responde ÚNICAMENTE esto: "Documento no encontrado en base interna". No intentes adivinar ni dar consejos generales.',
        tools=[
            agent_tool.AgentTool(agent=_buscador_google),
            agent_tool.AgentTool(agent=_buscador_url)
        ],
    )

    # --- Sub-agentes del Explorador Web de Manuales ---
    _explorador_google = LlmAgent(
        name='El_Explorador_de_Manuales_Web_google_search_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in performing Google searches.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()],
    )
    _explorador_url = LlmAgent(
        name='El_Explorador_de_Manuales_Web_url_context_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in fetching content from URLs.',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context],
    )
    el_explorador_de_manuales_web = LlmAgent(
        name='el_explorador_de_manuales_web',
        model='gemini-3.1-flash-lite-preview',
        description=(
            'Busca manuales y guías de reparación en sitios web externos y públicos.'
        ),
        sub_agents=[],
        instruction='Eres un investigador web especializado en documentación técnica. Tu objetivo es buscar en internet el manual de usuario, manual de servicio o esquemas del electrodoméstico solicitado (Marca y Modelo).\nUtiliza tus herramientas de búsqueda para encontrar PDFs públicos o páginas de soporte oficiales.\nExtrae la respuesta al problema del usuario citando la fuente web de donde sacaste la información.',
        tools=[
            agent_tool.AgentTool(agent=_explorador_google),
            agent_tool.AgentTool(agent=_explorador_url)
        ],
    )

    # --- Sub-agentes del Investigador de Fallas Web ---
    _investigador_google = LlmAgent(
        name='Investigador_Fallas_Web_google_search_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in performing Google searches.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()],
    )
    _investigador_url = LlmAgent(
        name='Investigador_Fallas_Web_url_context_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in fetching content from URLs.',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context],
    )
    investigador_fallas_web = LlmAgent(
        name='investigador_fallas_web',
        model='gemini-3.1-flash-lite-preview',
        description=(
            'Busca fallas comunes, defectos de fábrica y problemas típicos en foros y comunidades online de técnicos.'
        ),
        sub_agents=[],
        instruction='Eres un técnico veterano que conoce los "secretos del oficio". Tu objetivo es buscar en internet cuáles son las fallas recurrentes o los defectos de fábrica más comunes para un modelo y marca específicos.\nBusca en foros de reparación, videos de técnicos y comunidades online.\nResume cuáles son las 2 o 3 piezas que más se rompen asociadas al síntoma que reporta el usuario y qué recomiendan revisar primero los técnicos en la web.',
        tools=[
            agent_tool.AgentTool(agent=_investigador_google),
            agent_tool.AgentTool(agent=_investigador_url)
        ],
    )

    # --- AGENTE PARALELO: Explorador Web + Investigador de Fallas (se ejecutan simultáneamente) ---
    # Se activa cuando el buscador interno no encuentra documentación.
    # Ambos agentes trabajan al mismo tiempo para reducir la latencia total a la mitad.
    busqueda_web_paralela = ParallelAgent(
        name='busqueda_web_paralela',
        description=(
            'Úsalo cuando el buscador_interno_manuales no encuentre documentación. '
            'Ejecuta en PARALELO la búsqueda de manuales web Y la investigación de fallas '
            'comunes, reduciendo el tiempo de respuesta a la mitad.'
        ),
        sub_agents=[el_explorador_de_manuales_web, investigador_fallas_web],
    )

    # --- Sub-agentes propios del Orquestador Principal ---
    _orq_google = LlmAgent(
        name='Orquestador_Principal_Reparaciones_google_search_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in performing Google searches.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()],
    )
    _orq_url = LlmAgent(
        name='Orquestador_Principal_Reparaciones_url_context_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in fetching content from URLs.',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context],
    )

    return LlmAgent(
        name='Orquestador_Principal_Reparaciones',
        model='gemini-3.1-flash-lite-preview',
        description=(
            'Punto de entrada principal. Coordina las solicitudes del técnico, recibe la marca y modelo del artefacto, y delega la búsqueda de información a los agentes especializados.'
        ),
        sub_agents=[buscador_interno_manuales, busqueda_web_paralela],
        instruction=(
            'Eres el Supervisor de Taller. Tu objetivo es coordinar la asistencia técnica. '
            'Recibirás consultas que incluirán obligatoriamente la Marca, el Modelo del artefacto y el problema o síntoma.\n\n'
            'REGLAS DE FLUJO DE TRABAJO (seguir en orden estricto):\n\n'
            '0. ANTES DE TODO: Si el sistema tiene una BASE DE CONOCIMIENTO COLECTIVA con experiencias '
            'previas de otros técnicos, inclúyelas en tu análisis. Estas experiencias reales del equipo '
            'son tan valiosas como la documentación oficial.\n\n'
            '1. SIEMPRE llama primero al agente buscador_interno_manuales. Nunca saltes este paso.\n\n'
            '2. Si buscador_interno_manuales responde "Documento no encontrado en base interna", '
            'DEBES llamar al agente busqueda_web_paralela. Este agente buscará en PARALELO '
            'manuales en la web Y las fallas más comunes, dándote ambas respuestas al mismo tiempo.\n\n'
            '3. Combina los resultados de ambos sub-agentes de busqueda_web_paralela en una única '
            'respuesta estructurada: primero el procedimiento del manual y luego las fallas típicas '
            'conocidas por los técnicos.\n\n'
            'REGLA DE ORO: NUNCA inventes pasos de reparación. Usa siempre la información que te '
            'devuelven tus sub-agentes. Resume la respuesta para que sea fácil de escuchar por voz.'
        ),
        tools=[
            agent_tool.AgentTool(agent=_orq_google),
            agent_tool.AgentTool(agent=_orq_url)
        ],
    )


# Backward-compatible alias for any code that still imports root_agent
root_agent = get_repairs_agent()
