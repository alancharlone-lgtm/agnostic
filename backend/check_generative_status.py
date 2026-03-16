
from google.cloud import dialogflowcx_v3 as dialogflow

def check_agent_generative(agent_id):
    client = dialogflow.AgentsClient()
    try:
        agent = client.get_agent(name=agent_id)
        print(f"Agente: {agent.display_name}")
        # Check for answer generation settings
        if hasattr(agent, 'answer_generation_settings') and agent.answer_generation_settings:
            print(">>> ES UN AGENTE GENERATIVO (VERTEX AI AGENT)")
        else:
            print("Parece un agente de Dialogflow CX tradicional.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    agent_id = "projects/stok-7bc5c/locations/global/agents/91e9d29a-b40e-4273-adef-d2af0c711cf6"
    check_agent_generative(agent_id)
