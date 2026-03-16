
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.client_options import ClientOptions

def get_engine_by_id(project_id, engine_id):
    client = discoveryengine.EngineServiceClient()
    
    # Probamos variaciones del ID
    possible_ids = [engine_id, engine_id.replace('_', '-')]
    locations = ["global", "us-central1"]
    
    for loc in locations:
        for p_id in possible_ids:
            name = f"projects/{project_id}/locations/{loc}/collections/default_collection/engines/{p_id}"
            print(f"Probando Engine: {name}")
            try:
                # Intentamos obtenerlo directamente
                engine = client.get_engine(name=name)
                print(f"¡ENCONTRADO! Display Name: {engine.display_name}")
                return name
            except Exception as e:
                # print(f"  No encontrado: {e}")
                pass
    return None

if __name__ == "__main__":
    found = get_engine_by_id("stok-7bc5c", "agent_1771938686136")
    if not found:
        print("No se encontró el motor con las variaciones comunes de ID.")
