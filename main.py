import re
from email.utils import parseaddr

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware
import json, os, smtplib, logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date
from generator import SudokuGenerator
import database

logger = logging.getLogger(__name__)

# ── Pydantic models ───────────────────────────────────────────────────────────

class AuthRequest(BaseModel):
    username: str
    password: str
    email: str | None = None

class HintRequest(BaseModel):
    current_board: list[list[int]]
    solution: list[list[int]]

class ProgressUpdate(BaseModel):
    time_taken: int
    mistakes: int
    clues_remaining: int
    mistake_positions: list

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI()

def get_secret_key() -> str:
    return os.getenv("SESSION_SECRET", "change-this-secret")

app.add_middleware(SessionMiddleware, secret_key=get_secret_key())
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

def is_valid_email(email: str) -> bool:
    """Return True when the email looks like a valid address."""
    if not email or len(email) > 254:
        return False
    parsed = parseaddr(email)[1]
    return parsed == email and bool(_EMAIL_RE.match(email))


gen = SudokuGenerator()
database.init_db()

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html", media_type="text/html")

# ── Email helper ──────────────────────────────────────────────────────────────

def _build_verification_url(request: Request, token: str) -> str:
    base = os.getenv("APP_BASE_URL", str(request.base_url).rstrip("/"))
    return f"{base}/verify-email?token={token}"

