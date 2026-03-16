"""
ADK Sub-Agente de Experiencias Técnicas
========================================
Sub-agente que consulta la base de conocimiento colectiva de técnicos.
Se integra como sub-agente en los orquestadores de reparaciones (residential)
y el mentor universal (hogar).
"""

from google.adk.agents import LlmAgent
from google.adk.tools import agent_tool
from google.adk.tools.google_search_tool import GoogleSearchTool
from google.adk.tools import url_context


def get_experiencias_agent():
    """
    Factory function que crea una instancia del agente de experiencias técnicas.
    Este agente NO tiene herramientas propias — su único rol es formular
    la consulta correcta. La búsqueda real se hace vía la tool function
    en main.py (consultar_experiencias_tecnicas).
    """
    
    _exp_google = LlmAgent(
        name='experiencias_tecnicas_google_search_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in performing Google searches.',
        sub_agents=[],
        instruction='Use the GoogleSearchTool to find information on the web.',
        tools=[GoogleSearchTool()],
    )
    
    _exp_url = LlmAgent(
        name='experiencias_tecnicas_url_context_agent',
        model='gemini-3.1-flash-lite-preview',
        description='Agent specialized in fetching content from URLs.',
        sub_agents=[],
        instruction='Use the UrlContextTool to retrieve content from provided URLs.',
        tools=[url_context],
    )
    
    return LlmAgent(
        name='consultor_experiencias_tecnicas',
        model='gemini-3.1-flash-lite-preview',
        description=(
            'Consulta la BASE DE CONOCIMIENTO COLECTIVA de técnicos. '
            'Busca reparaciones previas similares al problema actual '
            'para enriquecer el diagnóstico con experiencia real del equipo.'
        ),
        sub_agents=[],
        instruction=(
            'Eres el Archivista de Experiencias del equipo técnico. '
            'Tu misión es buscar en la memoria colectiva del equipo si algún '
            'técnico ya enfrentó un problema similar al actual.\n\n'
            'FLUJO:\n'
            '1. Recibe el síntoma o problema reportado.\n'
            '2. Formula una consulta clara y concisa para la búsqueda semántica.\n'
            '3. Presenta los resultados destacando la solución aplicada.\n\n'
            'REGLAS:\n'
            '- Si hay experiencias previas, resúmelas técnicamente.\n'
            '- Si no hay experiencias, dilo claramente: "Sin experiencias previas para este caso".\n'
            '- NUNCA inventes experiencias que no existan en la base de datos.'
        ),
        tools=[
            agent_tool.AgentTool(agent=_exp_google),
            agent_tool.AgentTool(agent=_exp_url)
        ],
    )
