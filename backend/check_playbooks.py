
from google.cloud import dialogflowcx_v3beta1 as dialogflow

def list_playbooks(agent_id):
    client = dialogflow.PlaybooksClient()
    parent = agent_id
    print(f"Buscando Playbooks en: {parent}")
    try:
        request = dialogflow.ListPlaybooksRequest(parent=parent)
        page_result = client.list_playbooks(request=request)
        for pb in page_result:
            print(f"PLAYBOOK: {pb.display_name} | ID: {pb.name}")
    except Exception as e:
        print(f"Error listando Playbooks: {e}")

if __name__ == "__main__":
    # Agnostic-Orchestrator in stok-7bc5c
    agent_id = "projects/stok-7bc5c/locations/global/agents/91e9d29a-b40e-4273-adef-d2af0c711cf6"
    list_playbooks(agent_id)
