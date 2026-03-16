
import json
import datetime

def to_local(utc_str):
    try:
        utc_str = utc_str.replace('Z', '')
        if '.' in utc_str:
            base, frac = utc_str.split('.')
            frac = (frac + '000000')[:6]
            utc_str = f"{base}.{frac}"
        dt = datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.%f')
        dt = dt - datetime.timedelta(hours=3)
        return dt.strftime('%H:%M:%S.%f')[:-3]
    except:
        return utc_str

def check_vloop_reaction():
    try:
        with open('final_session_audit.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        with open('final_session_audit.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)

    logs.sort(key=lambda x: x.get('timestamp', ''))

    vloop_start_time = None
    
    print("ANÁLISIS DE REACCIÓN INICIAL (V-LOOP)")
    print("-" * 100)
    
    for l in logs:
        payload = l.get('textPayload', '')
        if not payload: continue
        
        timestamp = l.get('timestamp', '')
        local_time = to_local(timestamp)
        
        # Detect V-LOOP start
        if 'V-LOOP: Iniciando' in payload:
            vloop_start_time = local_time
            print(f"[{local_time}] START: V-LOOP disparado.")
        
        # If we have a V-LOOP, look at the next 30 seconds
        if vloop_start_time and '14:18' in local_time:
            if 'DEBUG INJECTION (V-LOOP)' in payload:
                print(f"[{local_time}] INYECCIÓN V-LOOP ENVIADA.")
            elif 'DEBUG TRANSCRIPT OUTPUT' in payload:
                print(f"[{local_time}] IA DIJO: {payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '')}")
            elif 'DEBUG TOOL START' in payload:
                print(f"[{local_time}] IA USÓ HERRAMIENTA: {payload.replace('DEBUG TOOL START: ', '')}")

if __name__ == "__main__":
    check_vloop_reaction()
