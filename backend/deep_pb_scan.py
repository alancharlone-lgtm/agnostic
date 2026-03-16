
from google.cloud import dialogflowcx_v3beta1 as dialogflow

def list_all_playbooks(project_id):
    agents_client = dialogflow.AgentsClient()
    playbooks_client = dialogflow.PlaybooksClient()
    
    parent = f"projects/{project_id}/locations/global"
    print(f"Buscando agentes en {parent}...")
    try:
        agents = agents_client.list_agents(parent=parent)
        for agent in agents:
            print(f"\nAgente: {agent.display_name} ({agent.name})")
            try:
                pbs = playbooks_client.list_playbooks(parent=agent.name)
                for pb in pbs:
                    print(f"  PLAYBOOK: {pb.display_name} | {pb.name}")
                    if "Orquestador" in pb.display_name:
                        print("  >>> MATCH FOUND! <<<")
            except Exception as e:
                print(f"  No Playbooks found or error: {e}")
    except Exception as e:
        print(f"Error listando agentes: {e}")

if __name__ == "__main__":
    list_all_playbooks("stok-7bc5c")
