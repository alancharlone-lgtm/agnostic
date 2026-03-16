import json
from datetime import datetime

def analyze():
    try:
        with open('logs_utf8.json', 'r', encoding='utf-8-sig') as f:
            logs = json.load(f)
    except Exception as e:
        print(f"Error loading logs: {e}")
        return

    tools = {}
    
    # Sort logs by timestamp
    logs.sort(key=lambda x: x['timestamp'])

    print("--- ANÁLISIS DE EJECUCIÓN DE AGENTES ---")
    
    for entry in logs:
        text = entry.get('textPayload', '')
        ts_str = entry.get('timestamp')
        ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))

        if "DEBUG TOOL START" in text:
            # Extract tool name
            name = text.split("DEBUG TOOL START: ")[1].split("(")[0]
            tools[name] = {"start": ts}
            print(f"Inició: {name} a las {ts_str}")

        if "DEBUG ADK SUCCESS" in text or "DEBUG TOOL END" in text:
            # This is tricky because ADK success doesn't always have the name in the same line
            # But we can assume the most recent tool started is the one that finished if it's sequential
            # or look for context.
            # Let's just find the most recent 'start' that doesn't have an 'end'
            pending = [n for n, d in tools.items() if "end" not in d]
            if pending:
                name = pending[-1]
                tools[name]["end"] = ts
                duration = (ts - tools[name]["start"]).total_seconds()
                tools[name]["duration"] = duration
                print(f"Finalizó: {name} a las {ts_str} (Duración: {duration:.2f}s)")
        
        if "DEBUG ADK ERROR" in text:
            pending = [n for n, d in tools.items() if "end" not in d]
            if pending:
                name = pending[-1]
                tools[name]["end"] = ts
                tools[name]["status"] = "ERROR"
                print(f"ERROR en {name} a las {ts_str}")

    print("\n--- RESUMEN FINAL ---")
    for name, data in tools.items():
        status = data.get("status", "SUCCESS")
        duration = data.get("duration", "N/A")
        print(f"- Agente: {name}")
        print(f"  Estado: {status}")
        print(f"  Duración: {duration}s")

if __name__ == "__main__":
    analyze()
