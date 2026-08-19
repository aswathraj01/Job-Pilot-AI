# Job-Pilot AI 🚀

> **AI-powered job application tracker** — paste any job URL and our AI extracts every detail, tracks your pipeline, matches your resume, and syncs your Gmail.

[![Backend CI](https://github.com/yourusername/Job-Pilot-AI/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/yourusername/Job-Pilot-AI/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/yourusername/Job-Pilot-AI/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/yourusername/Job-Pilot-AI/actions/workflows/frontend-ci.yml)

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🤖 **AI Job Extraction** | Paste a URL → Gemini 1.5 Flash extracts title, company, salary, skills, benefits, and more |
| 📊 **Pipeline Tracking** | 8-stage status pipeline from Saved → Offer with analytics |
| 📈 **Analytics Dashboard** | Funnel, timeline chart, top skills demand, company breakdown |
| 📄 **Resume Matching** | Upload PDF/DOCX → AI scores every job 0–100 with gap analysis |
| 📧 **Gmail Sync** | OAuth2 integration links recruiter emails to your tracked jobs |
| 🔔 **Reminders** | Set reminders per job — emails sent automatically |
| 🔌 **Chrome Extension** | One-click save from LinkedIn, Indeed, Greenhouse, Lever, Workday |
| 🔐 **JWT RS256 Auth** | Secure access + refresh token rotation with Redis blacklisting |

---

## 🏗️ Architecture

```
Flutter Web → Nginx → FastAPI (Python 3.12)
                         ├── PostgreSQL 16
                         ├── Redis 7 (cache + Celery queue)
                         └── Celery Workers (scrape + LLM + email sync)
```

---

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker & Docker Compose
- Google Gemini API key ([get one free](https://makersuite.google.com/app/apikey))
- Openssl (for RSA key generation)

### 1. Clone & Configure

```bash
git clone https://github.com/yourusername/Job-Pilot-AI.git
cd Job-Pilot-AI
cp backend/.env.example backend/.env
```

Edit `backend/.env` with your values:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
POSTGRES_PASSWORD=your_strong_password
```

### 2. Generate RSA Keys for JWT

```bash
mkdir -p backend/keys
openssl genrsa -out backend/keys/private.pem 2048
openssl rsa -in backend/keys/private.pem -pubout -out backend/keys/public.pem
```

### 3. Start All Services

```bash
cd docker
docker compose up -d

# Run migrations
docker compose run --rm migrate
```

### 4. Access the App

| Service | URL |
|---------|-----|
| **Flutter Web** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/api/docs |
| **Flower (Celery Monitor)** | http://localhost:5555 |

---

## 💻 Local Development

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Start services (PostgreSQL + Redis required)
uvicorn app.main:app --reload

# Run Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Run tests
pytest --cov=app -v
```

### Frontend

```bash
cd frontend
flutter pub get
flutter run -d chrome
```

### Chrome Extension

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked** → select `chrome_extension/` folder
4. Extension appears in toolbar — log in via the popup

---

## 📁 Project Structure

```
Job-Pilot-AI/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/               # Route handlers (auth, jobs, analytics, resume, email)
│   │   ├── core/              # Config, security, logging, WebSocket manager
│   │   ├── db/                # SQLAlchemy models + session
│   │   ├── migrations/        # Alembic migrations
│   │   ├── schemas/           # Pydantic v2 request/response models
│   │   ├── services/          # Business logic (scraper, extractor, matcher, analytics, email)
│   │   └── tasks/             # Celery async tasks (job processing, reminders, email sync)
│   └── tests/                 # pytest test suite
│
├── frontend/                   # Flutter Web
│   └── lib/
│       ├── core/              # Theme, router, network client, storage
│       ├── features/
│       │   ├── auth/          # Login, register, JWT provider
│       │   ├── jobs/          # Job list, detail, add job
│       │   ├── dashboard/     # Analytics charts
│       │   ├── resume/        # Upload + match view
│       │   └── settings/      # Gmail connect, profile
│       └── shared/            # Reusable widgets, theme tokens
│
├── chrome_extension/           # Manifest V3
│   ├── background/            # Service worker
│   ├── content/               # Inject floating save button
│   └── popup/                 # Extension popup UI
│
├── docker/                     # Docker Compose + Nginx configs
└── .github/workflows/          # CI/CD pipelines
```

---

## 🔌 API Reference

Full interactive docs at: `http://localhost:8000/api/docs`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Create account |
| `/api/v1/auth/login` | POST | Get JWT tokens |
| `/api/v1/jobs/` | POST | Add job by URL (async AI extraction) |
| `/api/v1/jobs/` | GET | List jobs with filters |
| `/api/v1/jobs/{id}` | GET | Full job detail |
| `/api/v1/jobs/{id}/ws` | WebSocket | Real-time processing status |
| `/api/v1/analytics/` | GET | Full analytics dashboard data |
| `/api/v1/resume/upload` | POST | Upload PDF/DOCX resume |
| `/api/v1/resume/match/{job_id}` | POST | Run AI match scoring |
| `/api/v1/email/connect` | GET | Gmail OAuth2 URL |

---

## 🧪 Testing

```bash
# Backend (≥70% coverage required)
cd backend && pytest --cov=app --cov-report=term-missing -v

# Frontend
cd frontend && flutter test

# Integration
cd docker && docker compose up -d
cd backend && pytest tests/integration/ -v
```

---

## 🌐 Environment Variables

See `backend/.env.example` for the full reference. Key variables:

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Gemini 1.5 Flash API key |
| `DATABASE_URL` | PostgreSQL async connection string |
| `REDIS_URL` | Redis connection URL |
| `JWT_PRIVATE_KEY_PATH` | Path to RSA private key (.pem) |
| `GOOGLE_CLIENT_ID` | Gmail OAuth2 client ID |
| `SMTP_USER` / `SMTP_PASSWORD` | Email sender credentials |

---

## 📜 License

MIT License — see [LICENSE](LICENSE)

---

<div align="center">
Built with ❤️ using FastAPI, Flutter, PostgreSQL, Redis, and Gemini AI
</div>
