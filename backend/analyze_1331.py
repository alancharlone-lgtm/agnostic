
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

def analyze_full_session():
    try:
        with open('session_1331_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        try:
            with open('session_1331_raw.json', 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception as e:
            print(f"Error loading logs: {e}")
            return

    logs.sort(key=lambda x: x.get('timestamp', ''))

    print(f"\n{'HORA (ARG)':<12} | {'EVENTO':<25} | {'DETALLE'}")
    print("-" * 140)

    for entry in logs:
        payload = entry.get('textPayload', '')
        if not payload: continue
        
        timestamp = entry.get('timestamp', '')
        local_time = to_local(timestamp)

        # 1. Inyecciones Proactivas (Silenciosas)
        if 'DEBUG INJECTION' in payload:
            type_inj = "V-LOOP (INICIO)" if "V-LOOP" in payload else "NUDGE (AMBIENTAL)"
            detail = payload.split("):")[-1].strip() if "):" in payload else payload
            print(f"{local_time:<12} | {type_inj:<25} | [SILENCIOSO] {detail[:90]}...")

        # 2. Flujo de Audio/Video (Hardware)
        elif 'DEBUG IN: Received vision frame' in payload:
            # Demasiados frames, imprimimos solo uno cada tanto o resumimos
            pass 
        elif 'DEBUG IN: Audio flowing' in payload:
            print(f"{local_time:<12} | FLUJO AUDIO ENTRANTE    | Procesando chunks de voz del usuario...")

        # 3. Transcripciones (Diálogo)
        elif 'DEBUG TRANSCRIPT INPUT' in payload:
            text = payload.replace('DEBUG TRANSCRIPT INPUT: ', '').strip()
            print(f"{local_time:<12} | USUARIO (VOZ)           | {text}")
        elif 'DEBUG TRANSCRIPT OUTPUT' in payload:
            text = payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '').strip()
            print(f"{local_time:<12} | IA (VOZ)                | {text}")

        # 4. Herramientas
        elif 'DEBUG TOOL START' in payload:
            tool_name = payload.replace('DEBUG TOOL START: ', '').split('(')[0]
            print(f"{local_time:<12} | HERRAMIENTA INICIO      | {payload.replace('DEBUG TOOL START: ', '')}")
        elif 'DEBUG TOOL END' in payload:
            print(f"{local_time:<12} | HERRAMIENTA FIN         | {payload.replace('DEBUG TOOL END: ', '')}")

        # 5. Salida de Audio (IA hablando)
        elif 'DEBUG OUT: Sending buffered' in payload:
            print(f"{local_time:<12} | IA ENVIANDO AUDIO       | Generando respuesta sonora...")

        # 6. Errores críticos
        elif 'DEBUG ERROR' in payload or 'DEBUG CRITICAL' in payload:
            print(f"{local_time:<12} | ESTADO/ERROR            | {payload[:100]}")

if __name__ == "__main__":
    analyze_full_session()
