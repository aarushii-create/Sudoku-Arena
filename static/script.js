/* ════════════════════════════════════════════════════
   SUDOKU ARENA — script.js
   ════════════════════════════════════════════════════ */

let currentUser     = null;
let currentSolution = [];
let selectedCell    = null;
let seconds         = 0;
let timerInterval   = null;
let gameActive      = false;
let isPaused        = true;
let mistakes        = 0;
let mistakePositions = [];

/* authMode must be declared BEFORE DOMContentLoaded */
let authMode = 'register';

/* ─────────────────────────────────────────────────────
   INIT
───────────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    setAuthMode(authMode);
    await restoreSession();
});

/* ─────────────────────────────────────────────────────
   THEME
───────────────────────────────────────────────────── */
function initTheme() {
    const savedTheme = localStorage.getItem('sudokuTheme') || 'dark';
    setTheme(savedTheme);
}

function toggleTheme() {
    const nextTheme = document.body.classList.contains('light') ? 'dark' : 'light';
    setTheme(nextTheme);
}

function setTheme(theme) {
    document.body.classList.toggle('light', theme === 'light');
    const icon = theme === 'light' ? '☾' : '☀';
    document.querySelectorAll('.theme-icon').forEach(el => el.textContent = icon);
    localStorage.setItem('sudokuTheme', theme);
}

/* ─────────────────────────────────────────────────────
   SESSION
───────────────────────────────────────────────────── */
async function restoreSession() {
    try {
        const res = await fetch('/current-user', { credentials: 'include' });
        if (!res.ok) { showOverlay(); return; }
        currentUser = await res.json();
        hideOverlay();
        updateUI();
        await fetchNewPuzzle();
        await loadDailyFeedback();
    } catch (err) {
        console.error('Session restore failed:', err);
        showOverlay();
    }
}

function showOverlay() {
    const el = document.getElementById('login-overlay');
    if (el) el.style.display = 'flex';
}

function hideOverlay() {
    const el = document.getElementById('login-overlay');
    if (el) el.style.display = 'none';
}

/* ─────────────────────────────────────────────────────
   AUTH
───────────────────────────────────────────────────── */
function setAuthMode(mode) {
    authMode = mode;

    const title          = document.getElementById('auth-title');
    const note           = document.getElementById('auth-note');
    const submit         = document.getElementById('auth-submit');
    const confirmWrapper = document.getElementById('confirm-password-wrapper');
    const emailWrapper   = document.getElementById('email-field');
    const switchText     = document.getElementById('auth-switch-text');
    const signupTab      = document.getElementById('signup-tab');
    const loginTab       = document.getElementById('login-tab');

    function setSubmitLabel(text) {
        const span = submit ? submit.querySelector('span') : null;
        if (span) span.textContent = text;
        else if (submit) submit.textContent = text;
    }

    if (mode === 'register') {
        if (title)          title.textContent = 'Create Account';
        if (note)           note.textContent  = 'Join thousands of solvers. Track your progress.';
        setSubmitLabel('SIGN UP');
        if (emailWrapper)   emailWrapper.style.display   = 'flex';
        if (confirmWrapper) confirmWrapper.style.display = 'flex';
        if (switchText)     switchText.innerHTML = 'Already have an account? <button class="link-btn" onclick="setAuthMode(\'login\')">Log in</button>';
        if (signupTab)      signupTab.classList.add('active');
        if (loginTab)       loginTab.classList.remove('active');
    } else {
        if (title)          title.textContent = 'Welcome Back';
        if (note)           note.textContent  = 'Log in using your username or email and password.';
        setSubmitLabel('LOG IN');
        if (emailWrapper)   emailWrapper.style.display   = 'none';
        if (confirmWrapper) confirmWrapper.style.display = 'none';
        if (switchText)     switchText.innerHTML = 'New here? <button class="link-btn" onclick="setAuthMode(\'register\')">Create account</button>';
        if (signupTab)      signupTab.classList.remove('active');
        if (loginTab)       loginTab.classList.add('active');
    }

    const errorEl = document.getElementById('auth-error');
    if (errorEl) errorEl.textContent = '';
}

