# Agnostic - El Asistente Técnico Proactivo Manos Libres

Agnostic es una aplicación móvil nativa (Flutter) y un backend en Python (FastAPI) diseñado para resolver el problema de asistencia técnica "Manos Libres" para técnicos de campo. Aprovecha **Gemini 2.5 Flash Native Audio**, el **Google GenAI SDK**, y **Google Cloud Run** para crear una experiencia de Agente en Vivo proactiva y con cero latencia.

## ✨ Propuesta de Valor para el Gemini Live Agent Challenge
Los técnicos de campo trabajan con las manos sucias y llenas de herramientas. Los chatbots tradicionales basados en texto o solo voz son demasiado lentos. Agnostic actúa como un verdadero "Copiloto" proactivo:
- **Contexto Visual Proactivo**: Apunta la cámara a un electrodoméstico roto, y antes de que siquiera hables, Gemini precarga silenciosamente el contexto visual (marca, modelo, entorno).
- **Grounding Geográfico (Consciente de la Ubicación)**: El sistema adapta automáticamente su universo de repuestos y marcas conocidas a la región local del técnico.
- **Ejecución Real Manos Libres**: Interacción rápida, enfocada en la voz, con **Google Search Grounding** en tiempo real para buscar manuales y precios locales.
- **Manejo de Sesión Robusto**: Lógica de reconexión transparente incorporada para manejar caídas de red del mundo real sin matar la sesión de audio.

## Características de "Let's Go"
- **UX (Experiencia de Usuario) Centrada en Manos Libres**: Vista nativa de cámara completa, botón de micrófono gigante, consola de registros translúcida.
- **Ruteo de Contexto**: Cambio entre modos Industrial y Residencial.
- **Backend Multi-Agente**: El backend de Python sirve de proxy para el Audio en Vivo e inyecta dinámicamente diferentes Herramientas y Prompts basados en la selección del usuario.
- **Streaming Live por WebSocket**: Preparado para streaming bidireccional de WebRTC/trozos (chunks) de Audio.

---

## 🌍 Visión a Futuro (Roadmap): La Red de Conocimiento Global Agnostic (Hive)

Agnostic está diseñado para escalar más allá del uso individual y nichos específicos. Nuestra visión es transformar Agnostic en una **Base de Conocimiento Global Colaborativa (Crowdsourced)** para técnicos de *todas* las industrias (refrigeración, maquinaria pesada, automotriz, electrónica).

**El Flujo de Trabajo de "Global Hive":**
1. **Documentación Sin Esfuerzo (Zero-Effort):** Cuando un técnico resuelve exitosamente un problema complejo y no documentado usando la app, el **Librarian Agent (Agente Bibliotecario)** resume automáticamente el problema, los síntomas y la solución aplicada en segundo plano —sin que el técnico tenga que escribir nada.
2. **Agrupación Inter-Industrial:** Esta solución anonimizada y categorizada se inserta en una Base de Datos Vectorial centralizada (El Global Hive).
3. **Inteligencia Colectiva:** Cuando otro técnico, en cualquier parte del mundo, se enfrenta al mismo comportamiento extraño de una máquina, el **Search Agent (Agente de Búsqueda)** de Agnostic recupera la solución generada por el primer técnico, compartiendo efectivamente experiencia probada en campo al instante.
4. **Validación Comunitaria:** Los técnicos pueden confirmar por voz ("Sí, eso funcionó"), actuando como un sistema de votos a favor (upvote) natural para aumentar la clasificación de confianza de soluciones específicas.

---

## 🚀 Cómo Ejecutar el Backend (FastAPI + Gemini)

1. Navega a la carpeta `backend`:
    ```bash
    cd backend
    ```

2. Crea un entorno virtual (opcional pero recomendado):
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    ```

3. Instala los requisitos:
    ```bash
    pip install -r requirements.txt
    ```

4. Configura tu Google API Key:
    - Crea un archivo `.env` en la carpeta `backend/`.
    - Agrega: `GEMINI_API_KEY=tu_genai_api_key_aqui`

5. Inicia el Servidor:
    ```bash
    python main.py
    ```
    El servidor se ejecutará en `http://0.0.0.0:8000`.

---

## 📱 Cómo Ejecutar el Frontend (Flutter)

1. Asegúrate de tener el SDK de Flutter instalado y un emulador de Android corriendo (o un dispositivo físico conectado).

2. Navega a la carpeta `frontend/agnostic_app`:
    ```bash
    cd frontend/agnostic_app
    ```

3. Instala las dependencias de Dart:
    ```bash
    flutter pub get
    ```

4. Ejecuta la app:
    ```bash
    flutter run
    ```
    *(Nota: Si estás probando en un dispositivo físico, asegúrate de actualizar la dirección IP del WebSocket en `frontend/agnostic_app/lib/main.dart` de `10.0.2.2` a la dirección IP local de tu computadora).*

---

## ☁️ Instrucciones para Jueces y Despliegue en Google Cloud

**Para los Jueces del Hackathon:**
- Nuestro backend depende del **Google GenAI SDK** oficial y **Gemini 2.5 Flash** para la conexión a la Live API.
- Por favor, consulta el archivo `backend/main.py` para revisar el bucle robusto de reconexión de sesión y la implementación de Google Search Grounding.
- Puedes encontrar el resumen arquitectónico en `architecture_diagram.md`.

**Instrucciones de Reproducción / Despliegue:**
Para desplegar el backend en **Google Cloud Run** por ti mismo para cumplir con los requisitos del Gemini Live Agent Challenge:

1. Asegúrate de tener instalado el [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) y estar autenticado (`gcloud auth login`).
2. Configura tu Proyecto de Google Cloud:
    ```bash
    gcloud config set project TU_ID_DE_PROYECTO
    ```
3. Desde el directorio `backend/`, ejecuta el comando de despliegue. Esto construirá automáticamente el contenedor y lo desplegará:
    ```bash
    gcloud run deploy agnostic-backend \
      --source . \
      --region us-central1 \
      --allow-unauthenticated \
      --set-env-vars="GEMINI_API_KEY=tu_genai_api_key_aqui"
    ```
4. Una vez desplegado, Cloud Run te proporcionará una URL (ej., `https://agnostic-backend-xxxxx-uc.a.run.app`).
5. **Paso Final**: En tu app de Flutter (`main.dart`), reemplaza `ws://10.0.2.2:8000/ws/gemini-live` por `wss://agnostic-backend-xxxxx-uc.a.run.app/ws/gemini-live` (Nota el **`wss://`** para WebSockets seguros).
