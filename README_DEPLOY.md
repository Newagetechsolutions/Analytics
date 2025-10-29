# WinGo Dashboard — quick deploy
1. Create a new GitHub repo and push these files.
2. In Render:
   - New → Web Service
   - Connect to GitHub repo
   - Build: pip install -r requirements.txt
   - Start: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1
3. App auto-fetches data every 60s and serves dashboard.