async function submitAuth() {
    try {
        const username        = document.getElementById('username-input').value.trim();
        const email           = document.getElementById('email-input').value.trim();
        const password        = document.getElementById('password-input').value;
        const confirmPassword = document.getElementById('confirm-password-input').value;
        const errorEl         = document.getElementById('auth-error');
        errorEl.textContent   = '';

        if (!username || !password) {
            errorEl.textContent = 'Please enter both username and password.';
            return;
        }
        if (authMode === 'register') {
            const emailRegex = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
            if (!email || !emailRegex.test(email)) {
                errorEl.textContent = 'Please enter a valid email address.';
                return;
            }
            if (password !== confirmPassword) {
                errorEl.textContent = 'Passwords do not match.';
                return;
            }
        }

        const payload = { username, password };
        if (authMode === 'register') payload.email = email;

        const res = await fetch(`/${authMode}`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const body = await res.json().catch(() => ({}));
            errorEl.textContent = body.detail || 'Authentication failed. Please try again.';
            return;
        }

        currentUser = await res.json();
        hideOverlay();
        updateUI();
        await fetchNewPuzzle();
        await loadDailyFeedback();
    } catch (err) {
        console.error('Authentication error:', err);
        document.getElementById('auth-error').textContent = 'Unable to connect to server.';
    }
}

/* ─────────────────────────────────────────────────────
   EMAIL VERIFICATION BANNER
───────────────────────────────────────────────────── */
function showVerifyBanner() {
    const banner = document.getElementById('verify-banner');
    if (banner) banner.style.display = 'flex';
}

function hideVerifyBanner() {
    const banner = document.getElementById('verify-banner');
    if (banner) banner.style.display = 'none';
}

async function resendVerification() {
    const btn = document.getElementById('resend-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }

    try {
        const res = await fetch('/resend-verification', {
            method: 'POST',
            credentials: 'include'
        });
        const data = await res.json();

        const textEl = document.getElementById('verify-banner-text');
        if (data.status === 'already_verified') {
            if (textEl) textEl.textContent = 'Your email is already verified!';
            hideVerifyBanner();
            if (currentUser) currentUser.email_verified = true;
        } else {
            if (textEl) textEl.textContent = `Verification email sent to ${currentUser?.email || 'your address'}. Check your inbox.`;
            if (btn) { btn.textContent = 'Sent ✓'; }
        }
    } catch (err) {
        console.error('Resend failed:', err);
        if (btn) { btn.disabled = false; btn.textContent = 'Resend email'; }
    }
}

/* ─────────────────────────────────────────────────────
   PUZZLE FETCH  (arena — generates a new puzzle each time)
───────────────────────────────────────────────────── */
async function fetchNewPuzzle() {
    if (!currentUser) return;

    const checkedRadio = document.querySelector('input[name="difficulty"]:checked');
    const difficultySelect = document.getElementById('difficulty-select');
    if (checkedRadio) difficultySelect.value = checkedRadio.value;

    const difficulty = difficultySelect.value;
    const res = await fetch(`/get-personalized-puzzle?level=${difficulty}`, { credentials: 'include' });
    if (!res.ok) { console.error('Unable to load puzzle', res.statusText); return; }

    const data = await res.json();
    currentSolution = data.solution;
    resetState();
    renderBoard(data.puzzle);
}

/* ─────────────────────────────────────────────────────
   DAILY PUZZLE  (persistent — same puzzle all day)
───────────────────────────────────────────────────── */
async function playDailyPuzzle() {
    if (!currentUser) return;

    const btn = document.getElementById('play-daily-btn');
    if (btn) { btn.disabled = true; btn.querySelector('span').textContent = 'Loading…'; }

    try {
        const res = await fetch('/get-daily-puzzle', { credentials: 'include' });
        if (!res.ok) { console.error('Failed to load daily puzzle', res.statusText); return; }

        const data = await res.json();
        currentSolution = data.solution;
        resetState();
        renderBoard(data.puzzle);

        /* Switch to Arena tab so the player can actually play */
        await showSection('arena');

        const pauseBtn = document.getElementById('pause-btn');
        const span = pauseBtn ? pauseBtn.querySelector('span') : null;
        if (span) span.textContent = 'Start (Daily)';
        else if (pauseBtn) pauseBtn.textContent = 'Start (Daily)';
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.querySelector('span').textContent = 'Play Daily Puzzle';
        }
    }
}

