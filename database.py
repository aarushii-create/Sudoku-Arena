import sqlite3
import os
import hashlib
import secrets
import json

DB_PATH = os.getenv("DATABASE_URL", "game.db")
PASSWORD_ITERATIONS = 100_000

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PASSWORD_ITERATIONS
    ).hex()
    return salt, pw_hash

def verify_password(password: str, salt: str, password_hash: str) -> bool:
    check_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), PASSWORD_ITERATIONS
    ).hex()
    return secrets.compare_digest(check_hash, password_hash)

# ── Schema ────────────────────────────────────────────────────────────────────

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username          TEXT PRIMARY KEY,
            email             TEXT,
            password_hash     TEXT,
            password_salt     TEXT,
            stars             INTEGER DEFAULT 0,
            current_world     TEXT    DEFAULT 'Easy',
            sub_level         INTEGER DEFAULT 1,
            total_mistakes    INTEGER DEFAULT 0,
            email_verified    INTEGER DEFAULT 0,
            email_token       TEXT    DEFAULT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_logs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            username         TEXT,
            time_taken       INTEGER,
            mistakes         INTEGER,
            clues_remaining  INTEGER,
            mistake_positions TEXT,
            timestamp        DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')

    # Daily puzzle cache — one row per (username, date)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_puzzles (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            username     TEXT    NOT NULL,
            puzzle_date  TEXT    NOT NULL,
            puzzle       TEXT    NOT NULL,
            solution     TEXT    NOT NULL,
            difficulty   INTEGER DEFAULT 30,
            UNIQUE(username, puzzle_date)
        )
    ''')

    # Migrate existing users table if columns are missing
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(users)").fetchall()}
    migrations = {
        "password_hash":  "ALTER TABLE users ADD COLUMN password_hash TEXT",
        "password_salt":  "ALTER TABLE users ADD COLUMN password_salt TEXT",
        "email":          "ALTER TABLE users ADD COLUMN email TEXT",
        "email_verified": "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0",
        "email_token":    "ALTER TABLE users ADD COLUMN email_token TEXT DEFAULT NULL",
    }
    for col, sql in migrations.items():
        if col not in existing_cols:
            cursor.execute(sql)

    conn.commit()
    conn.close()

# ── User CRUD ─────────────────────────────────────────────────────────────────

def get_user(username: str):
    conn = get_db_connection()
    user = conn.execute(
        """SELECT username, email, password_hash, password_salt,
                  stars, current_world, sub_level,
                  email_verified, email_token
           FROM users WHERE username = ?""",
        (username,)
    ).fetchone()
    conn.close()
    return user

def get_user_by_email(email: str):
    conn = get_db_connection()
    user = conn.execute(
        """SELECT username, email, password_hash, password_salt,
                  stars, current_world, sub_level,
                  email_verified, email_token
           FROM users WHERE email = ?""",
        (email,)
    ).fetchone()
    conn.close()
    return user

def get_user_by_identifier(identifier: str):
    conn = get_db_connection()
    user = conn.execute(
        """SELECT username, email, password_hash, password_salt,
                  stars, current_world, sub_level,
                  email_verified, email_token
           FROM users WHERE username = ? OR email = ?""",
        (identifier, identifier)
    ).fetchone()
    conn.close()
    return user

def create_user(username: str, password: str, email: str = None) -> str:
    """Create user and return a fresh email verification token."""
    salt, pw_hash = hash_password(password)
    token = secrets.token_urlsafe(32)
    conn = get_db_connection()
    try:
        existing = conn.execute(
            "SELECT password_hash, email FROM users WHERE username = ?", (username,)
        ).fetchone()

        if existing:
            updates, values = [], []
            if not existing["password_hash"]:
                updates += ["password_hash = ?", "password_salt = ?"]
                values  += [pw_hash, salt]
            if email and not existing["email"]:
                updates += ["email = ?", "email_token = ?", "email_verified = 0"]
                values  += [email, token]
            if updates:
                values.append(username)
                conn.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE username = ?",
                    tuple(values)
                )
                conn.commit()
        else:
            conn.execute(
                """INSERT INTO users
                   (username, email, password_hash, password_salt, email_verified, email_token)
                   VALUES (?, ?, ?, ?, 0, ?)""",
                (username, email, pw_hash, salt, token)
            )
            conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
    return token

def verify_user(identifier: str, password: str) -> bool:
    user = get_user_by_identifier(identifier)
    if not user or not user["password_hash"] or not user["password_salt"]:
        return False
    return verify_password(password, user["password_salt"], user["password_hash"])

# ── Email verification ────────────────────────────────────────────────────────

def get_user_by_token(token: str):
    """Look up a user by their email verification token."""
    conn = get_db_connection()
    user = conn.execute(
        "SELECT username, email, email_verified FROM users WHERE email_token = ?",
        (token,)
    ).fetchone()
    conn.close()
    return user

def mark_email_verified(username: str):
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET email_verified = 1, email_token = NULL WHERE username = ?",
        (username,)
    )
    conn.commit()
    conn.close()

def refresh_email_token(username: str) -> str:
    """Generate a new verification token for the user and return it."""
    token = secrets.token_urlsafe(32)
    conn = get_db_connection()
    conn.execute(
        "UPDATE users SET email_token = ?, email_verified = 0 WHERE username = ?",
        (token, username)
    )
    conn.commit()
    conn.close()
    return token

# ── Daily puzzle cache ────────────────────────────────────────────────────────

def get_daily_puzzle(username: str, date_str: str):
    """Return cached (puzzle, solution) for today, or None if not yet generated."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT puzzle, solution FROM daily_puzzles WHERE username = ? AND puzzle_date = ?",
        (username, date_str)
    ).fetchone()
    conn.close()
    if row:
        return json.loads(row["puzzle"]), json.loads(row["solution"])
    return None

def save_daily_puzzle(username: str, date_str: str, puzzle: list, solution: list, difficulty: int = 30):
    """Persist today's puzzle so it stays the same if the user refreshes."""
    conn = get_db_connection()
    conn.execute(
        """INSERT OR IGNORE INTO daily_puzzles (username, puzzle_date, puzzle, solution, difficulty)
           VALUES (?, ?, ?, ?, ?)""",
        (username, date_str, json.dumps(puzzle), json.dumps(solution), difficulty)
    )
    conn.commit()
    conn.close()
