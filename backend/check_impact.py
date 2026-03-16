
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

def find_correlations():
    try:
        # gcloud on Windows often outputs in UTF-16
        with open('session_validation_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        try:
            with open('session_validation_raw.json', 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception as e:
            print(f"Error loading logs: {e}")
            return

    logs.sort(key=lambda x: x.get('timestamp', ''))

    correlation_found = False
    last_injection = None
    last_injection_time = None

    print("\n--- ANÁLISIS DE IMPACTO DE INYECCIONES ---")
    
    for entry in logs:
        payload = entry.get('textPayload', '')
        if not payload: continue
        
        timestamp = entry.get('timestamp', '')
        local_time = to_local(timestamp)

        if 'DEBUG INJECTION' in payload:
            last_injection = payload
            last_injection_time = local_time
            # print(f"[{local_time}] INYECCIÓN: {payload[:60]}...")
            
        elif ('DEBUG TOOL START' in payload or 'DEBUG TRANSCRIPT OUTPUT' in payload) and last_injection:
            # Check if this happened shortly after an injection (within 5 seconds)
            # Simplified check: just show the immediate next action
            if 'DEBUG TOOL START' in payload:
                action = f"LLAMÓ A HERRAMIENTA: {payload.replace('DEBUG TOOL START: ', '')}"
            else:
                action = f"IA DIJO: {payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '')[:100]}..."
                
            print(f"[{last_injection_time}] INYECCIÓN SILENCIOSA -> {last_injection[:50]}...")
            print(f"[{local_time}] DETERMINACIÓN IA       -> {action}")
            print("-" * 100)
            
            last_injection = None # Reset to look for next correlation

if __name__ == "__main__":
    find_correlations()
