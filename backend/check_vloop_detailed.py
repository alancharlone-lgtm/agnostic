
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

def audit_vloop_session():
    try:
        with open('final_session_audit.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        with open('final_session_audit.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)

    logs.sort(key=lambda x: x.get('timestamp', ''))
    
    # We want the session around 14:18:24
    start_collecting = False
    
    print(f"{'HORA':<12} | {'SISTEMA/IA':<25} | {'CONTENIDO'}")
    print("-" * 120)
    
    for l in logs:
        payload = l.get('textPayload', '')
        if not payload: continue
        
        local_time = to_local(l.get('timestamp'))
        
        if '14:18:24' in local_time and 'V-LOOP: Iniciando' in payload:
            start_collecting = True
            print(f"\n[{local_time}] >>> COMIENZO DE LA LUPA SOBRE V-LOOP <<<")

        if start_collecting:
            if any(term in payload for term in ['DEBUG INJECTION', 'DEBUG TRANSCRIPT', 'DEBUG TOOL']):
                print(f"{local_time:<12} | {payload[:40]:<25} | {payload.split(': ', 1)[-1] if ': ' in payload else payload}")
            
            # Stop after 2 minutes of this session
            if '14:20:30' in local_time:
                break

if __name__ == "__main__":
    audit_vloop_session()
