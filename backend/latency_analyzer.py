
import json
import datetime
import os

def to_dt(utc_str):
    try:
        if not utc_str: return None
        utc_str = utc_str.replace('Z', '')
        if '.' in utc_str:
            base, frac = utc_str.split('.')
            frac = (frac + '000000')[:6]
            utc_str = f"{base}.{frac}"
        else:
            utc_str = f"{utc_str}.000000"
        return datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.%f')
    except Exception as e:
        return None

def analyze_latencies(file_path):
    logs = []
    # Intento robusto de lectura
    encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be']
    success = False
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                logs = json.load(f)
                print(f"DEBUG: Archivo cargado exitosamente con encode: {enc}")
                success = True
                break
        except Exception:
            continue
    
    if not success:
        print("Error: No se pudo cargar el archivo JSON con ninguna codificación estándar.")
        return

    # Ordenar por timestamp
    logs.sort(key=lambda x: x.get('timestamp', ''))

    results = []
    current_vloop_start = None
    last_user_input_end = None
    
    print(f"\n{'EVENTO':<40} | {'TIMESTAMP (UTC)':<20} | {'LATENCIA':<10}")
    print("-" * 75)

    for entry in logs:
        payload = entry.get('textPayload', '')
        if not payload: continue
        timestamp = to_dt(entry.get('timestamp'))
        if not timestamp: continue

        # Inicio de V-LOOP
        if "V-LOOP: Iniciando" in payload:
            current_vloop_start = timestamp
            print(f"{'INICIO V-LOOP/CÁMARA':<40} | {timestamp.strftime('%H:%M:%S.%f')[:-3]} | -")

        # Registro de herramientas para contexto (opcional)
        if "DEBUG TOOL START" in payload:
            t_name = payload.split("DEBUG TOOL START: ")[1].split("(")[0]
            # print(f"DEBUG: Herramienta {t_name} a las {timestamp.strftime('%H:%M:%S.%f')[:-3]}")

        # Respuestas de Gemini
        if "DEBUG TRANSCRIPT OUTPUT:" in payload:
            text = payload.split("DEBUG TRANSCRIPT OUTPUT:")[1].strip()
            
            if current_vloop_start:
                latency = (timestamp - current_vloop_start).total_seconds()
                print(f"{'PRIMERA RESPUESTA (V-LOOP)':<40} | {timestamp.strftime('%H:%M:%S.%f')[:-3]} | {latency:>6.2f}s")
                results.append({"type": "V-LOOP", "latency": latency, "text": text})
                current_vloop_start = None 
            elif last_user_input_end:
                latency = (timestamp - last_user_input_end).total_seconds()
                # Filtrar ruidos/latencias negativas si los logs vienen desordenados por ms
                if latency > 0:
                    print(f"{'RESPUESTA CONVERSACIONAL':<40} | {timestamp.strftime('%H:%M:%S.%f')[:-3]} | {latency:>6.2f}s")
                    results.append({"type": "CONVERSATION", "latency": latency, "text": text})
                last_user_input_end = None

        # Entrada de usuario (Input Transcript)
        if "DEBUG TRANSCRIPT INPUT:" in payload:
             last_user_input_end = timestamp

    if not results:
        print("\nNo se encontraron secuencias completas de interacción en este bloque de logs.")
    else:
        vloop_list = [r['latency'] for r in results if r['type'] == 'V-LOOP']
        conv_list = [r['latency'] for r in results if r['type'] == 'CONVERSATION']
        
        avg_vloop = sum(vloop_list) / len(vloop_list) if vloop_list else 0
        avg_conv = sum(conv_list) / len(conv_list) if conv_list else 0
        
        print("\n" + "="*40)
        print(f"RESUMEN FINAL DE LATENCIAS")
        print(f"Promedio V-LOOP (Apertura -> Voz):  {avg_vloop:.2f}s")
        print(f"Promedio Turno Conversacional:      {avg_conv:.2f}s")
        print(f"Máxima Latencia detectada:          {max([r['latency'] for r in results]):.2f}s")
        print(f"Mínima Latencia detectada:          {min([r['latency'] for r in results]):.2f}s")
        print("="*40)

if __name__ == "__main__":
    import sys
    target = 'audit_latency_analysis.json' # Default
    if len(sys.argv) > 1:
        target = sys.argv[1]
    analyze_latencies(target)
