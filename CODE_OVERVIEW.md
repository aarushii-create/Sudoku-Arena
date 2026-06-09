# Sudoku Arena — Architecture and Technology Overview

This document explains the structure of the project, the role of each file,
and the reasoning behind the major design decisions.

## Project purpose

Sudoku Arena is a full-featured Sudoku game with a Python backend and a static
frontend. The app is designed to be self-contained, easy to deploy, and useful
for demonstrating:

- Puzzle generation with uniqueness enforcement
- User authentication and session management
- Email verification via SMTP
- Persistent user statistics and daily puzzles
- Responsive browser-based UI without a JavaScript framework

---

## Architecture summary

### Backend

- FastAPI provides a clean, declarative API surface.
- Starlette `SessionMiddleware` stores session state in signed cookies.
- SQLite is used as a lightweight persistent store with simple schema migration
  logic built into `database.init_db()`.
- Email verification is implemented using standard library `smtplib` and MIME.
- Puzzle generation relies on a custom backtracking generator in `generator.py`.

### Frontend

- A single HTML shell in `static/index.html` contains all page sections.
- `static/script.js` handles auth, puzzle loading, board rendering, and game state.
- `static/style.css` defines the visual theme, responsive layout, and hover states.

### Deployment

- `Dockerfile` packages the app in `python:3.11-slim` and runs `uvicorn`.
- No build step or bundler is required for the frontend.

---

## Detailed file breakdown

### `main.py`

This is the application entry point and implements all backend behavior.

#### Request models

- `AuthRequest`
  - `username`: required
  - `password`: required
  - `email`: optional for login, required for registration
- `HintRequest`
  - `current_board`: current game board state
  - `solution`: solution board used to provide hints
- `ProgressUpdate`
  - `time_taken`, `mistakes`, `clues_remaining`, `mistake_positions`

#### App setup

- `FastAPI()` initializes the API.
- `SessionMiddleware` uses `SESSION_SECRET` to sign cookies.
- CORS is configured to allow all origins, methods, and headers.
- `app.mount('/static', StaticFiles(...))` serves the frontend assets.

#### Email helper functions

- `_build_verification_url(request, token)` builds a URL using either
  `APP_BASE_URL` or `request.base_url`.
- `send_verification_email(to_email, username, verify_url)` sends a styled HTML
  message through SMTP.
- If SMTP credentials are missing, the function logs a warning and returns.

#### Email validation

- `is_valid_email(email)` uses `parseaddr()` plus a regex to verify format.
- This is used by `/register` to ensure only properly formatted emails are accepted.

#### Session helper

- `get_session_username(request)` extracts `username` from the session or raises
  an HTTP 401 if the request is not authenticated.

#### Auth endpoints

- `POST /register`
  - Validates username, password, email presence
  - Validates email format and uniqueness
  - Creates the user and verification token via `database.create_user()`
  - Sends verification email in a background task
  - Stores the username in the session
- `POST /login`
  - Accepts username or email as identifier
  - Verifies password using `database.verify_user()`
  - Sets session username on success
- `POST /logout`
  - Clears session data
- `GET /current-user`
  - Returns the authenticated user’s profile data

#### Verification endpoints

- `GET /verify-email`
  - Reads the token from the query string
  - Marks the associated user verified
  - Sends a simple HTML response to confirm verification
- `POST /resend-verification`
  - Resends a new token to the logged-in user if not already verified

#### Puzzle endpoints

- `GET /get-personalized-puzzle`
  - Generates a new puzzle on every request
  - Uses `generator.generate_puzzle(level)`
- `GET /get-daily-puzzle`
  - Returns a cached puzzle for the current user and date
  - If missing, generates and saves a new puzzle

#### Progress and analytics

- `POST /update-progress`
  - Logs completed games in `game_logs`
  - Awards stars (3 for zero mistakes, otherwise 1)
  - Increments total mistakes for the user
- `GET /get-ai-analysis`
  - Returns a static tip list and placeholder heatmap markup
- `GET /get-personal-stats`
  - Aggregates `game_logs` to compute play stats
- `GET /ai-daily-feedback`
  - Returns a motivational text string
- `POST /get-ai-hint`
  - Finds the first empty cell and returns its solution value

---

### `database.py`

This module encapsulates database access and schema management.

#### Connection helper

- `get_db_connection()` returns a SQLite connection with `row_factory`
  set to `sqlite3.Row` for dictionary-like results.

#### Password helpers

- `hash_password(password)` generates a random salt and PBKDF2-SHA256 hash.
- `verify_password(password, salt, password_hash)` compares the computed hash
  against the stored value using `secrets.compare_digest()`.

#### Schema and migrations

- `init_db()` creates three tables: `users`, `game_logs`, `daily_puzzles`.
- It also checks existing `users` columns and runs ALTER TABLE migrations if
  needed, making the startup safe for older databases.

