
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

def audit():
    try:
        # gcloud on Windows = UTF-16 usually
        with open('final_session_audit.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        try:
            with open('final_session_audit.json', 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception as e:
            print(f"Error loading logs: {e}")
            return

    logs.sort(key=lambda x: x.get('timestamp', ''))

    print(f"\n{'HORA (ARG)':<12} | {'EVENTO':<25} | {'DETALLE'}")
    print("-" * 150)

    for entry in logs:
        payload = entry.get('textPayload', '')
        if not payload: continue
        local_time = to_local(entry.get('timestamp'))

        # 1. Start of session
        if 'V-LOOP: Iniciando' in payload:
            print(f"\n[{local_time}] >>> INICIO DE SESIÓN DETECTADO <<<")
            print(f"{local_time:<12} | SESIÓN START            | {payload}")

        # 2. V-LOOP Injections
        elif 'DEBUG INJECTION (V-LOOP)' in payload:
            print(f"{local_time:<12} | INYECCIÓN SILENCIOSA    | {payload.replace('DEBUG INJECTION (V-LOOP): ', '')[:100]}...")

        # 3. Audio/Video Data flow (briefly)
        elif 'DEBUG IN: Received' in payload or 'DEBUG IN: Audio flowing' in payload:
            # We don't want to spam, but noting when audio starts flowing is good
            if 'Audio flowing' in payload:
                print(f"{local_time:<12} | HARDWARE: AUDIO FLOW    | Iniciando recepción de voz del usuario.")

        # 4. Transcripts
        elif 'DEBUG TRANSCRIPT INPUT' in payload:
            print(f"{local_time:<12} | DIÁLOGO: USUARIO (VOZ)  | {payload.replace('DEBUG TRANSCRIPT INPUT: ', '')}")
        elif 'DEBUG TRANSCRIPT OUTPUT' in payload:
            print(f"{local_time:<12} | DIÁLOGO: IA (VOZ)       | {payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '')}")

        # 5. Tools
        elif 'DEBUG TOOL START' in payload:
            print(f"{local_time:<12} | HERRAMIENTA: INICIO     | {payload.replace('DEBUG TOOL START: ', '')}")
        elif 'DEBUG TOOL END' in payload:
            print(f"{local_time:<12} | HERRAMIENTA: FIN        | {payload.replace('DEBUG TOOL END: ', '')}")

        # 6. Errors/Status
        elif 'DEBUG ERROR' in payload:
            print(f"{local_time:<12} | ESTADO: ERROR           | {payload[:110]}")

if __name__ == "__main__":
    audit()
