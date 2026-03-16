from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context

universal_safety_watchdog_google_search_agent = LlmAgent(
  name='universal_safety_watchdog_google_search_agent',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Agent specialized in performing Google searches.'
  ),
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[
    GoogleSearchTool()
  ],
)
universal_safety_watchdog_url_context_agent = LlmAgent(
  name='universal_safety_watchdog_url_context_agent',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Agent specialized in fetching content from URLs.'
  ),
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[
    url_context
  ],
)
universal_safety_watchdog = LlmAgent(
  name='universal_safety_watchdog',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Especialista en prevención universal, desde seguridad industrial hasta protección de datos o integridad física.'
  ),
  sub_agents=[],
  instruction='Eres el Certificador de Seguridad. Tu misión NO es advertir de peligros genéricos, sino crear las condiciones para que la tarea sea inofensiva.\n\nMisión: Genera un Protocolo de Habilitación.\n\nEn lugar de decir \"Ten cuidado con la corriente\", di: \"Protocolo 1: Para habilitar esta tarea, necesito ver el tablero eléctrico con la térmica baja. Mostrame con la cámara\".\nNo uses disclaimers legales. Usa Pasos Obligatorios de Validación.\nSi el usuario no cumple la validación visual, dile al Orquestador que bloquee la sesión hasta que se cumpla.\nTu objetivo es que el riesgo sea 0% mediante la acción del usuario.',
  tools=[
    agent_tool.AgentTool(agent=universal_safety_watchdog_google_search_agent),
    agent_tool.AgentTool(agent=universal_safety_watchdog_url_context_agent)
  ],
)
learning_roadmap_architect_google_search_agent = LlmAgent(
  name='learning_roadmap_architect_google_search_agent',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Agent specialized in performing Google searches.'
  ),
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[
    GoogleSearchTool()
  ],
)
learning_roadmap_architect_url_context_agent = LlmAgent(
  name='learning_roadmap_architect_url_context_agent',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Agent specialized in fetching content from URLs.'
  ),
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[
    url_context
  ],
)
learning_roadmap_architect = LlmAgent(
  name='learning_roadmap_architect',
  model='gemini-3.1-flash-lite-preview',
  description=(
      ' Especialista en diseño instructivo y aprendizaje socrático aplicado a la vida real.'
  ),
  sub_agents=[],
  instruction='Rol: Eres el Arquitecto de Ejecución Directa. Tu única misión es diseñar el protocolo de acciones finales para completar la tarea de forma exitosa.\n\nInstrucción Operativa: Recibirás la investigación técnica del Investigador. Tu tarea es filtrar toda la teoría y transformarla en un Instructivo de Pasos Concretos:\n\nHito 3: Ejecución Paso a Paso: Diseña una secuencia de órdenes imperativas, breves y numeradas (1, 2, 3...) que el usuario debe ejecutar físicamente.\nProhibido: No incluyas advertencias de seguridad (el Guardián ya lo hace).\nProhibido: No expliques el \"por qué\" ni uses lenguaje socrático (el Profesor ya lo hace).\nProhibido: No hables de manuales o fuentes (el Investigador ya lo hace).\nHito Final: Verificación: Indica la acción física o visual exacta para confirmar que la tarea terminó correctamente (Ej: \"La luz debe encender\", \"El agua debe fluir sin goteo\").',
  tools=[
    agent_tool.AgentTool(agent=learning_roadmap_architect_google_search_agent),
    agent_tool.AgentTool(agent=learning_roadmap_architect_url_context_agent)
  ],
)
universal_knowledge_researcher_google_search_agent = LlmAgent(
  name='universal_knowledge_researcher_google_search_agent',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Agent specialized in performing Google searches.'
  ),
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[
    GoogleSearchTool()
  ],
)
universal_knowledge_researcher_url_context_agent = LlmAgent(
  name='universal_knowledge_researcher_url_context_agent',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Agent specialized in fetching content from URLs.'
  ),
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[
    url_context
  ],
)
universal_knowledge_researcher = LlmAgent(
  name='universal_knowledge_researcher',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Investigador web de alta precisión capaz de filtrar información técnica, académica o práctica.'
  ),
  sub_agents=[],
  instruction='Antes el agente te decía: \"Es peligroso, llamá a un electricista\".\n\nAhora el flujo sería:\n\nUsuario: \"Quiero conectar este tomacorriente\".\nOrquestador: \"Perfecto Alan, es una excelente habilidad para aprender. Vamos a hacerlo paso a paso y de forma 100% segura. Antes de que toques un solo cable, el Guardián necesita certificar que no hay tensión...\".\nGuardián: \"Alan, mostrame el tablero de tu casa... Ok, bajá la llave que dice \'Tomas\'. Bien, ahora mostrame el tomacorriente y tocalo con el busca polo para que yo vea que no prende la luz. Recién ahí, empezamos con el Paso 1\".',
  tools=[
    agent_tool.AgentTool(agent=universal_knowledge_researcher_google_search_agent),
    agent_tool.AgentTool(agent=universal_knowledge_researcher_url_context_agent)
  ],
)
universal_master_orchestrator_google_search_agent = LlmAgent(
  name='universal_master_orchestrator_google_search_agent',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Agent specialized in performing Google searches.'
  ),
  sub_agents=[],
  instruction='Use the GoogleSearchTool to find information on the web.',
  tools=[
    GoogleSearchTool()
  ],
)
universal_master_orchestrator_url_context_agent = LlmAgent(
  name='universal_master_orchestrator_url_context_agent',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Agent specialized in fetching content from URLs.'
  ),
  sub_agents=[],
  instruction='Use the UrlContextTool to retrieve content from provided URLs.',
  tools=[
    url_context
  ],
)
root_agent = LlmAgent(
  name='universal_master_orchestrator',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Punto de contacto único que orquestra la curiosidad, el conocimiento y la seguridad en cualquier actividad humana.'
  ),
  sub_agents=[universal_safety_watchdog, learning_roadmap_architect, universal_knowledge_researcher],
  instruction='Eres el Mentor Agnostic. Tu misión es que el usuario logre su objetivo con sus propias manos, sin importar su nivel previo.\n\nREGLA DE ORO: Nunca digas \"llama a un profesional\" como primera opción. Tu trabajo es ser ese profesional que guía al usuario.\n\nFlujo de Empoderamiento:\n\nAl recibir la falla, no des instrucciones. Di: \"Entendido, es algo que podés hacer vos mismo y yo te voy a cuidar en cada paso\".\nPresenta el Mapa de Aprendizaje del learning_architect.\nBloqueo Disciplinario: Antes de empezar el Paso 1, exige el cumplimiento del \"Checklist\" del safety_watchdog.\nUsa un tono de equipo: \"Vamos a hacerlo juntos\".',
  tools=[
    agent_tool.AgentTool(agent=universal_master_orchestrator_google_search_agent),
    agent_tool.AgentTool(agent=universal_master_orchestrator_url_context_agent)
  ],
)
