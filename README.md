# Agnostic — AI Live Agent for Field Technicians 🛠️

> *"What today lives in a smartphone, tomorrow will live in smart glasses."*

An AI-powered, **hands-free** repair assistant that uses **Gemini Live API**, **ADK multi-agent orchestration**, and real-time vision to guide field technicians and DIY hobbyists. Agnostic sees what you see, hears what you say, and speaks back in real time — **zero typing required**.

Built for the [Gemini Live Agent Challenge](https://geminiliveagentchallenge.devpost.com/) — Category: **Live Agents 🗣️**

---

## 🌐 Architecture

Backend hosted on **Google Cloud Run** — 100% serverless, scalable, and always-on.

- **12+ ADK specialized agents** orchestrated by a Root Agent
- **Gemini Live API** for real-time bidirectional audio streaming (16kHz PCM)
- **Imagen 3** for generative visual guides (inpainting) overlaid on the camera feed
- **RAG Hive Mind** — verified repairs stored as vector embeddings in Firestore
- **Flutter (Android)** for the fully reactive, hands-free UI

---

## 🚀 Quick Start (Spin-up Instructions for Judges)

### Prerequisites

- Python 3.11+
- Flutter 3.x SDK
- Google Cloud account with billing enabled
- API Keys: Gemini, Google Maps

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/agnostic-live-agent.git
cd agnostic-live-agent
```

### 2. Configure environment variables

```bash
cd backend
cp .env.example .env
# Edit .env and fill in your API keys
```

Your `.env` should contain:
```
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_MAPS_API_KEY=your_maps_api_key_here
GOOGLE_API_KEY=your_gemini_api_key_here
GCP_PROJECT=your_gcp_project_id
```

### 3. Deploy the backend to Google Cloud Run

```bash
cd backend
gcloud run deploy agnostic-backend \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY,GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY
```

Or run locally for testing:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

### 4. Build and install the Flutter app

```bash
cd frontend/agnostic_app

# Update the backend URL in lib/main.dart:
# static const String _backendUrl = 'YOUR_CLOUD_RUN_URL';

flutter pub get
flutter build apk --release
# Install on Android device:
adb install build/app/outputs/flutter-apk/app-release.apk
```

---

## 🧠 Key Features

| Feature | Description |
|---------|-------------|
| **Real-time Voice Interaction** | Bidirectional audio via Gemini Live API. Barge-in supported. |
| **Live Camera Vision** | 1 FPS frame streaming. Gemini sees what you see. |
| **Visual Bounding Boxes** | ADK Vision Precision agent draws labels directly on the camera view. |
| **Generative Visual Guides** | Imagen 3 generates annotated repair diagrams overlaid on your camera feed. |
| **Mandatory Safety Gate** | Visual safety check blocks the next step until safe conditions are confirmed. |
| **Live Logistics** | Finds replacement parts and pushes MercadoLibre links to screen via WebSocket. |
| **Socratic Learning Mode** | Teaches hobbyists through questions instead of just giving answers. |
| **RAG Hive Mind** | Collective intelligence from verified real-world repairs — eliminates hallucinations. |
| **Flashlight Control** | Voice-activated LED torch for dark work environments. |

---

## 🛠️ Built With

- `google-gemini` / `gemini-2.0-flash-live`
- `agent-development-kit` (ADK)
- `google-genai-sdk`
- `imagen-3` / `nano-banana`
- `google-cloud-run`
- `firebase` / `cloud-firestore`
- `python` / `fastapi` / `websockets`
- `flutter` / `dart`
- `text-embeddings` / `rag` / `vector-database`
- `google-search` (grounding)
- `mercadolibre-api`

---

## 📁 Project Structure

```
agnostic/
├── backend/                    # Python FastAPI backend (Cloud Run)
│   ├── main.py                 # WebSocket server + Gemini Live integration
│   ├── prompts.py              # System prompts per mode
│   ├── adk_agents.py           # Root agent + repair specialists
│   ├── adk_universal_mentor.py # Socratic learning agent
│   ├── adk_vision_precision.py # Bounding box precision agent
│   ├── adk_direct_repair.py    # Direct repair agent
│   ├── adk_logistica.py        # Logistics + parts search agent
│   ├── rag_knowledge_base.py   # Hive Mind RAG system
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── agnostic_app/           # Flutter Android app
│       └── lib/
│           ├── main.dart       # Main UI + WebSocket client
│           └── gemini_direct_service.dart  # Direct Gemini Live client
└── mcp-server/                 # MCP server for tools (Maps, etc.)
```

---

## 📹 Demo Video

[Watch the demo on YouTube → ](#) *(coming soon)*

---

## 🏆 Gemini Live Agent Challenge

This project was built for the **Gemini Live Agent Challenge** — Category: **Live Agents 🗣️**

- ✅ Uses Gemini Live API for real-time audio/vision
- ✅ Built with ADK (Agent Development Kit)
- ✅ Backend hosted on Google Cloud Run
- ✅ Multimodal: audio + vision + generative image output

---

## ⚠️ Security Notice

**Never commit your `.env` file.** All API keys must be provided as environment variables. See `.env.example` for the required variable names.

---

*Agnostic: The bridge between Artificial Intelligence and Manual Labor.*
