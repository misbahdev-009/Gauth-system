# FastAPI Google OAuth & Password Authentication

A modern, secure FastAPI authentication system featuring:
- **Google OAuth 2.0 (OpenID Connect)** with automatic user profile sync (name, avatar).
- **Email + Password Authentication** with secure **Argon2id** password hashing.
- **Session Management** using Starlette signed session cookies.
- **MongoDB Atlas Integration** with automatic resilient fallback to **In-Memory Store** for development and offline testing.
- **Light / Dark Theme Support** with zero-flash pre-paint script and local storage persistence.
- **Responsive UI** styled with modern vanilla CSS and Jinja2 templates.
- **Vercel Deployment Ready** via `vercel.json`.

---

## Project Structure

```
├── app/
│   ├── static/               # Static assets (CSS, JS)
│   │   ├── app.js            # Theme toggle and password visibility toggle
│   │   └── style.css         # Modern responsive CSS styles
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── partials/         # Component partials (google button, theme toggle)
│   │   ├── base.html         # Base HTML layout
│   │   ├── dashboard.html    # Authenticated user dashboard
│   │   ├── login.html        # Sign-in page
│   │   └── register.html     # Sign-up page
│   ├── auth.py               # Auth routes (login, register, logout, Google OAuth)
│   ├── config.py             # Pydantic Settings & environment variable configuration
│   ├── dependencies.py       # FastAPI dependency injection (get_current_user)
│   ├── main.py               # Core FastAPI app instance, middleware & routes
│   ├── security.py           # Argon2 password hashing & verification
│   ├── templating.py         # Jinja2 template renderer setup
│   └── users.py              # User model, InMemory and MongoDB stores
├── main.py                   # Root entrypoint for uvicorn and direct execution
├── requirements.txt          # Python dependencies
├── vercel.json               # Vercel deployment configuration
└── .env                      # Environment configuration
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12 and 3.14)
- A Google Cloud OAuth 2.0 Client ID & Secret (for Google Sign-In)

### 2. Installation

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Environment Configuration

Create or update your `.env` file in the project root:

```env
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
SESSION_SECRET_KEY=generate-a-secure-random-key-for-session-signing
HTTPS_ONLY=false
MONGODB_URI=
MONGODB_DB=oauth_app
```

> **Note on `HTTPS_ONLY`:** Keep `HTTPS_ONLY=false` when developing locally on `http://localhost:8000`. Leaving it as `true` on plain HTTP causes browsers to reject session cookies marked with the `Secure` flag, which breaks OAuth CSRF verification.

> **Note on `MONGODB_URI`:** If omitted or if connection to MongoDB fails (e.g. Atlas IP whitelist restriction), the app automatically falls back to an in-memory store so you can still run and test everything locally.

---

## Running the Application

You can start the server using any of the following methods:

```bash
# Using uvicorn with the root entrypoint
uvicorn main:app --reload --port 8000

# Or directly with Python
python main.py

# Or pointing to app.main
uvicorn app.main:app --reload --port 8000
```

Once running, visit:
- **Application:** [http://localhost:8000](http://localhost:8000)
- **Health check:** [http://localhost:8000/health](http://localhost:8000/health)

