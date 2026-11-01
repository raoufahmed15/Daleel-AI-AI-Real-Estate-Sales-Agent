# Daleel AI

A local-first real-estate sales sandbox with a Flutter client, a FastAPI CRM backend, and a separate RAG assistant API. The database starts empty. Bookings and CRM conversations are simulated; RAG answers use the configured local model and knowledge base.

## Project layout

- `flutter/daleel/backend/` — FastAPI application, local SQLite setup, the PaddleOCR adapter, other model-adapter slots, and API tests.
- `flutter/daleel/` — Flutter app for web, Android, and desktop.
- `Rag_RealEstate/` — approved-document retrieval, local LLM agent, Streamlit UI, and the HTTP API used by the app.

## Run locally on Windows

### 1. Start the backend

In PowerShell:

```powershell
cd flutter\daleel\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API documentation is available at <http://127.0.0.1:8000/docs>. A new `daleel-local.db` is created automatically but no leads, properties, model weights, vector data, or training data are generated. The pre-existing `daleel.db` sample file is preserved but is not used by default. Add your own leads and inventory through the app or API.

### 2. Start the RAG assistant

Follow the model, environment, and knowledge-base setup in [Rag_RealEstate/README.md](Rag_RealEstate/README.md), then start its API:

```powershell
cd Rag_RealEstate
python -m pip install -r requirements.txt
python -m uvicorn rag_api:app --reload --host 0.0.0.0 --port 8100
```

The Flutter app defaults to `http://localhost:8100` for web/desktop and `http://10.0.2.2:8100` for the Android emulator. Change the RAG service URL in Settings if needed. The service uses the RAG project's local Ollama model and vector database; it does not call an external AI provider by default.

The chat's microphone button records a short voice question and sends it to the public QwenCleo Arabic transcription model on Hugging Face. The app asks for confirmation before recording; the transcript is shown for review before it is sent as a chat message. The image button uploads a JPEG, PNG, or WebP file (up to 10 MB) to the local backend and extracts Arabic text with PaddleOCR. The image is not persisted by the application. PaddleOCR downloads its Arabic model files the first time OCR is used, so the backend needs internet access for that initial request.

### 3. Start the Flutter app

In a second PowerShell window:

```powershell
cd flutter\daleel
flutter pub get
flutter run -d chrome
```

To run on the Android emulator instead, use `flutter run -d emulator-5554`. The app is configured to reach the backend and RAG service through the emulator host at `10.0.2.2` on ports `8000` and `8100`.

For a physical Android device connected over USB, keep the backend bound to `127.0.0.1`, run `adb reverse tcp:8000 tcp:8000`, then launch Flutter with `flutter run -d <device-id> --dart-define=DALEEL_BACKEND_URL=http://127.0.0.1:8000`. This forwards OCR and other backend requests through USB without exposing the local backend to the Wi-Fi network.

## Local model and data extension points

The Integrations screen and FastAPI expose typed, opt-in endpoints for the modules below. Unimplemented modules return `501 not_implemented`; OCR uses a local PaddleOCR adapter and can raise `503 not_configured` if its dependencies or model files cannot be initialized. No mock AI answers or model weights are included.

| Module | Endpoint |
| --- | --- |
| Recommendation Engine | `POST /api/integrations/recommendation-engine/query` |
| Lead Scoring | `POST /api/integrations/lead-scoring/score` |
| RAG | `POST /api/integrations/rag/query` |
| STT | `POST /api/integrations/stt/transcribe` |
| TTS | `POST /api/integrations/tts/speak` |
| OCR | `POST /api/integrations/ocr/extract` (multipart image upload) |
| LLM Agent | `POST /api/integrations/llm-agent/chat` |

The OCR adapter is registered under `flutter/daleel/backend/app/extensions/` and uses PaddleOCR's local Arabic model. Its dependencies are installed with the backend requirements. Other model integrations can be added under the same extension directory and registered in `register(registry)` in `flutter/daleel/backend/app/extensions/__init__.py`. Handler request/response models and required fields are defined in `flutter/daleel/backend/app/integrations/contracts.py`; successful responses are validated against those contracts. Keep weights and private data outside version control and configure file locations through your own local settings. Commercial RAG answers must include evidence with its source, update date, and version; unsupported claims are not shown.

Set `DALEEL_DATABASE_URL` to use your own relational database and `DALEEL_AUTO_SEED=1` only when you explicitly want the optional synthetic demo seed. The default is no seed. `DALEEL_APP_MODE` defaults to `sandbox`.

## Verify

```powershell
# From flutter\daleel\backend\
python -m pytest tests

# From flutter\daleel\
flutter analyze
flutter test
```