/* ─────────────────────────────────────────────────────
   BOARD RENDER
───────────────────────────────────────────────────── */
function renderBoard(p) {
    const b = document.getElementById('sudoku-board');
    b.innerHTML = '';
    p.forEach((row, r) => row.forEach((val, c) => {
        const cell = document.createElement('div');
        cell.className = 'cell' + (val !== 0 ? ' fixed' : '');
        cell.textContent = val !== 0 ? val : '';
        cell.dataset.row = r;
        cell.dataset.col = c;
        cell.setAttribute('role', 'gridcell');
        cell.setAttribute('aria-label', val !== 0
            ? `Row ${r+1} Column ${c+1} value ${val}`
            : `Row ${r+1} Column ${c+1} empty`);
        if (val === 0) cell.onclick = () => { if (!isPaused) selectCell(cell); };
        b.appendChild(cell);
    }));
}

/* ─────────────────────────────────────────────────────
   CELL SELECTION & HIGHLIGHTING
───────────────────────────────────────────────────── */
function selectCell(c) {
    if (selectedCell) selectedCell.classList.remove('selected');
    selectedCell = c;
    selectedCell.classList.add('selected');
    highlightPeers(c);
    highlightSameNumbers(c);
}

function highlightPeers(cell) {
    clearHighlights();
    const row    = parseInt(cell.dataset.row, 10);
    const col    = parseInt(cell.dataset.col, 10);
    const boxRow = Math.floor(row / 3) * 3;
    const boxCol = Math.floor(col / 3) * 3;

    document.querySelectorAll('#sudoku-board .cell').forEach(c => {
        const r  = parseInt(c.dataset.row, 10);
        const co = parseInt(c.dataset.col, 10);
        const inBox = r >= boxRow && r < boxRow + 3 && co >= boxCol && co < boxCol + 3;
        if ((r === row || co === col || inBox) && c !== cell) c.classList.add('peer');
    });
}

function highlightSameNumbers(cell) {
    const num = cell.textContent.trim();
    if (!num) return;
    document.querySelectorAll('#sudoku-board .cell').forEach(c => {
        if (c !== cell && c.textContent.trim() === num) c.classList.add('same-num');
    });
}

function clearHighlights() {
    document.querySelectorAll('#sudoku-board .cell').forEach(c => {
        c.classList.remove('peer', 'same-num');
    });
}

/* ─────────────────────────────────────────────────────
   NUMBER INPUT
───────────────────────────────────────────────────── */
function inputNumber(n) {
    if (!selectedCell || isPaused || selectedCell.classList.contains('fixed')) return;

    selectedCell.textContent = n === 0 ? '' : n;
    const r = parseInt(selectedCell.dataset.row, 10);
    const c = parseInt(selectedCell.dataset.col, 10);

    if (n !== 0 && n != currentSolution[r][c]) {
        selectedCell.classList.add('error');
        selectedCell.classList.remove('same-num');
        mistakes++;
        updateMistakeCounter();
        mistakePositions.push([r, c]);
    } else {
        selectedCell.classList.remove('error');
        highlightSameNumbers(selectedCell);
        if (n !== 0) checkWin();
    }
    if (selectedCell) highlightPeers(selectedCell);
}

function updateMistakeCounter() {
    const el = document.getElementById('mistake-counter');
    if (el) el.textContent = mistakes;
}

/* ─────────────────────────────────────────────────────
   GAME STATE
───────────────────────────────────────────────────── */
function resetState() {
    clearInterval(timerInterval);
    seconds = 0; mistakes = 0; isPaused = true; gameActive = true;
    selectedCell = null;
    document.getElementById('timer').textContent = '00:00';
    document.getElementById('pause-overlay').style.display = 'flex';
    document.getElementById('overlay-status').textContent = 'Ready?';

    const pauseBtn = document.getElementById('pause-btn');
    if (pauseBtn) {
        const span = pauseBtn.querySelector('span');
        if (span) span.textContent = 'Start';
        else pauseBtn.textContent = 'Start';
    }

    updateMistakeCounter();
    mistakePositions = [];
    clearHighlights();
}

