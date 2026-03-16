
import json
import datetime

def to_local(utc_str):
    try:
        if not utc_str: return "00:00:00.000"
        utc_str = utc_str.replace('Z', '')
        if '.' in utc_str:
            base, frac = utc_str.split('.')
            frac = (frac + '000000')[:6]
            utc_str = f"{base}.{frac}"
        else:
            utc_str = f"{utc_str}.000000"
        dt = datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.%f')
        dt = dt - datetime.timedelta(hours=3) # Argentina
        return dt.strftime('%H:%M:%S.%f')[:-3]
    except:
        return utc_str

def audit_1725():
    try:
        with open('audit_1725_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        try:
            with open('audit_1725_raw.json', 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception as e:
            print(f"Error loading logs: {e}")
            return

    logs.sort(key=lambda x: x.get('timestamp', ''))

    print(f"\n{'HORA (ARG)':<12} | {'EVENTO':<25} | {'DETALLE'}")
    print("-" * 150)

    session_found = False
    
    for entry in logs:
        payload = entry.get('textPayload', '')
        if not payload: continue
        local_time = to_local(entry.get('timestamp'))

        # Look for sessions starting after 17:20
        if '17:20' > local_time: continue

        if 'V-LOOP: Iniciando' in payload:
            session_found = True
            print(f"\n[{local_time}] >>> INICIO DE SESIÓN DETECTADO (V-LOOP) <<<")
            
        if not session_found: continue

        if 'DEBUG INJECTION (V-LOOP)' in payload:
            print(f"{local_time:<12} | INYECCIÓN V-LOOP         | {payload.split(': ', 1)[-1][:100]}...")

        elif 'DEBUG TRANSCRIPT INPUT' in payload:
            print(f"{local_time:<12} | USUARIO (VOZ)           | {payload.split(': ', 1)[-1]}")
            
        elif 'DEBUG TRANSCRIPT OUTPUT' in payload:
            print(f"{local_time:<12} | IA (VOZ)                | {payload.split(': ', 1)[-1]}")

        elif 'DEBUG TOOL START' in payload:
            print(f"{local_time:<12} | HERRAMIENTA INICIO      | {payload.split(': ', 1)[-1]}")

        elif 'DEBUG TOOL END' in payload:
            print(f"{local_time:<12} | HERRAMIENTA FIN         | {payload.split(': ', 1)[-1]}")
            
        elif 'DEBUG ERROR' in payload:
            print(f"{local_time:<12} | ESTADO: ERROR           | {payload[:110]}")

if __name__ == "__main__":
    audit_1725()
