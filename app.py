from flask import Flask, render_template, request, redirect, url_for, flash
import os
from collections import deque
import re

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "friendnet-demo-key-change-in-production")

# Demo data. For persistent production data on Vercel, connect a hosted database.
users = {"purvesh", "radha"}
friends = {"purvesh": {"radha"}, "radha": {"purvesh"}}

def clean_name(value):
    value = re.sub(r"\s+", " ", (value or "").strip())
    if not value or len(value) > 60 or not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", value):
        return None
    return value

def user_key(name):
    return name.casefold()

def get_name(key):
    return next((u for u in users if user_key(u) == key), key)

def add_user(name):
    key = user_key(name)
    if any(user_key(u) == key for u in users):
        return False
    users.add(name)
    friends[key] = set()
    return True

def connect(a, b):
    ka, kb = user_key(a), user_key(b)
    if ka == kb or ka not in {user_key(u) for u in users} or kb not in {user_key(u) for u in users}:
        return False, "Choose two different existing users."
    if kb in friends.get(ka, set()):
        return False, "These users are already friends."
    friends.setdefault(ka, set()).add(kb)
    friends.setdefault(kb, set()).add(ka)
    return True, f"{get_name(ka)} and {get_name(kb)} are now connected."

def disconnect(a, b):
    ka, kb = user_key(a), user_key(b)
    friends.get(ka, set()).discard(kb)
    friends.get(kb, set()).discard(ka)

def mutual_friends(a, b):
    return sorted(friends.get(user_key(a), set()) & friends.get(user_key(b), set()))

def recommend(user):
    key = user_key(user)
    scores = {}
    for friend in friends.get(key, set()):
        for candidate in friends.get(friend, set()):
            if candidate != key and candidate not in friends.get(key, set()):
                scores[candidate] = scores.get(candidate, 0) + 1
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))