function toggleGame() {
    if (!gameActive) return;
    isPaused = !isPaused;

    document.getElementById('pause-overlay').style.display = isPaused ? 'flex' : 'none';

    const pauseBtn = document.getElementById('pause-btn');
    if (pauseBtn) {
        const span  = pauseBtn.querySelector('span');
        const label = isPaused ? 'Start' : 'Pause';
        if (span) span.textContent = label; else pauseBtn.textContent = label;
    }

    if (!isPaused) {
        timerInterval = setInterval(() => {
            seconds++;
            const m = Math.floor(seconds / 60).toString().padStart(2, '0');
            const s = (seconds % 60).toString().padStart(2, '0');
            document.getElementById('timer').textContent = `${m}:${s}`;
        }, 1000);
    } else {
        clearInterval(timerInterval);
    }
}

/* ─────────────────────────────────────────────────────
   WIN DETECTION
───────────────────────────────────────────────────── */
function checkWin() {
    const cells = Array.from(document.querySelectorAll('#sudoku-board .cell'));
    if (cells.every(c => c.textContent !== '' && !c.classList.contains('error'))) {
        gameActive = false;
        clearInterval(timerInterval);
        triggerWin();
    }
}

async function triggerWin() {
    let stars = 1;
    if (mistakes === 0 && seconds < 90) stars = 3;
    else if (mistakes <= 2) stars = 2;

    const currentBoard   = getCurrentBoardState();
    const cluesRemaining = currentBoard.flat().filter(v => v === 0).length;
    await submitGame(seconds, mistakes, cluesRemaining, mistakePositions);

    const starEl = document.getElementById('star-rating');
    if (starEl) starEl.textContent = '★'.repeat(stars) + '☆'.repeat(3 - stars);

    document.getElementById('win-modal').style.display = 'flex';

    if (typeof confetti === 'function') {
        confetti({ particleCount: 120, spread: 80, origin: { y: 0.5 },
                   colors: ['#f0b429', '#ffc947', '#ffffff'] });
    }
}

function nextLevel() {
    document.getElementById('win-modal').style.display = 'none';
    fetchNewPuzzle();
}

/* ─────────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────────── */
function getCurrentBoardState() {
    const board = Array.from({ length: 9 }, () => Array(9).fill(0));
    document.querySelectorAll('#sudoku-board .cell').forEach(cell => {
        const row   = parseInt(cell.dataset.row, 10);
        const col   = parseInt(cell.dataset.col, 10);
        const value = parseInt(cell.textContent, 10);
        board[row][col] = Number.isFinite(value) ? value : 0;
    });
    return board;
}

function highlightHintCell(row, col) {
    resetHintHighlights();
    const cell = document.querySelector(
        `#sudoku-board .cell[data-row='${row}'][data-col='${col}']`
    );
    if (!cell) return;
    cell.classList.add('hint');
    setTimeout(() => cell.classList.remove('hint'), 2800);
}

function resetHintHighlights() {
    document.querySelectorAll('#sudoku-board .cell.hint').forEach(el => el.classList.remove('hint'));
}

function renderPreviewBoard(puzzle) {
    const preview = document.getElementById('preview-board');
    if (!preview) return;
    preview.innerHTML = '';
    puzzle.forEach((row) => row.forEach((val) => {
        const cell = document.createElement('div');
        cell.className = 'cell' + (val !== 0 ? ' fixed' : '');
        cell.textContent = val !== 0 ? val : '';
        preview.appendChild(cell);
    }));
}

/* ─────────────────────────────────────────────────────
   UI UPDATE
───────────────────────────────────────────────────── */
function updateUI() {
    const starEl    = document.getElementById('star-count');
    const userLabel = document.getElementById('user-label');
    if (starEl)    starEl.textContent    = currentUser.stars;
    if (userLabel) userLabel.textContent = currentUser.username.toUpperCase();

    /* Difficulty lock */
    const medRadio  = document.getElementById('opt-med');
    const hardRadio = document.getElementById('opt-hard');
    const medSel    = document.getElementById('opt-med-sel');
    const hardSel   = document.getElementById('opt-hard-sel');
    if (medRadio)  medRadio.disabled  = currentUser.stars < 25;
    if (hardRadio) hardRadio.disabled = currentUser.stars < 75;
    if (medSel)    medSel.disabled    = currentUser.stars < 25;
    if (hardSel)   hardSel.disabled   = currentUser.stars < 75;

    /* Email verification banner */
    if (currentUser.email_verified === false || currentUser.email_verified === 0) {
        showVerifyBanner();
    } else {
        hideVerifyBanner();
    }
}

