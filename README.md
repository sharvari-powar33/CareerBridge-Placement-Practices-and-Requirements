# CareerBrigade

**AI-powered placement preparation platform — Prepare. Practice. Get placed.**

CareerBrigade is a student placement-preparation web application built from the supplied project synopsis and feature brief. It brings resume review, aptitude practice, technical practice, company preparation, progress tracking, profile management and recent activity into one responsive interface.

## Run locally

Requirements: Python 3.10 or newer.

```powershell
cd CareerBrigade
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. Create an account with a valid email and a password of at least 8 characters containing uppercase and lowercase letters, a number and a special character. The application creates its SQLite database (`careerbrigade.db`) on first run.

## Included modules

- Account registration, login, password hashing, session logout and remember-me control.
- Student dashboard with resume, aptitude, technical, company-preparation and placement-readiness scores, recent activity and shortcuts.
- PDF/DOCX resume upload, text extraction, heuristic ATS score, skills detected/missing, completeness checks and actionable suggestions.
- Aptitude, programming-language and company practice setup. Select Easy/Medium/Hard; Aptitude and Technical support 10, 25, 50 or 100 questions. Sets use distinct prompts and parameters, and served questions are recorded per account to avoid reuse. Navigate back and forward, submit answers, see explanations and save scores.
- Progress history, latest category scores, profile editing and account logout.
- Page-to-page Back navigation and a Close Project control that stops the local Flask server and prints a completion message in the terminal.
- Responsive dark sign-in screen and responsive student workspace.

## Project layout

```text
CareerBrigade/
├── app.py                 Flask routes, session auth and SQLite data layer
├── requirements.txt       Python dependencies
├── README.md
└── static/
    ├── index.html
    ├── style.css
    └── app.js
```

## Notes for project submission

The synopsis lists MySQL as the database. This runnable edition uses SQLite by default so a student can launch it without installing or configuring a database server. To use MySQL for a deployment, replace the small SQLite data-access layer in `app.py` with a MySQL connector and configure credentials through environment variables. The current resume score and suggestions are transparent, rule-based heuristics; they do not call an external AI service. The included practice bank is a starter bank for demonstrating the full test workflow and should be expanded and reviewed by the project team before a formal production or academic question-bank submission. Add the institution's approved questions and verify answer keys before a live assessment.

For deployment, set a strong `CAREERBRIGADE_SECRET`, disable Flask debug mode, use HTTPS, and configure persistent storage and upload retention policies.
