
from google.cloud import dialogflowcx_v3 as dialogflow
import sys

def list_cx_agents(project_id):
    client = dialogflow.AgentsClient()
    parent = f"projects/{project_id}/locations/global"
    
    print(f"Buscando agentes CX en: {parent}")
    try:
        request = dialogflow.ListAgentsRequest(parent=parent)
        page_result = client.list_agents(request=request)
        
        found = False
        for response in page_result:
            print(f"---")
            print(f"Nombre Mostrar: {response.display_name}")
            print(f"Resource Name: {response.name}")
            if "Orquestador_Principal_Reparaciones" in response.display_name:
                found = True
                print(">>> ¡ENCONTRADO EN DIALOGFLOW CX! <<<")
        
        if not found:
            # Reintentar en us-central1 por las dudas
            parent_us = f"projects/{project_id}/locations/us-central1"
            print(f"Buscando agentes CX en: {parent_us}")
            request = dialogflow.ListAgentsRequest(parent=parent_us)
            client_us = dialogflow.AgentsClient(client_options={"api_endpoint": "us-central1-dialogflow.googleapis.com"})
            page_result = client_us.list_agents(request=request)
            for response in page_result:
                print(f"---")
                print(f"Nombre Mostrar: {response.display_name}")
                print(f"Resource Name: {response.name}")
                if "Orquestador_Principal_Reparaciones" in response.display_name:
                    found = True
                    print(">>> ¡ENCONTRADO EN DIALOGFLOW CX (us-central1)! <<<")
            
        if not found:
             print("\nNo se encontró en Dialogflow CX (global/us-central1).")
            
    except Exception as e:
        print(f"Error al listar: {e}")

if __name__ == "__main__":
    list_cx_agents("stok-7bc5c")
