
import json
import datetime

def to_dt(utc_str):
    try:
        utc_str = utc_str.replace('Z', '')
        if '.' in utc_str:
            base, frac = utc_str.split('.')
            frac = (frac + '000000')[:6]
            utc_str = f"{base}.{frac}"
        return datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.%f')
    except: return None

def calculate_lag():
    try:
        with open('audit_1833_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        with open('audit_1833_raw.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)

    logs.sort(key=lambda x: x.get('timestamp', ''))

    camera_start = None
    first_speech_output = None
    id_maquina = None
    herramientas_disparadas = []

    for entry in logs:
        payload = entry.get('textPayload', '')
        if not payload: continue
        timestamp = to_dt(entry.get('timestamp'))

        # 1. Identificar cuando se inició el V-LOOP (Apertura de cámara)
        if "V-LOOP: Iniciando" in payload and not camera_start:
            camera_start = timestamp
            print(f"DEBUG: Cámara detectada abierta a las {timestamp.strftime('%H:%M:%S.%f')[:-3]} (UTC)")

        # 2. Identificar el primer frame enviado
        if "V-LOOP: Enviando frame 1/3" in payload and not camera_start:
             camera_start = timestamp
             print(f"DEBUG: Primer frame capturado a las {timestamp.strftime('%H:%M:%S.%f')[:-3]} (UTC)")

        # 3. Detectar qué identificó el agente de visión
        if "Vision Agent (Live Tool):" in payload:
            id_maquina = payload.split("IDENTIFICADO VISUALMENTE:")[1].strip() if "IDENTIFICADO VISUALMENTE:" in payload else "Desconocido"

        # 4. Registrar herramientas disparadas
        if "DEBUG TOOL START" in payload:
            t_name = payload.split("DEBUG TOOL START: ")[1].split("(")[0]
            herramientas_disparadas.append(t_name)

        # 5. Identificar el primer audio generado por Gemini
        if "DEBUG TRANSCRIPT OUTPUT:" in payload and not first_speech_output:
            first_speech_output = timestamp
            speech_text = payload.split("DEBUG TRANSCRIPT OUTPUT:")[1].strip()
            print(f"DEBUG: Primer audio generado a las {timestamp.strftime('%H:%M:%S.%f')[:-3]} (UTC)")
            print(f"DEBUG: Texto inicial: '{speech_text}'")

    if camera_start and first_speech_output:
        lag = (first_speech_output - camera_start).total_seconds()
        print(f"\n--- RESULTADO FINAL DEL LAG ---")
        print(f"Inicio Proactivo (V-LOOP): {camera_start.strftime('%H:%M:%S.%f')[:-3]} (UTC)")
        print(f"Respuesta de Gemini:     {first_speech_output.strftime('%H:%M:%S.%f')[:-3]} (UTC)")
        print(f"LAG TOTAL:               {lag:.2f} segundos")
        print(f"Artefacto:               {id_maquina}")
        print(f"Herramientas usadas:     {', '.join(set(herramientas_disparadas))}")
    else:
        print("No se encontró una secuencia completa de inicio de cámara y respuesta de voz.")

if __name__ == "__main__":
    calculate_lag()
