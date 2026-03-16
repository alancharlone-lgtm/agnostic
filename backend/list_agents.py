
from google.cloud import discoveryengine_v1beta as discoveryengine
import sys

def list_engines(project_id):
    client = discoveryengine.EngineServiceClient()
    parent = f"projects/{project_id}/locations/global/collections/default_collection"
    
    print(f"Buscando motores en: {parent}")
    try:
        request = discoveryengine.ListEnginesRequest(parent=parent)
        page_result = client.list_engines(request=request)
        
        found = False
        for response in page_result:
            print(f"---")
            print(f"Nombre: {response.display_name}")
            print(f"ID completo: {response.name}")
            print(f"Tipo: {response.solution_type}")
            if "Orquestador_Principal_Reparaciones" in response.display_name:
                found = True
                print(">>> ¡ENCONTRADO! <<<")
        
        if not found:
            print("\nNo se encontró el agente con ese nombre exacto. Revisa si está en otra locación o tiene un nombre de display diferente.")
            
    except Exception as e:
        print(f"Error al listar: {e}")

if __name__ == "__main__":
    list_engines("stok-7bc5c")
