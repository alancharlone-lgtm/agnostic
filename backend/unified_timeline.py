
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

def unified_timeline():
    # gcloud outputs in UTF-16 on Windows usually
    try:
        with open('session_full_validation_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        with open('session_full_validation_raw.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)

    logs.sort(key=lambda x: x.get('timestamp', ''))

    print("\n--- LÍNEA DE TIEMPO INTEGRADA (Sesiones y Pings) ---")
    
    session_count = 0
    for entry in logs:
        payload = entry.get('textPayload', '')
        if not payload: continue
        
        local_time = to_local(entry.get('timestamp', ''))

        if 'V-LOOP: Iniciando' in payload:
            session_count += 1
            print(f"\n[SESIÓN #{session_count} INICIADA A LAS {local_time}]")
            print(f"{local_time} | FASE 1: V-LOOP (Arranque de 3 frames)")
            
        elif 'DEBUG INJECTION (NUDGE)' in payload:
            print(f"{local_time} | FASE 2: NUDGE (Ping de mantenimiento)")
            
        elif 'DEBUG TOOL START' in payload:
            print(f"{local_time} | IA ACTUANDO -> Herramienta: {payload.split('START: ')[-1]}")

if __name__ == "__main__":
    unified_timeline()
