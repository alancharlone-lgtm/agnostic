
from google.cloud import dialogflowcx_v3 as dialogflow

def get_agent_details(agent_name):
    client = dialogflow.AgentsClient()
    try:
        agent = client.get_agent(name=agent_name)
        print(f"DISPLAY NAME: {agent.display_name}")
        print(f"DESCRIPTION: {agent.description}")
        print(f"TIME ZONE: {agent.time_zone}")
        
        # List flows
        flows_client = dialogflow.FlowsClient()
        flows = flows_client.list_flows(parent=agent_name)
        print("\nFLOWS:")
        for flow in flows:
            print(f"- {flow.display_name}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Agnostic-Orchestrator ID found earlier
    agent_id = "projects/stok-7bc5c/locations/global/agents/91e9d29a-b40e-4273-adef-d2af0c711cf6"
    get_agent_details(agent_id)