#### User CRUD

- `get_user(username)` loads a user by username.
- `get_user_by_email(email)` loads a user by email.
- `get_user_by_identifier(identifier)` loads a user by username or email.
- `create_user(username, password, email)` inserts a new user or upgrades an
  existing placeholder row.
- `verify_user(identifier, password)` checks login credentials.

#### Email verification storage

- `get_user_by_token(token)` looks up the pending verification token.
- `mark_email_verified(username)` sets `email_verified=1` and clears the token.
- `refresh_email_token(username)` issues a new token and resets verification state.

#### Daily puzzle cache

- `get_daily_puzzle(username, date_str)` returns cached puzzle/solution if present.
- `save_daily_puzzle(username, date_str, puzzle, solution, difficulty)` stores a
  puzzle for the day using `INSERT OR IGNORE`.

---

### `generator.py`

Produces playable Sudoku puzzles on demand.

- Inherits from `SudokuEngine`.
- `fill_grid(board)` fills an empty board with a complete valid solution.
- `count_solutions(board)` checks how many full solutions exist, stopping after
  two.
- `generate_puzzle(difficulty_level)` removes numbers randomly while preserving
  uniqueness until the target clue count is reached.

This generator is intentionally simple and safe: it always verifies that the
puzzle remains uniquely solvable.

---

### `sudoku_engine.py`

Implements core Sudoku rules and solver utilities.

- `is_valid(board, row, col, num)` checks whether `num` can be placed in a cell.
- `find_empty(board)` scans for the next empty cell.
- `solve(board)` uses backtracking to solve a board.
- `print_board(board)` prints the board for debugging.

This module is the foundation for both generation and any solver-related UI
features.

---

### `static/index.html`

The single-page UI shell contains:

- authentication overlay
- verification banner
- game board grid
- number input panel
- difficulty selector
- daily puzzle preview
- AI lab section with analysis and personal progress

The page is intentionally structured for progressive enhancement, with the
JavaScript layer controlling visibility and data loading.

---

### `static/script.js`

Frontend logic and user interactions.

#### Session and auth

- `restoreSession()` checks `GET /current-user`.
- `submitAuth()` handles registration and login.
- `setAuthMode(mode)` toggles between register/login UI.

#### Email validation

- Registration validates email syntax client-side with a regex.
- The backend also validates email format server-side.

#### Puzzle lifecycle

- `fetchNewPuzzle()` loads a new game from `/get-personalized-puzzle`.
- `playDailyPuzzle()` loads `/get-daily-puzzle` and preserves the same board
  across refreshes for the day.

#### Board rendering

- `renderBoard(p)` builds the game grid.
- Input selection, highlighting, and error styling are managed entirely in JS.

#### Verification banner

- `showVerifyBanner()` and `resendVerification()` let unverified users request
  a new verification email.

---

### `static/style.css`

The CSS defines:

- dark and light theme palettes
- responsive grid layout for mobile/tablet/desktop
- board and cell styling for fixed vs editable values
- banner styling for email verification notices
- animated hover and focus states for interactive controls

---

### `requirements.txt`

| Package | Purpose |
|---------|---------|
| `fastapi` | API framework |
| `uvicorn[standard]` | ASGI server |
| `pydantic` | Request validation |
| `python-multipart` | Form upload support |
| `itsdangerous` | Session signing support |
| `starlette` | ASGI toolkit used by FastAPI |
| `python-dotenv` | Optional environment file loading |

---

### `Dockerfile`

- Uses `python:3.11-slim`
- Installs requirements from `requirements.txt`
- Copies the full application into `/app`
- Exposes `8000`
- Runs `uvicorn main:app --host 0.0.0.0 --port 8000`

---

## Internal design notes

### Email verification flow

1. `POST /register` validates input and rejects bad emails.
2. The backend generates an email token and creates/updates the user row.
3. A verification email is sent asynchronously.
4. `GET /verify-email` completes verification and returns a confirmation page.

### Daily puzzle persistence

- `GET /get-daily-puzzle` first checks `daily_puzzles` for the current username/date
- If a row exists, it returns the cached board and solution
- If not, it generates a new puzzle, saves it, and returns it

This ensures users can continue the same puzzle throughout the day.

### Data model decisions

- `users.email` is optional in the schema but required for registration.
- `email_verified` is stored as a boolean flag in SQLite (`0/1`).
- `mistake_positions` are stored as JSON so the frontend can later render
  heatmaps or analytics.
- `daily_puzzles` uses `UNIQUE(username, puzzle_date)` to guarantee one board
  per user per day.

---

## Recommended improvements

- Build real heatmap rendering from `mistake_positions`
- Add a password reset flow via email
- Add expiry for verification tokens
- Add unit tests for puzzle generation and database logic
- Add a leaderboard or social user metrics
