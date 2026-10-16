# FriendNet – Social Network Friend Recommendation System (Phase 3)

A Flask web application that stores a social network in a database and applies graph algorithms
(mutual friends, friends-of-friends ranking, BFS, shortest path) written in plain Python.
It does not use machine learning; all results come from the stored graph.

## Features
- Users: add, list, search by name, view profile, remove (with confirmation), duplicate and invalid-name checks
- Friendships: create / remove, no self-friendship, no duplicates, always symmetric
- Mutual friends via set intersection
- Ranked friend recommendations with an explanation for each candidate
- BFS traversal of a user's connected component
- Shortest connection path (BFS) with link count and "no path" message
- Network statistics computed live from the stored data
- Persistent storage: SQLite locally, PostgreSQL in production
- CSRF protection on all POST forms, parameterized SQL, auto-escaped templates

## Technologies
Python 3, Flask, Jinja2, `sqlite3` (local), PostgreSQL via `psycopg` (production), `unittest`, HTML/CSS and a small JS file (confirm dialogs, mobile menu).

## Folder structure
```
app.py                Flask app + routes (Vercel entry point, exposes `app`)
graph.py              SocialGraph: adjacency list, BFS, shortest path
recommendations.py    mutual friends, recommendation ranking, statistics
database.py           SQLite / PostgreSQL data access and validation
templates/            Jinja2 pages
public/static/        CSS and JS (served by Vercel CDN; by Flask locally)
tests/                unittest suites
requirements.txt  .env.example  .gitignore
```

## How it works
**Graph.** `graph[user] = set_of_friends`, stored as a dict of sets. Every friendship is added to both users' sets so it is always symmetric. The graph is rebuilt from the database on each request.

**Mutual friends.** `adj[a] & adj[b]` (set intersection).

**Recommendations.** For the selected user, visit each friend's friends. Skip the user and existing friends. Count how many different friends lead to each candidate (the mutual-friend count). Sort by count descending, then by name ascending (case-insensitive) so ties are stable.

**BFS and shortest path.** Both use `collections.deque`. BFS visits neighbours in alphabetical order and returns the visit order of the connected component. Shortest path runs BFS from the source while recording each node's parent, then walks parents back from the destination. BFS finds the fewest links on an unweighted graph. If the destination is never reached there is no path.

## Run locally (VS Code, Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. Without `DATABASE_URL`, data is stored in `data/network.db` (created automatically, never wiped on startup).

## Tests
```powershell
python -m unittest discover -s tests
```

## Database setup
Tables (`users`, `friendships`) are created with `CREATE TABLE IF NOT EXISTS` on the first request, so there is no separate migration step and existing data is never dropped.
For production:
1. Create a free PostgreSQL database (for example at neon.tech).
2. Copy its connection string (`postgresql://user:password@host/dbname?sslmode=require`).
3. Set it as `DATABASE_URL` (see below). Never commit it.

## Environment variables
| Name | Purpose |
|------|---------|
| `DATABASE_URL` | PostgreSQL connection string. Required on Vercel. Unset locally to use SQLite. |
| `SECRET_KEY` | Random string for signing session cookies / CSRF tokens. Required on Vercel. |
| `SQLITE_PATH` | Optional local SQLite file path. |

Generate a key: `python -c "import secrets; print(secrets.token_hex(32))"`

## Upload to GitHub
```powershell
git init
git add .
git commit -m "Phase 3: social network friend recommendation system"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```
`.gitignore` already excludes `.env`, `.venv` and local databases.

## Deploy on Vercel
Per the current Vercel Flask documentation, Vercel detects a Flask instance named `app` in `app.py`, so no `vercel.json` is needed. Static files must live in `public/`, which is why CSS/JS are in `public/static/`.
1. Push the project to GitHub.
2. In Vercel: Add New > Project > import the repository. Framework preset: Flask / Other. Leave build and output settings empty.
3. Under Environment Variables add `DATABASE_URL` and `SECRET_KEY`.
4. Deploy, then open `/health`. It returns `{"status": "ok"}` when the database is reachable.

## Common deployment errors
| Problem | Fix |
|---------|-----|
| Page shows "DATABASE_URL is not set" | Add the variable in Vercel > Settings > Environment Variables and redeploy. |
| "Could not connect to the database" | Check the connection string, that it includes `sslmode=require`, and that the database is running. |
| `ModuleNotFoundError` | Make sure the package is listed in `requirements.txt`. |
| Styles missing | CSS must be under `public/static/`; do not rely on Flask's static folder on Vercel. |
| "form was invalid" (400) | `SECRET_KEY` changed or is missing, or the session cookie expired. Set a fixed `SECRET_KEY`. |
| Data disappears | You are running without `DATABASE_URL` on Vercel. Local SQLite is not persistent there. |

## Limitations and future ideas
- No user accounts or authentication.
- The graph is reloaded from the database on every request, which is fine for hundreds of users but not for very large networks.
- Possible additions: weighted recommendations, graph visualisation, CSV import/export.