def send_verification_email(to_email: str, username: str, verify_url: str):
    """
    Send an HTML verification email.

    Required environment variables
    ───────────────────────────────
    SMTP_HOST     (default: smtp.gmail.com)
    SMTP_PORT     (default: 587)
    SMTP_USER     sender email address
    SMTP_PASSWORD sender password / app password
    FROM_EMAIL    display name + address  (default: SMTP_USER)
    """
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")
    from_addr = os.getenv("FROM_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        logger.warning("SMTP credentials not configured — skipping verification email.")
        return

    subject = "Verify your Sudoku Arena account"
    html_body = f"""
    <html><body style="font-family:sans-serif;background:#0c0e14;color:#eef0f6;padding:40px;">
      <div style="max-width:480px;margin:auto;background:#1a1e2b;border-radius:16px;padding:36px;border:1px solid #252b3a;">
        <h1 style="color:#f0b429;margin-top:0;">◈ Sudoku Arena</h1>
        <p>Hi <strong>{username}</strong>,</p>
        <p>Thanks for signing up! Please verify your email address to unlock all features.</p>
        <a href="{verify_url}"
           style="display:inline-block;margin:20px 0;padding:14px 28px;background:#f0b429;
                  color:#0c0e14;font-weight:700;border-radius:10px;text-decoration:none;">
          Verify Email Address
        </a>
        <p style="color:#8890a8;font-size:0.85rem;">
          If you didn't create this account, you can safely ignore this email.<br>
          This link does not expire.
        </p>
      </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = to_email
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_addr, to_email, msg.as_string())
        logger.info("Verification email sent to %s", to_email)
    except Exception as exc:
        logger.error("Failed to send verification email: %s", exc)

# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_session_username(request: Request) -> str:
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return username

# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/register")
def register(data: AuthRequest, request: Request, background_tasks: BackgroundTasks):
    username = data.username.strip()
    password = data.password.strip()
    email    = (data.email or "").strip()

    if not username or not password or not email:
        raise HTTPException(status_code=400, detail="Username, email, and password are required")
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Please provide a valid email address")

    existing = database.get_user(username)
    if existing and existing["password_hash"]:
        raise HTTPException(status_code=409, detail="Username already exists")

    existing_email = database.get_user_by_email(email)
    if existing_email and existing_email["username"] != username:
        raise HTTPException(status_code=409, detail="Email already registered")

    token = database.create_user(username, password, email)
    verify_url = _build_verification_url(request, token)
    background_tasks.add_task(send_verification_email, email, username, verify_url)

    request.session["username"] = username
    user = database.get_user(username)
    return {
        "username":       user["username"],
        "email":          user["email"],
        "stars":          user["stars"],
        "world":          user["current_world"],
        "level":          user["sub_level"],
        "email_verified": bool(user["email_verified"]),
    }

@app.post("/login")
def login(data: AuthRequest, request: Request):
    username = data.username.strip()
    password = data.password.strip()
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    user = database.get_user_by_identifier(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not database.verify_user(username, password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    request.session["username"] = user["username"]
    return {
        "username":       user["username"],
        "email":          user["email"],
        "stars":          user["stars"],
        "world":          user["current_world"],
        "level":          user["sub_level"],
        "email_verified": bool(user["email_verified"]),
    }

@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged_out"}

@app.get("/current-user")
def current_user(request: Request):
    username = get_session_username(request)
    u = database.get_user(username)
    if not u:
        raise HTTPException(status_code=500, detail="Unable to load current user")
    return {
        "username":       u["username"],
        "email":          u["email"],
        "stars":          u["stars"],
        "world":          u["current_world"],
        "level":          u["sub_level"],
        "email_verified": bool(u["email_verified"]),
    }

# ── Email verification endpoints ──────────────────────────────────────────────

@app.get("/verify-email", response_class=HTMLResponse)
def verify_email(token: str):
    """
    Clicked from the email link.  Marks the user as verified and shows a
    simple confirmation page the player can close and return to the game.
    """
    user = database.get_user_by_token(token)
    if not user:
        return HTMLResponse(content=_verification_page(
            success=False,
            message="This verification link is invalid or has already been used."
        ), status_code=400)

    database.mark_email_verified(user["username"])
    return HTMLResponse(content=_verification_page(
        success=True,
        message=f"Your email has been verified, {user['username']}! You can close this tab and return to the game."
    ))

@app.post("/resend-verification")
def resend_verification(request: Request, background_tasks: BackgroundTasks):
    """Re-send the verification email for the currently logged-in user."""
    username = get_session_username(request)
    user = database.get_user(username)
    if not user or not user["email"]:
        raise HTTPException(status_code=400, detail="No email address on file")
    if user["email_verified"]:
        return {"status": "already_verified"}

    token      = database.refresh_email_token(username)
    verify_url = _build_verification_url(request, token)
    background_tasks.add_task(send_verification_email, user["email"], username, verify_url)
    return {"status": "sent"}

def _verification_page(success: bool, message: str) -> str:
    color  = "#f0b429" if success else "#f05252"
    icon   = "✓" if success else "✗"
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Sudoku Arena — Email Verification</title>
<style>
  body{{margin:0;font-family:sans-serif;background:#0c0e14;color:#eef0f6;
       display:flex;align-items:center;justify-content:center;min-height:100vh;}}
  .card{{background:#1a1e2b;border:1px solid #252b3a;border-radius:20px;
          padding:48px 56px;text-align:center;max-width:480px;}}
  .icon{{font-size:3rem;color:{color};margin-bottom:16px;}}
  h1{{font-size:1.5rem;margin:0 0 12px;}}
  p{{color:#8890a8;}}
  a{{display:inline-block;margin-top:24px;padding:12px 24px;background:{color};
     color:#0c0e14;font-weight:700;border-radius:10px;text-decoration:none;}}
</style>
</head>
<body>
  <div class="card">
    <div class="icon">{icon}</div>
    <h1>{"Email Verified" if success else "Verification Failed"}</h1>
    <p>{message}</p>
    <a href="/">Return to Game</a>
  </div>
</body></html>"""

# ── Puzzle endpoints ──────────────────────────────────────────────────────────

@app.get("/get-personalized-puzzle")
def get_puzzle(request: Request, level: int = 30):
    username = get_session_username(request)
    board, solution = gen.generate_puzzle(level)
    return {"username": username, "puzzle": board, "solution": solution, "level": level}

@app.get("/get-daily-puzzle")
def get_daily_puzzle(request: Request):
    """
    Returns today's personal puzzle for the logged-in user.
    The same puzzle is returned for the entire calendar day, so the player
    can leave and come back without losing their board.  If SMTP is not
    configured, the puzzle is still available regardless of email_verified.
    """
    username   = get_session_username(request)
    today      = date.today().isoformat()          # e.g. "2025-06-09"
    cached     = database.get_daily_puzzle(username, today)

    if cached:
        puzzle, solution = cached
    else:
        # Difficulty 30 = moderate, good balance for a daily challenge
        puzzle, solution = gen.generate_puzzle(30)
        database.save_daily_puzzle(username, today, puzzle, solution, difficulty=30)

    return {
        "puzzle":   puzzle,
        "solution": solution,
        "date":     today,
    }

# ── Progress ──────────────────────────────────────────────────────────────────

@app.post("/update-progress")
def update_progress(data: ProgressUpdate, request: Request):
    username = get_session_username(request)
    conn     = database.get_db_connection()
    cursor   = conn.cursor()
    cursor.execute(
        """INSERT INTO game_logs (username, time_taken, mistakes, clues_remaining, mistake_positions)
           VALUES (?, ?, ?, ?, ?)""",
        (username, data.time_taken, data.mistakes, data.clues_remaining,
         json.dumps(data.mistake_positions))
    )
    stars_to_add = 3 if data.mistakes == 0 else 1
    cursor.execute(
        "UPDATE users SET stars = stars + ?, total_mistakes = total_mistakes + ? WHERE username = ?",
        (stars_to_add, data.mistakes, username)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "stars_awarded": stars_to_add}

# ── AI / analytics endpoints ──────────────────────────────────────────────────

@app.get("/get-ai-analysis")
def get_ai_analysis(request: Request):
    username   = get_session_username(request)
    today      = date.today().isoformat()
    cached     = database.get_daily_puzzle(username, today)

    if cached:
        board, _ = cached
    else:
        board, solution = gen.generate_puzzle(30)
        database.save_daily_puzzle(username, today, board, solution)

    return {
        "heatmap":    "<p>No puzzle history yet. Complete a game to see a heatmap.</p>",
        "tips":       "<ul><li>Start with rows/columns that have the most filled cells.</li>"
                      "<li>Use block elimination for each 3×3 box.</li>"
                      "<li>Look for naked singles first — cells with only one possible value.</li></ul>",
        "desc":       f"Your personal daily puzzle for {today}, {username}. Play it in full from the Daily Puzzle button.",
    }

@app.get("/get-personal-stats")
def get_personal_stats(request: Request):
    username = get_session_username(request)
    conn     = database.get_db_connection()
    stats    = conn.execute(
        """SELECT COUNT(*) AS games_played,
                  AVG(time_taken)  AS avg_time,
                  MIN(time_taken)  AS best_time,
                  SUM(mistakes)    AS total_mistakes
           FROM game_logs WHERE username = ?""",
        (username,)
    ).fetchone()
    conn.close()

    games_played   = stats["games_played"] or 0
    avg_time       = int(stats["avg_time"])    if stats["avg_time"]    is not None else 0
    best_time      = int(stats["best_time"])   if stats["best_time"]   is not None else 0
    total_mistakes = stats["total_mistakes"]   or 0
    accuracy       = round(max(0, 100 - total_mistakes * 5), 1) if games_played > 0 else 0

    return {
        "games_played": games_played,
        "avg_time":     avg_time,
        "best_time":    best_time,
        "accuracy":     accuracy,
    }

@app.get("/ai-daily-feedback")
def ai_daily_feedback(request: Request):
    username = get_session_username(request)
    return {"feedback": f"Keep going, {username}! Focus on blocks and row patterns for fewer mistakes."}

@app.post("/get-ai-hint")
def get_hint(req: HintRequest):
    for r in range(9):
        for c in range(9):
            if req.current_board[r][c] == 0:
                return {"row": r, "col": c, "val": req.solution[r][c]}
    return {"message": "Complete"}
