# PinFlow AI 📌

> AI-powered Pinterest pin creator for Amazon affiliate marketers.
> Paste a link → pick an image → get 5 AI titles + 5 descriptions → post to Pinterest.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask 3, Flask-Login, Flask-Bcrypt, Flask-Limiter |
| Database | PostgreSQL + SQLAlchemy |
| Jobs | Celery + Redis |
| AI | Anthropic Claude (Sonnet 4) |
| Pinterest | Pinterest API v5 (OAuth 2.0) |
| Frontend | Vanilla JS, CSS custom properties, Syne + Inter fonts |

---

## Project Structure

```
pinflow/
├── app/
│   ├── __init__.py          # App factory, extension init
│   ├── models.py            # User, Pin, BoardCache models
│   ├── tasks.py             # Celery async tasks
│   ├── routes/
│   │   ├── auth.py          # /auth/login, /auth/signup, /auth/logout
│   │   ├── api.py           # /api/fetch, /api/generate, /api/post-pin, /api/boards, /api/history
│   │   ├── pinterest.py     # /pinterest/connect, /pinterest/callback, /pinterest/disconnect
│   │   └── main.py          # / and /dashboard
│   ├── services/
│   │   ├── ai_service.py    # Claude API — generates 5 titles + 5 descriptions
│   │   ├── scraper.py       # Amazon product scraper
│   │   ├── pinterest_service.py  # Pinterest OAuth + API calls
│   │   └── image_service.py # Image download + local storage
│   ├── templates/
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   └── dashboard.html
│   └── static/
│       ├── style.css        # Dark Pinterest UI
│       └── script.js        # Dashboard interactions
├── config.py                # Dev / Prod / Test config classes
├── run.py                   # Dev server entry point
├── celery_worker.py         # Celery worker entry point
├── gunicorn.conf.py         # Production Gunicorn config
├── Procfile                 # Render/Railway process definitions
├── requirements.txt
└── .env.example
```

---

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL running locally
- Redis running locally (`redis-server`)

### 1. Clone & install

```bash
git clone https://github.com/yourname/pinflow.git
cd pinflow
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in your keys (see below)
```

**Required keys:**

| Variable | Where to get it |
|----------|----------------|
| `SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Your local Postgres URL |
| `REDIS_URL` | `redis://localhost:6379/0` |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `PINTEREST_CLIENT_ID` | https://developers.pinterest.com/apps/ |
| `PINTEREST_CLIENT_SECRET` | Same Pinterest app |
| `PINTEREST_REDIRECT_URI` | Set to `http://localhost:5000/pinterest/callback` |

### 3. Create the database

```bash
# Create the DB in psql:
createdb pinflow_dev

# Then initialise tables:
python run.py          # tables auto-created on first run
# OR use the CLI command:
flask --app run init-db
```

### 4. Run the development server

**Terminal 1 — Flask:**
```bash
python run.py
```

**Terminal 2 — Celery worker (required for Pinterest posting):**
```bash
celery -A celery_worker.celery worker --loglevel=info
```

Open http://localhost:5000 → sign up → connect Pinterest → start creating pins.

---

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/fetch` | ✅ | Scrape Amazon link |
| POST | `/api/generate` | ✅ | Generate 5 titles + 5 descriptions |
| POST | `/api/post-pin` | ✅ | Queue pin for posting |
| GET | `/api/boards` | ✅ | List Pinterest boards (cached) |
| POST | `/api/boards/refresh` | ✅ | Clear board cache |
| GET | `/api/history` | ✅ | Last 50 pins |
| DELETE | `/api/history/<id>` | ✅ | Delete a pin |
| GET | `/pinterest/connect` | ✅ | Start OAuth flow |
| GET | `/pinterest/callback` | ✅ | OAuth callback |
| POST | `/pinterest/disconnect` | ✅ | Remove Pinterest tokens |

---

## Deployment (Render)

### Services to create

1. **Web Service** — Python, runs Flask
2. **Background Worker** — Python, runs Celery
3. **PostgreSQL** — Render managed DB
4. **Redis** — Render managed Redis

### Steps

1. Push code to GitHub
2. In Render dashboard → New → Web Service → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn -c gunicorn.conf.py "app:create_app('production')"`
5. Add all environment variables from `.env.example`
6. Set `FLASK_ENV=production`
7. Create a second Render service (Background Worker) with start command:
   ```
   celery -A celery_worker.celery worker --loglevel=info --concurrency=2
   ```
8. Set `PINTEREST_REDIRECT_URI` to your Render domain:
   ```
   https://your-app.onrender.com/pinterest/callback
   ```
9. Update this URL in your Pinterest app settings too.

### Database migration on deploy

In Render shell or as a one-off job:
```bash
flask --app run init-db
```

---

## Pinterest App Setup

1. Go to https://developers.pinterest.com/apps/
2. Create a new app
3. Add OAuth redirect URI: `https://yourdomain.com/pinterest/callback`
4. Request scopes: `boards:read`, `pins:write`, `user_accounts:read`
5. Copy Client ID and Client Secret to your `.env`

---

## Rate Limits

- `/api/fetch` — 30 requests/minute per user
- `/api/generate` — 20 requests/minute per user
- `/api/post-pin` — 10 requests/minute per user
- Global default — 200/day, 50/hour

Limits are enforced via Flask-Limiter backed by Redis.

---

## Features

- **5 AI titles + 5 descriptions** per generation with different marketing angles
- **4 content tones**: Viral 🔥 / Luxury ✨ / Casual 💬 / Affiliate 💰
- **Image selection** from product images + lifestyle grid
- **Pinterest board selector** with 1-hour caching
- **Async posting** via Celery with auto-retry (3 attempts)
- **Pin history** — last 50 pins per user with status badges
- **Toast notifications** for all actions
- **Live pin preview** updates as you edit
- **Rate limiting** per user via Redis
- **Token refresh** — Pinterest access tokens auto-refreshed
