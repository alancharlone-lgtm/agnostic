
from google.cloud import discoveryengine_v1beta as discoveryengine

def try_converse(project_id, engine_id):
    client = discoveryengine.ConversationalSearchServiceClient()
    
    locations = ["global", "us", "eu"]
    for loc in locations:
        serving_config = f"projects/{project_id}/locations/{loc}/collections/default_collection/engines/{engine_id}/servingConfigs/default_config"
        print(f"Probando chat en: {serving_config}")
        
        try:
            request = discoveryengine.ConverseConversationRequest(
                name=serving_config,
                query=discoveryengine.TextInput(input="Hola"),
            )
            response = client.converse_conversation(request=request)
            print(f"¡RESPUESTA RECIBIDA en {loc}!")
            print(response.reply.reply)
            return True
        except Exception as e:
            # print(f"  Error: {e}")
            pass
    return False

if __name__ == "__main__":
    # Probamos con guion medio que es el estandar de API
    engine_id_clean = "agent-1771938686136"
    try_converse("stok-7bc5c", engine_id_clean)
    try_converse("stok-7bc5c", "agent_1771938686136")
