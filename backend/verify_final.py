
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.client_options import ClientOptions

def verify_agent_access(project_id, agent_id):
    client_options = ClientOptions(api_endpoint="global-discoveryengine.googleapis.com")
    client = discoveryengine.EngineServiceClient(client_options=client_options)
    
    # Intento en global
    name = f"projects/{project_id}/locations/global/collections/default_collection/engines/{agent_id}"
    print(f"Verificando: {name}")
    try:
        engine = client.get_engine(name=name)
        print(f"EXITO!")
        print(f"Nombre: {engine.display_name}")
        print(f"Tipo: {engine.solution_type}")
        return True
    except Exception as e:
        print(f"Fallo en global: {e}")

    # Intento en us-central1
    try:
        name_us = f"projects/{project_id}/locations/us-central1/collections/default_collection/engines/{agent_id}"
        print(f"Verificando: {name_us}")
        client_us = discoveryengine.EngineServiceClient(
            client_options=ClientOptions(api_endpoint="us-central1-discoveryengine.googleapis.com")
        )
        engine = client_us.get_engine(name=name_us)
        print(f"EXITO EN US-CENTRAL1!")
        print(f"Nombre: {engine.display_name}")
        return True
    except Exception as e:
        print(f"Fallo en us-central1: {e}")
        
    return False

if __name__ == "__main__":
    verify_agent_access("stok-7bc5c", "agent_1771938686136")
