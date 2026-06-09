# Contributing to Sudoku Arena

Thank you for your interest in contributing to Sudoku Arena! This project
welcomes improvements, bug fixes, documentation updates, and new ideas.

## How to contribute

1. Fork the repository.
2. Create a new branch for your change:
   ```bash
git checkout -b feature/my-new-idea
```
3. Make your changes.
4. Run the application locally and verify your changes work.
5. Commit your work with a clear message.
6. Open a pull request describing what you changed and why.

## Development setup

1. Install dependencies:
   ```bash
pip install -r requirements.txt
```
2. Start the server:
   ```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
3. Open `http://127.0.0.1:8000/` in your browser.

## Contribution guidelines

- Keep code changes small and focused.
- Add or update documentation when behavior changes.
- Use clear commit messages.
- If you add new features, include any required configuration details.

## Reporting bugs

If you find a bug, please include:
- A short description of the issue
- Steps to reproduce
- Expected behavior vs actual behavior
- Any relevant error messages or logs

## Suggestions

If you have a feature idea, describe:
- What it does
- Why it is useful
- How it should work from a user perspective

Thank you for helping improve Sudoku Arena!