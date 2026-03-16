from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context

# --- SUB-AGENTS DE BÚSQUEDA Y CONTEXTO ---

search_agent_instruction = 'Use the GoogleSearchTool to find precise information on the web. Focus on official sources and expert forums.'

url_agent_instruction = 'Use the UrlContextTool to retrieve and summarize content from provided URLs.'

# --- ESPECIALISTA EN INVESTIGACIÓN TÉCNICA ---

universal_knowledge_researcher_google_search_agent = LlmAgent(
  name='knowledge_researcher_search',
  model='gemini-3.1-flash-lite-preview',
  description='Agent specialized in performing Google searches for technical truth.',
  instruction=search_agent_instruction,
  tools=[GoogleSearchTool()],
)

universal_knowledge_researcher_url_context_agent = LlmAgent(
  name='knowledge_researcher_url',
  model='gemini-3.1-flash-lite-preview',
  description='Agent specialized in fetching content from URLs.',
  instruction=url_agent_instruction,
  tools=[url_context],
)

universal_knowledge_researcher = LlmAgent(
  name='universal_knowledge_researcher',
  model='gemini-3.1-flash-lite-preview',
  description='Investigador web de alta precisión. Provee la "verdad técnica" objetiva.',
  instruction=(
      'Eres el Investigador de Campo. Tu misión es buscar en la web información técnica precisa, '
      'manuales de usuario o guías de expertos sobre la tarea solicitada. '
      'Extrae: 1. Nombres correctos de las piezas/componentes involucrados. 2. Herramientas óptimas. '
      '3. Valores técnicos de referencia o advertencias de fabricantes. '
      'Resume todo en un informe técnico objetivo para el Orquestador. '
      'NO des consejos al usuario, solo provee datos duros y precisos.'
  ),
  tools=[
    agent_tool.AgentTool(agent=universal_knowledge_researcher_google_search_agent),
    agent_tool.AgentTool(agent=universal_knowledge_researcher_url_context_agent)
  ],
)

# --- ESPECIALISTA EN DISEÑO PEDAGÓGICO (ROADMAP) ---

learning_roadmap_architect_google_search_agent = LlmAgent(
  name='learning_architect_search',
  model='gemini-3.1-flash-lite-preview',
  description='Agent specialized in searching pedagogical patterns.',
  instruction=search_agent_instruction,
  tools=[GoogleSearchTool()],
)

learning_roadmap_architect_url_context_agent = LlmAgent(
  name='learning_architect_url',
  model='gemini-3.1-flash-lite-preview',
  description='Agent specialized in fetching content from URLs.',
  instruction=url_agent_instruction,
  tools=[url_context],
)

learning_roadmap_architect = LlmAgent(
  name='learning_roadmap_architect',
  model='gemini-3.1-flash-lite-preview',
  description='Especialista en diseño instructivo y aprendizaje socrático universal.',
  instruction=(
      'Eres el Arquitecto de Aprendizaje Socrático ("Gemini Learning Coach"). '
      'Tu objetivo NO es dar instrucciones directas de cómo arreglar algo, sino diseñar '
      'un camino de aprendizaje basado en preguntas interactivas, analogías simples y validación. '
      'La estructura de tu plan debe ser:\n'
      'Hito 1: La Pregunta Detonadora (Ej: ¿Sabés por qué la corriente necesita un camino cerrado?)\n'
      'Hito 2: Analogía Casera (Explicar el concepto usando agua, autos o cocina).\n'
      'Hito 3: Identificación Visual (Guiar al usuario a que encuentre la pieza por sí mismo haciéndole preguntas en vez de decirle dónde está).\n'
      'Hito 4: Acción con Reflexión (Ej: "Ahora que aflojaste eso, ¿qué creés que pasará con el cable?").\n'
      'Tu output es el Guion Pedagógico que usará el Mentor principal para charlar con el usuario.'
  ),
  tools=[
    agent_tool.AgentTool(agent=learning_roadmap_architect_google_search_agent),
    agent_tool.AgentTool(agent=learning_roadmap_architect_url_context_agent)
  ],
)

# --- ESPECIALISTA EN EJECUCIÓN DIRECTA (ÓRDENES) ---

direct_step_architect_google_search_agent = LlmAgent(
  name='direct_architect_search',
  model='gemini-3.1-flash-lite-preview',
  description='Agent specialized in searching factory repair sequences.',
  instruction=search_agent_instruction,
  tools=[GoogleSearchTool()],
)

direct_step_architect_url_context_agent = LlmAgent(
  name='direct_architect_url',
  model='gemini-3.1-flash-lite-preview',
  description='Agent specialized in fetching technical manual sequences.',
  instruction=url_agent_instruction,
  tools=[url_context],
)

