<<<<<<< HEAD
# Sudoku Arena

A polished browser-based Sudoku app with a Python backend, user accounts,
email verification, daily puzzles, and interactive analytics.

## 🚀 Project overview

Sudoku Arena is a full-stack puzzle game built with:
- FastAPI backend
- SQLite persistence
- Static frontend using vanilla HTML/CSS/JavaScript
- Session-based authentication and email verification
- Daily puzzle caching and simple AI-assisted hints

## ✨ Features

- Unique Sudoku puzzle generation via backtracking
- Personal daily puzzle: same board for a user on the same calendar day
- Authenticated user accounts with email verification
- Session cookies via Starlette `SessionMiddleware`
- Password hashing with PBKDF2-SHA256 and random salt
- Username or email login
- Frontend hint button that reveals the next empty cell
- Mistake counter, star scoring, and progress tracking
- Light / dark theme support
- Responsive design for desktop and mobile

## 📦 Requirements

- Python 3.11+
- `pip`

## ✅ Quick start

```powershell
cd "C:\Users\aarus\OneDrive\Attachments\Desktop\Sudoku\SudokuCodeBase"
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Then visit: `http://127.0.0.1:8000`

## 🔧 Environment variables

The app supports email verification and session signing through environment variables.
Create a `.env` file in the project root and do not commit it.

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=yourapp@gmail.com
SMTP_PASSWORD=your-smtp-app-password
FROM_EMAIL="Sudoku Arena <yourapp@gmail.com>"
APP_BASE_URL=http://localhost:8000
SESSION_SECRET=replace-this-with-a-long-random-secret
```

### Important

- `SMTP_USER` and `SMTP_PASSWORD` are required only if you want email verification.
- If they are missing, the app still runs, but verification emails are skipped.
- `SESSION_SECRET` should be a long random string for secure session cookies.

## 📧 Email verification

Registration requires a valid email address. The backend validates email format and
ensures the email is not already registered before creating the account.

After registration:

1. a verification token is generated
2. a verification email is sent in the background
3. `/verify-email?token=...` marks the account verified
4. unverified users see a banner in the UI with a resend button

## 🧠 Authentication

- `POST /register` — create a new account and send verification email
- `POST /login` — log in with username or email plus password
- `POST /logout` — clear session cookie
- `GET /current-user` — return current user data including `email_verified`

## 🧩 Game behavior

- `GET /get-personalized-puzzle` — returns a newly generated Sudoku puzzle and solution
- `GET /get-daily-puzzle` — returns the user’s cached daily puzzle for the current date
- `POST /update-progress` — records completed game stats and awards stars
- `POST /get-ai-hint` — returns the next empty cell and the correct value
- `GET /get-ai-analysis` — returns static tips and heatmap placeholder
- `GET /get-personal-stats` — returns aggregated play stats for the current user
- `GET /ai-daily-feedback` — returns motivational feedback text

## 🧱 Code structure

```
SudokuCodeBase/
├── main.py             FastAPI backend, auth, puzzles, email verification
├── database.py         SQLite schema, user CRUD, email verification, daily puzzle cache
├── generator.py        Puzzle generation (extends SudokuEngine)
├── sudoku_engine.py    Core Sudoku solver and validator
├── requirements.txt    Python dependencies
├── Dockerfile
├── static/
│   ├── index.html      Single-page UI shell and game layout
│   ├── script.js       Frontend logic, auth, board rendering, API calls
│   └── style.css       Responsive theme styling
├── CODE_OVERVIEW.md    Deep architecture and implementation notes
└── README.md           Project introduction and setup guide
```

## 📚 Dependencies

`requirements.txt` includes:

- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `python-multipart`
- `itsdangerous`
- `starlette`
- `python-dotenv`

## 🐳 Docker

Build and run locally:

```powershell
docker build -t sudoku-app .
docker run -p 8000:8000 \
  -e SMTP_USER=yourapp@gmail.com \
  -e SMTP_PASSWORD="your-smtp-app-password" \
  -e SESSION_SECRET="replace-me" \
  sudoku-app
```

## 💡 Notes

- The app creates `game.db` automatically on first run.
- `game.db` should be ignored in Git.
- `APP_BASE_URL` is used to build verification links when sending email.
- The daily puzzle is cached so users get the same board all day.
- This project is licensed under the MIT License.

## ✅ Recommended improvements

- Add a password reset flow
- Add email token expiry
- Add unit tests for generator and database logic
- Add a leaderboard or competitive mode
- Improve AI analysis with real mistake heatmaps
=======
# Sudoku-Arena
>>>>>>> 66b3e665d3aa9d5ee2c19d1f6f6f65d2d38c6b5a
