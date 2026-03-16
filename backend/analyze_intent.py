
import json
import datetime

def to_local(utc_str):
    try:
        utc_str = utc_str.replace('Z', '')
        if '.' in utc_str:
            base, frac = utc_str.split('.')
            frac = (frac + '000000')[:6]
            utc_str = f"{base}.{frac}"
        else:
            utc_str = f"{utc_str}.000000"
            
        dt = datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.%f')
        dt = dt - datetime.timedelta(hours=3)
        return dt.strftime('%H:%M:%S.%f')[:-3]
    except:
        return utc_str

def analyze_intent():
    try:
        with open('session_full_validation_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        try:
            with open('session_full_validation_raw.json', 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception as e:
            print(f"Error loading logs: {e}")
            return

    logs.sort(key=lambda x: x.get('timestamp', ''))

    print("\n--- CASOS DE ÉXITO: INYECCIÓN -> DETERMINACIÓN ---")
    
    pending_injection = None
    
    for i, entry in enumerate(logs):
        payload = entry.get('textPayload', '')
        if not payload: continue
        
        timestamp = entry.get('timestamp', '')
        local_time = to_local(timestamp)

        # Si es una inyección, la guardamos como "causa"
        if 'DEBUG INJECTION' in payload:
            pending_injection = (local_time, payload)
            continue
            
        # Si vemos una herramienta o una respuesta que mencione marcas/modelos/fallas tras una inyección
        if pending_injection:
            # Buscamos en los siguientes 15 segundos o 20 logs
            is_tool = 'DEBUG TOOL START' in payload
            is_transcript = 'DEBUG TRANSCRIPT OUTPUT' in payload
            
            if is_tool or is_transcript:
                inj_time, inj_text = pending_injection
                
                # Ejemplo de determinación: Llamar a prefetch o identificar máquina
                relevant = False
                if is_tool:
                    relevant = True # Toda tool tras inyección es relevante
                elif is_transcript:
                    # Si la IA menciona algo técnico que no dijo el usuario antes
                    if any(word in payload.lower() for word in ['heladera', 'patrick', 'bimetálico', 'resistencia', 'manual']):
                        relevant = True
                
                if relevant:
                    print(f" CAUSA: [{inj_time}] INYECCIÓN {inj_text[:40]}...")
                    if is_tool:
                        print(f" EFECTO: [{local_time}] HERRAMIENTA: {payload.replace('DEBUG TOOL START: ', '')}")
                    else:
                        print(f" EFECTO: [{local_time}] IA DIJO: {payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '')[:100]}...")
                    print("-" * 100)
                    
                    pending_injection = None # Marcamos como procesada

if __name__ == "__main__":
    analyze_intent()
