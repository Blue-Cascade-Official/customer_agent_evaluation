# Internee AI Call Evaluation Dashboard

Open dashboard for internees to practice calls with an ElevenLabs agent, then receive split scores for **audio parameters** and **knowledge parameters** (RAG over uploaded company docs).

## Stack

- **Frontend:** React + Vite + `@elevenlabs/react`
- **Backend:** FastAPI
- **DB:** PostgreSQL + pgvector
- **Storage:** GCP Cloud Storage (local filesystem fallback if `GCS_BUCKET` is empty)
- **AI:** ElevenLabs Conversational AI + OpenAI embeddings/chat

## Quick start

### 1. Environment

```bash
cp .env.example .env
# Fill in ELEVENLABS_API_KEY, OPENAI_API_KEY
# Optionally GCS_BUCKET + GOOGLE_APPLICATION_CREDENTIALS
```

### 2. Database

```bash
docker compose up -d
```

### 3. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Flows

1. **Call** — enter name → start call → end call → backend fetches transcript/audio → evaluates
2. **Results** — search by name → dual scorecards + transcript + audio
3. **Knowledge** — upload PDF/DOCX/TXT/MD → chunk + embed into pgvector for RAG scoring

## Agent

Default agent id: `agent_8801m754zcqefqatys0hhnr0x82s` (override with `ELEVENLABS_AGENT_ID`).

## Notes

- No authentication (internal internee use).
- Without GCS credentials, audio/docs are stored under `./data/`.
- MP3 decoding for audio metrics may require system `ffmpeg` for best results; transcript-based metrics still run without it.