def bfs(start):
    start = user_key(start)
    if start not in {user_key(u) for u in users}:
        return []
    seen, queue, order = {start}, deque([start]), []
    while queue:
        current = queue.popleft()
        order.append(get_name(current))
        for nxt in sorted(friends.get(current, set())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return order

def shortest_path(start, end):
    start, end = user_key(start), user_key(end)
    valid = {user_key(u) for u in users}
    if start not in valid or end not in valid:
        return []
    queue = deque([(start, [start])])
    seen = {start}
    while queue:
        current, path = queue.popleft()
        if current == end:
            return [get_name(k) for k in path]
        for nxt in sorted(friends.get(current, set())):
            if nxt not in seen:
                seen.add(nxt)
                queue.append((nxt, path + [nxt]))
    return []

def stats():
    count = len(users)
    edge_count = sum(len(v) for v in friends.values()) // 2
    degrees = {user_key(u): len(friends.get(user_key(u), set())) for u in users}
    avg = (sum(degrees.values()) / count) if count else 0
    isolated = sum(1 for d in degrees.values() if d == 0)
    most = sorted(users, key=lambda u: (-degrees[user_key(u)], user_key(u)))
    total_recs = sum(len(recommend(u)) for u in users)
    return {
        "users": count, "friendships": edge_count, "average": round(avg, 1),
        "isolated": isolated, "most_name": most[0] if most else "—",
        "most_count": degrees[user_key(most[0])] if most else 0,
        "users_with_recs": sum(1 for u in users if recommend(u)),
        "total_recs": total_recs
    }

@app.context_processor
def inject_navigation():
    def friend_count(name):
        return len(friends.get(user_key(name), set()))
    return {"friend_count": friend_count, "nav_items": [
        ("Dashboard", "dashboard"), ("Users", "users_page"),
        ("Friendships", "friendships_page"), ("Recommendations", "recommendations_page"),
        ("Network Explorer", "network_page"), ("Shortest Path", "shortest_path_page"),
        ("Statistics", "statistics_page")
    ]}

@app.get("/")
def dashboard():
    return render_template("dashboard.html", stats=stats(), active="Dashboard")

@app.route("/users", methods=["GET", "POST"])
def users_page():
    search = request.args.get("q", "").strip()
    if request.method == "POST":
        name = clean_name(request.form.get("name"))
        if not name:
            flash("Enter a valid name using letters, spaces, apostrophes, dots or hyphens.", "error")
        elif add_user(name):
            flash(f"Added {name}.", "success")
        else:
            flash("That user already exists (names are case-insensitive).", "error")
        return redirect(url_for("users_page"))
    shown = sorted([u for u in users if search.casefold() in u.casefold()], key=str.casefold)
    return render_template("users.html", active="Users", users=shown, search=search, all_count=len(users))

@app.post("/users/remove")
def remove_user():
    key = user_key(request.form.get("name", ""))
    found = next((u for u in users if user_key(u) == key), None)
    if found:
        for friend in list(friends.get(key, set())):
            friends.get(friend, set()).discard(key)
        friends.pop(key, None)
        users.remove(found)
        flash(f"Removed {found} and their friendship links.", "success")
    return redirect(url_for("users_page"))

@app.get("/users/<path:name>")
def user_detail(name):
    key = user_key(name)
    found = next((u for u in users if user_key(u) == key), None)
    if not found:
        flash("User not found.", "error")
        return redirect(url_for("users_page"))
    return render_template("user_detail.html", active="Users", person=found,
                           friends=sorted(friends.get(key, set())),
                           recommendations=recommend(found))

@app.route("/friendships", methods=["GET", "POST"])
def friendships_page():
    if request.method == "POST":
        ok, message = connect(request.form.get("first"), request.form.get("second"))
        flash(message, "success" if ok else "error")
        return redirect(url_for("friendships_page"))
    links = []
    for key, vals in friends.items():
        for other in vals:
            if key < other:
                links.append((get_name(key), get_name(other)))
    links.sort(key=lambda pair: (pair[0].casefold(), pair[1].casefold()))
    return render_template("friendships.html", active="Friendships",
                           users=sorted(users, key=str.casefold), links=links)

@app.post("/friendships/remove")
def remove_friendship():
    disconnect(request.form.get("first", ""), request.form.get("second", ""))
    flash("Friendship removed.", "success")
    return redirect(url_for("friendships_page"))

@app.route("/recommendations", methods=["GET", "POST"])
def recommendations_page():
    selected = request.form.get("user", "") if request.method == "POST" else request.args.get("user", "")
    results = recommend(selected) if selected and user_key(selected) in {user_key(u) for u in users} else []
    mutual = None
    first, second = "", ""
    if request.method == "POST" and request.form.get("action") == "mutual":
        first, second = request.form.get("first", ""), request.form.get("second", "")
        if first and second and user_key(first) != user_key(second):
            mutual = mutual_friends(first, second)
        else:
            flash("Select two different users to find mutual friends.", "error")
    return render_template("recommendations.html", active="Recommendations",
                           users=sorted(users, key=str.casefold), selected=selected,
                           results=results, mutual=mutual, first=first, second=second)

@app.route("/network", methods=["GET", "POST"])
def network_page():
    start = request.form.get("start", "") if request.method == "POST" else ""
    traversal = bfs(start) if start else []
    adjacency = [(u, len(friends.get(user_key(u), set())),
                  [get_name(k) for k in sorted(friends.get(user_key(u), set()))]) for u in sorted(users, key=str.casefold)]
    return render_template("network.html", active="Network Explorer", users=sorted(users, key=str.casefold),
                           adjacency=adjacency, start=start, traversal=traversal)

@app.route("/shortest-path", methods=["GET", "POST"])
def shortest_path_page():
    first = request.form.get("first", "")
    second = request.form.get("second", "")
    path = shortest_path(first, second) if request.method == "POST" else None
    return render_template("shortest_path.html", active="Shortest Path",
                           users=sorted(users, key=str.casefold), first=first, second=second, path=path)

@app.get("/statistics")
def statistics_page():
    return render_template("statistics.html", active="Statistics", stats=stats())

@app.errorhandler(404)
def not_found(error):
    return render_template("404.html", active=""), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
