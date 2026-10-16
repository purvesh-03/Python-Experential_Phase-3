# FriendNet — Social Network Friend Recommendation System

A responsive Python Flask website inspired by the supplied FriendNet screenshots. It includes functional pages for the dashboard, users, friendships, friend recommendations, mutual friends, network explorer, BFS traversal, shortest path, and statistics.

## Run locally

1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. In the terminal, create and activate a virtual environment (optional but recommended):

   **Windows**
   ```bash
   py -m venv .venv
   .venv\Scripts\activate
   ```

   **macOS/Linux**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Start the website:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000`.

## Deploy to Vercel

1. Upload/push the project folder to a GitHub repository.
2. In Vercel, select **Add New → Project** and import that repository.
3. Keep `app.py`, `requirements.txt`, and `vercel.json` at the repository root.
4. Deploy. The `README.md` is documentation only and does not prevent deployment.

If the Vercel build fails, open **Deployments → latest deployment → Build Logs** and check the first actual error.

## Deploy to Render (recommended for this Flask project)

This project is a Flask website, not a Streamlit app. Do not deploy it to Streamlit Cloud unless you rewrite it using Streamlit.\n\n1. Push the folder to GitHub and create a **New Web Service** on Render.
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn app:app`
4. Choose the free instance if offered for your account/region.

## Important data note

This starter project stores graph data in Python memory so the interactions work in a demo. It starts with two example users, `purvesh` and `radha`. Data may reset when the process restarts, and serverless platforms such as Vercel do not provide durable local storage. For a real deployed project, connect a hosted database (for example PostgreSQL through Neon or Supabase) and store users/friendships there.

## Included features

- Add, search, view and remove users
- Create and remove undirected friendship links
- Recommendations ranked by number of mutual friends
- Mutual friends between two selected users
- Adjacency list and breadth-first search (BFS)
- Shortest path between users using BFS
- Live dashboard and network statistics
- Responsive layout for mobile and desktop
