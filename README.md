# SmartLearn

SmartLearn is a responsive online learning platform starter with course discovery, learner registration and login, enrolment, and a personal learning dashboard.

## Deploy

The app is configured for Railway. Set `SECRET_KEY` to a long random value. For persistent production data, attach a MySQL service and set `DATABASE_URL` to its connection URL (Railway MySQL commonly provides `MYSQL_URL`; map it to `DATABASE_URL`). The app supports SQLite for local testing.

## Local run

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. Health endpoint: `/health`.
