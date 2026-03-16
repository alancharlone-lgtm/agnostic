
from google.cloud import dialogflowcx_v3beta1 as dialogflow

def scan_playbooks_regional(project_id, location):
    client_options = {"api_endpoint": f"{location}-dialogflow.googleapis.com"}
    agents_client = dialogflow.AgentsClient(client_options=client_options)
    playbooks_client = dialogflow.PlaybooksClient(client_options=client_options)
    
    parent = f"projects/{project_id}/locations/{location}"
    print(f"Scanning Agents in {parent}...")
    try:
        agents = agents_client.list_agents(parent=parent)
        for agent in agents:
            print(f"AGENT: {agent.display_name} ({agent.name})")
            try:
                pbs = playbooks_client.list_playbooks(parent=agent.name)
                for pb in pbs:
                    print(f"  PLAYBOOK: {pb.display_name} | {pb.name}")
                    if "Orquestador" in pb.display_name:
                        print("  >>> MATCH FOUND! <<<")
            except Exception as e:
                print(f"  Error listando playbooks: {e}")
    except Exception as e:
        print(f"Error listando agentes en {location}: {e}")

if __name__ == "__main__":
    scan_playbooks_regional("stok-7bc5c", "us-central1")
    scan_playbooks_regional("stok-7bc5c", "global") # Repetimos global por si acaso