direct_step_architect = LlmAgent(
  name='direct_step_architect',
  model='gemini-3.1-flash-lite-preview',
  description='Especialista en ejecución técnica directa y órdenes quirúrgicas.',
  instruction=(
      'Eres el Arquitecto de Acción Directa. Tu misión es diseñar el camino para realizar '
      'acciones concretas de forma inmediata.\n\n'
      'Estructura del Instructivo:\n'
      'Hito 1: Seguridad Bloqueante: Acción física obligatoria para eliminar riesgos (Ej: Desconectar energía, cerrar válvulas).\n'
      'Hito 2: Kit de Operación: Lista exacta de herramientas y materiales necesarios.\n'
      'Hito 3: Ejecución Técnica: La acción dividida en pasos imperativos, breves y numerados. '
      'PROHIBIDAS las preguntas o explicaciones teóricas. Solo órdenes directas para realizar la tarea.'
  ),
  tools=[
    agent_tool.AgentTool(agent=direct_step_architect_google_search_agent),
    agent_tool.AgentTool(agent=direct_step_architect_url_context_agent)
  ],
)

# --- ESPECIALISTA EN SEGURIDAD Y HABILITACIÓN ---

universal_safety_watchdog_google_search_agent = LlmAgent(
  name='safety_watchdog_search',
  model='gemini-3.1-flash-lite-preview',
  description='Agent specialized in searching safety regulations.',
  instruction=search_agent_instruction,
  tools=[GoogleSearchTool()],
)

universal_safety_watchdog_url_context_agent = LlmAgent(
  name='safety_watchdog_url',
  model='gemini-3.1-flash-lite-preview',
  description='Agent specialized in fetching safety protocols from URLs.',
  instruction=url_agent_instruction,
  tools=[url_context],
)

universal_safety_watchdog = LlmAgent(
  name='universal_safety_watchdog',
  model='gemini-3.1-flash-lite-preview',
  description='Certificador de Seguridad Universal. Crea las condiciones para el riesgo cero.',
  instruction=(
      'Eres el Certificador de Seguridad. Tu misión NO es advertir de peligros genéricos, '
      'sino crear las condiciones (Protocolos de Habilitación) para que la tarea sea inofensiva. '
      'Define requisitos obligatorios de validación visual (Ej: mostrar interruptor apagado a cámara, '
      'uso de EPP específico). Reporta tus protocolos al Orquestador Maestro para que los ponga al inicio del plan.'
  ),
  tools=[
    agent_tool.AgentTool(agent=universal_safety_watchdog_google_search_agent),
    agent_tool.AgentTool(agent=universal_safety_watchdog_url_context_agent)
  ],
)

# --- ORQUESTADOR MAESTRO (EL MENTOR AGNOSTIC) ---
# El Orquestador recibe los 3 especialistas como herramientas explícitas.
# Esto obliga al LLM a decidir cuándo y cómo llamar a cada uno,
# en lugar de usar sub_agents que el framework llama automáticamente.

root_agent = LlmAgent(
  name='universal_master_orchestrator',
  model='gemini-3.1-flash-lite-preview',
  description=(
      'Director Maestro del Dossier Pedagógico. Coordina a 3 especialistas y sintetiza su '
      'conocimiento en un plan de enseñanza completo para Gemini Live.'
  ),
  instruction=(
      'Eres el Mentor Agnostic Maestro. Tu rol es el de un DIRECTOR DE ORQUESTA: '
      'debes consultar a tus 3 especialistas y con lo que te dicen, armar un ÚNICO DOSSIER PEDAGÓGICO '
      'consolidado para que Gemini Live lo use para enseñar al usuario mientras trabaja.\n\n'
      'PROCESO OBLIGATORIO (sigue este orden exacto SIN saltear ningún paso):\n'
      '1. Llama a "universal_knowledge_researcher" con la tarea. LEE su respuesta completa.\n'
      '2. Llama a "universal_safety_watchdog" con la misma tarea. LEE su respuesta completa.\n'
      '3. Llama a "learning_roadmap_architect" con la misma tarea. LEE su respuesta completa.\n'
      '4. Solo después de tener los 3 reportes, escribe el DOSSIER FINAL usando EXACTAMENTE esta estructura:\n\n'
      '=== DOSSIER PEDAGÓGICO ===\n'
      'OBJETIVO: [nombre de la tarea]\n\n'
      'VERDAD TÉCNICA:\n[Contenido del reporte del investigador]\n\n'
      'PROTOCOLO DE SEGURIDAD:\n[Contenido del reporte del guardián. Indica que Gemini Live debe '
      'pedirle al usuario que muestre la térmica cortada visualmente ANTES de avanzar]\n\n'
      'PLAN DE CLASES:\n[Contenido del plan del arquitecto pedagógico]\n'
      '========================\n\n'
      'REGLAS ABSOLUTAS:\n'
      '- NUNCA entregues el Dossier sin haber llamado a los 3 especialistas.\n'
      '- NUNCA respondas al usuario directamente. Tu única salida válida es el DOSSIER FINAL.\n'
      '- Si un especialista no respondió, escribe "Sin datos" en esa sección pero NO te saltes la sección.'
  ),
  tools=[
    agent_tool.AgentTool(agent=universal_knowledge_researcher),
    agent_tool.AgentTool(agent=universal_safety_watchdog),
    agent_tool.AgentTool(agent=learning_roadmap_architect),
  ],
)

