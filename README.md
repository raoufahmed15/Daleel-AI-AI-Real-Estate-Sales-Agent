# Daleel AI

A demo real-estate sales workspace with a Flutter client and a FastAPI backend. Demo records are synthetic; bookings and integrations are simulated.

## Project layout

- `backend/` — FastAPI application, SQLite setup, synthetic seed data, and API tests.
- `flutter/daleel/` — Flutter app for web, Android, and desktop.

## Run locally on Windows

### 1. Start the backend

In PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API documentation is available at <http://127.0.0.1:8000/docs>. The local SQLite database is created automatically and seeded with synthetic demo data.

### 2. Start the Flutter app

In a second PowerShell window:

```powershell
cd flutter\daleel
flutter pub get
flutter run -d chrome
```

To run on the Android emulator instead, use `flutter run -d emulator-5554`. The app is configured to reach the backend through the emulator host at `10.0.2.2:8000`.

## Verify

```powershell
# From backend\
python -m pytest tests

# From flutter\daleel\
flutter analyze
flutter test
```
