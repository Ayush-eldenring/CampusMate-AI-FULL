# CampusMate AI — YUKTHI 2026

A Flask + SQLite student campus companion prototype with six feature areas:

1. AI Academic Rescue — study tasks and progress tracking.
2. Smart Classroom Finder — searchable campus directory.
3. Voice-Based Campus Assistant — text chat and browser speech input.
4. Campus Skill Exchange — student skill listings and suggested matches.
5. AI Lost & Found — similarity-based possible matches.
6. Green Campus AI — maintenance reports, duplicate detection and status tracking.

## Open and run in VS Code (Windows)

1. Extract this project ZIP.
2. Open **VS Code**.
3. Select **File → Open Folder** and choose the `CampusMate_AI` folder.
4. Open **Terminal → New Terminal**.
5. Create a virtual environment:

   ```powershell
   py -m venv .venv
   ```

6. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks activation, use the Command Prompt terminal in VS Code and run:

   ```cmd
   .venv\Scripts\activate.bat
   ```

7. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

8. Start the app:

   ```powershell
   python app.py
   ```

9. Open **http://127.0.0.1:5000** in your browser. Stop the server with `Ctrl + C` in the VS Code terminal.

## Accounts

- Choose **Create an account** on the sign-in page.
- Use a valid email address and a password of at least 8 characters.
- Log in with that email and password on later visits.
- Passwords are stored as PBKDF2-HMAC-SHA256 hashes, not plain text.
- Study tasks are isolated per account. Skill Exchange, Lost & Found and Green Campus boards are shared demo boards, as intended for campus-wide participation.
- The SQLite database (`campusmate.db`) is created automatically on first run.

## Important prototype notes

- The assistant currently uses local rule-based responses. It is **not connected to a hosted generative AI model/API** yet.
- Campus directory entries, hours and notices are placeholders. Replace them with verified college information before relying on them.
- Voice input uses the browser's Web Speech API where supported; recognition availability depends on browser/device.
- This is a local development prototype, not production-ready authentication. Before public deployment, set a strong random `CAMPUSMATE_SECRET_KEY`, use HTTPS, add CSRF protection, rate limiting, password reset and email verification, and review privacy/security requirements.

## Project structure

```text
CampusMate_AI/
├── app.py
├── requirements.txt
├── README.md
├── campusmate.db          # generated automatically at runtime
├── templates/
│   ├── auth.html
│   └── index.html
└── static/
    ├── auth.js
    ├── app.js
    └── style.css
```