/* ─────────────────────────────────────────────────────
   NAVIGATION
───────────────────────────────────────────────────── */
async function showSection(id) {
    document.getElementById('arena-section').style.display  = id === 'arena'  ? 'block' : 'none';
    document.getElementById('ai-lab-section').style.display = id === 'ai-lab' ? 'block' : 'none';

    document.querySelectorAll('.nav-pill').forEach(b => b.classList.remove('active'));
    const navEl = document.getElementById('nav-' + id);
    if (navEl) navEl.classList.add('active');

    if (id === 'ai-lab') await loadAILab();
}

/* ─────────────────────────────────────────────────────
   AI LAB
───────────────────────────────────────────────────── */
async function loadAILab() {
    const analysisRes = await fetch('/get-ai-analysis', { credentials: 'include' });
    if (!analysisRes.ok) { console.error('AI analysis failed'); return; }
    const analysis = await analysisRes.json();

    document.getElementById('mistake-heatmap').innerHTML = analysis.heatmap;
    document.getElementById('tips-content').innerHTML    = analysis.tips;

    /* Load today's daily puzzle for the preview */
    const dailyRes = await fetch('/get-daily-puzzle', { credentials: 'include' });
    if (dailyRes.ok) {
        const daily = await dailyRes.json();
        renderPreviewBoard(daily.puzzle);

        /* Format the date nicely, e.g. "Monday, 9 Jun 2025" */
        const dateObj   = new Date(daily.date + 'T00:00:00');
        const formatted = dateObj.toLocaleDateString(undefined, {
            weekday: 'long', year: 'numeric', month: 'short', day: 'numeric'
        });
        const chip = document.getElementById('daily-date-chip');
        if (chip) chip.textContent = formatted;
    }

    if (analysis.desc) {
        document.getElementById('preview-desc').textContent = analysis.desc;
    }

    const statsRes = await fetch('/get-personal-stats', { credentials: 'include' });
    if (!statsRes.ok) { console.error('Stats fetch failed'); return; }
    const stats = await statsRes.json();

    document.getElementById('games-played').textContent = stats.games_played;
    document.getElementById('avg-time').textContent     = stats.avg_time;
    document.getElementById('best-time').textContent    = stats.best_time;
    document.getElementById('accuracy').textContent     = stats.accuracy;
}

/* ─────────────────────────────────────────────────────
   API CALLS (unchanged logic)
───────────────────────────────────────────────────── */
async function getAIHint() {
    const currentBoard = getCurrentBoardState();
    const res = await fetch('/get-ai-hint', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_board: currentBoard, solution: currentSolution })
    });
    const data = await res.json();
    if (data.row !== undefined) highlightHintCell(data.row, data.col);
    else if (data.message)    console.log(data.message);
}

async function submitGame(time, mistakes, clues, pos) {
    const res = await fetch('/update-progress', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            time_taken: time, mistakes, clues_remaining: clues, mistake_positions: pos
        })
    });
    if (!res.ok) { console.error('Failed to submit game progress', res.statusText); return null; }
    return res.json();
}

async function quitGame() {
    if (confirm('Are you sure you want to quit? This will end your session.')) {
        const res = await fetch('/logout', { method: 'POST', credentials: 'include' });
        if (!res.ok) console.error('Logout failed');
        currentUser = null;
        location.reload();
    }
}

async function loadDailyFeedback() {
    const res = await fetch('/ai-daily-feedback', { credentials: 'include' });
    if (!res.ok) return;
    const data  = await res.json();
    const msgEl = document.getElementById('ai-message');
    if (msgEl) msgEl.textContent = data.feedback;
}

/* ─────────────────────────────────────────────────────
   INPUT BINDINGS
───────────────────────────────────────────────────── */
document.querySelectorAll('.numpad-btn').forEach(b => {
    b.onclick = () => inputNumber(parseInt(b.dataset.num, 10));
});

document.getElementById('erase-btn').onclick = () => inputNumber(0);

document.addEventListener('keydown', e => {
    if (e.key >= '1' && e.key <= '9') inputNumber(parseInt(e.key, 10));
    else if (e.key === 'Backspace' || e.key === 'Delete') inputNumber(0);
    else if (e.key === 'Escape' && gameActive && !isPaused) toggleGame();
});
