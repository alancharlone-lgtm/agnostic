
from google.cloud import dialogflowcx_v3 as dialogflow

def deep_search_cx(project_id):
    client = dialogflow.AgentsClient()
    flows_client = dialogflow.FlowsClient()
    
    parent = f"projects/{project_id}/locations/global"
    print(f"Buscando en agentes CX en {parent}...")
    try:
        agents = client.list_agents(parent=parent)
        for agent in agents:
            print(f"\nChecking Agent: {agent.display_name} ({agent.name})")
            # Check flows
            try:
                flows = flows_client.list_flows(parent=agent.name)
                for flow in flows:
                    print(f"  Flow: {flow.display_name}")
                    if "Orquestador" in flow.display_name or "Reparaciones" in flow.display_name:
                         print("  >>> MATCH IN FLOW NAME! <<<")
            except: pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    deep_search_cx("stok-7bc5c")
