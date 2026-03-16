
from google.cloud import dialogflowcx_v3beta1 as dialogflow

def check_specific_agent(project_id, agent_id):
    client = dialogflow.AgentsClient()
    # Intentamos construir el resource name. 
    name = f"projects/{project_id}/locations/global/agents/{agent_id}"
    print(f"Intentando acceder a: {name}")
    
    try:
        agent = client.get_agent(name=name)
        print(f"CONECTADO EXITO!")
        print(f"Display Name: {agent.display_name}")
        return True
    except Exception as e:
        print(f"Error con ID en global: {e}")
        
    # Reintentar en us-central1
    try:
        name_us = f"projects/{project_id}/locations/us-central1/agents/{agent_id}"
        print(f"Intentando acceder a: {name_us}")
        # Regional endpoint for us-central1
        client_us = dialogflow.AgentsClient(client_options={"api_endpoint": "us-central1-dialogflow.googleapis.com"})
        agent = client_us.get_agent(name=name_us)
        print(f"CONECTADO EXITO EN US-CENTRAL1!")
        print(f"Display Name: {agent.display_name}")
        return True
    except Exception as e:
        print(f"Error con ID en us-central1: {e}")
    
    return False

if __name__ == "__main__":
    check_specific_agent("stok-7bc5c", "agent_1771938686136")
