
from google.cloud import dialogflowcx_v3beta1 as dialogflow

def scan_playbooks_in_all_agents(project_id):
    agents_client = dialogflow.AgentsClient()
    playbooks_client = dialogflow.PlaybooksClient()
    
    parent = f"projects/{project_id}/locations/global"
    print(f"Buscando agentes en {parent}...")
    try:
        agents = agents_client.list_agents(parent=parent)
        for agent in agents:
            print(f"\n--- Agente: {agent.display_name} ({agent.name}) ---")
            try:
                pbs = playbooks_client.list_playbooks(parent=agent.name)
                for pb in pbs:
                    print(f"  PLAYBOOK: {pb.display_name} | {pb.name}")
                    if "Orquestador" in pb.display_name or "Reparaciones" in pb.display_name:
                        print("  >>> POSIBLE MATCH ENCONTRADO! <<<")
            except Exception as e:
                print(f"  Error en este agente: {e}")
    except Exception as e:
        print(f"Error general: {e}")

if __name__ == "__main__":
    scan_playbooks_in_all_agents("stok-7bc5c")
