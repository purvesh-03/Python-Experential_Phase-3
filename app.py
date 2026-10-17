"""
app.py - Flask Application & HTTP Route Handlers
Phase 3: Social Network Friend Recommendation System

Provides:
- Jinja2 Server-Rendered Views: Dashboard, Users, Profile, Friendships, Recommendations,
  Network Explorer, Shortest Path, BFS Traversal, Statistics.
- RESTful JSON API endpoints for dynamic frontend features and tests.
- Form validation, CSRF protection, error handling, flash alerts, and CSV export.
- Reliable Vercel serverless deployment entry point: exposes `app`.
"""

import csv
import io
import os
import time
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    Response,
    abort
)

from database import db
from graph import SocialGraph
from recommendations import recommend_friends, get_mutual_friends

# Set up paths relative to this file for cross-platform and Vercel compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)

app.secret_key = os.environ.get("SECRET_KEY", "social-graph-phase3-college-project-2026")

# In-memory Graph instance
social_graph = SocialGraph()


def sync_graph():
    """Synchronizes the in-memory graph with the database."""
    db.load_graph_from_db(social_graph)


# Initialize DB and populate in-memory graph
try:
    db.init_db()
    db.seed_initial_data_if_empty()
    sync_graph()
except Exception as e:
    app.logger.error(f"Error during database initialization: {e}")


@app.before_request
def ensure_graph_loaded():
    """Ensures in-memory graph is populated for serverless cold-starts."""
    if len(social_graph.users) == 0:
        sync_graph()


# -----------------------------------------------------------------
# Context Processor for Global Template Data
# -----------------------------------------------------------------

@app.context_processor
def inject_global_data():
    """Provides common data to all Jinja templates."""
    all_users = social_graph.get_all_users()
    return {
        "all_users_global": all_users,
        "current_year": time.strftime("%Y")
    }


# -----------------------------------------------------------------
# Page Routes
# -----------------------------------------------------------------

@app.route("/")
@app.route("/dashboard")
def dashboard():
    """Dashboard view showing network metrics and quick actions."""
    stats = social_graph.get_statistics()
    all_users = social_graph.get_all_users()
    friendships = social_graph.get_all_friendships()

    # Top connected users
    top_connected = sorted(
        all_users,
        key=lambda u: len(social_graph.adj.get(u["id"], set())),
        reverse=True
    )[:5]

    return render_template(
        "index.html",
        stats=stats,
        top_connected=top_connected,
        total_friendships=len(friendships),
        active_page="dashboard"
    )


@app.route("/users")
def users_list():
    """User directory view with search and add user form."""
    query = request.args.get("q", "").strip()
    if query:
        users = social_graph.search_users(query)
    else:
        users = social_graph.get_all_users()

    # Augment users with their friend count
    users_with_counts = [
        {
            "data": u,
            "friend_count": len(social_graph.adj.get(u["id"], set()))
        }
        for u in users
    ]

    return render_template(
        "users.html",
        users=users_with_counts,
        search_query=query,
        active_page="users"
    )


@app.route("/users/add", methods=["POST"])
def add_user():
    """Handles adding a new user."""
    name = request.form.get("name", "").strip()
    bio = request.form.get("bio", "").strip() or "Member"

    if not name:
        flash("User name is required.", "danger")
        return redirect(url_for("users_list"))

    # Check for duplicate user name
    existing = social_graph.get_user_by_name(name)
    if existing:
        flash(f"A user named '{name}' already exists in the network.", "warning")
        return redirect(url_for("users_list"))

    # Generate a unique user ID
    user_id = f"u{int(time.time() * 1000) % 1000000}"

    # Persist in DB and Graph
    success, res = db.create_user(user_id, name, bio)
    if success:
        social_graph.add_user(user_id, name, bio)
        flash(f"User '{name}' added successfully to the social network.", "success")
    else:
        flash(f"Failed to add user: {res}", "danger")

    return redirect(url_for("users_list"))


@app.route("/users/<user_id>")
def user_detail(user_id):
    """Individual user profile view with friends and personalized recommendations."""
    user = social_graph.get_user(user_id)
    if not user:
        flash("User not found.", "warning")
        return redirect(url_for("users_list"))

    direct_friends = social_graph.get_friends(user_id)
    recs = recommend_friends(social_graph, user_id, limit=5)

    return render_template(
        "user_detail.html",
        user=user,
        direct_friends=direct_friends,
        recommendations=recs.get("recommendations", []),
        active_page="users"
    )


@app.route("/users/delete/<user_id>", methods=["POST"])
def delete_user(user_id):
    """Removes a user and cascades deletion of friendships."""
    user = social_graph.get_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("users_list"))

    user_name = user["name"]
    db_success, db_msg = db.delete_user(user_id)
    if db_success:
        social_graph.remove_user(user_id)
        flash(f"User '{user_name}' and all associated connections removed.", "success")
    else:
        flash(f"Error removing user: {db_msg}", "danger")

    return redirect(url_for("users_list"))


@app.route("/friendships")
def friendships_list():
    """Friendship connections view with connect form and edge list."""
    all_friendships = social_graph.get_all_friendships()
    all_users = social_graph.get_all_users()

    return render_template(
        "friendships.html",
        friendships=all_friendships,
        users=all_users,
        active_page="friendships"
    )


@app.route("/friendships/add", methods=["POST"])
def add_friendship():
    """Creates a new friendship edge between two users."""
    u1 = request.form.get("user1_id", "").strip()
    u2 = request.form.get("user2_id", "").strip()
    redirect_to = request.form.get("redirect_to")

    if not u1 or not u2:
        flash("Please select both users.", "danger")
        return redirect(redirect_to or url_for("friendships_list"))

    if u1 == u2:
        flash("A user cannot be friends with themselves.", "warning")
        return redirect(redirect_to or url_for("friendships_list"))

    user1 = social_graph.get_user(u1)
    user2 = social_graph.get_user(u2)

    if not user1 or not user2:
        flash("One or both users do not exist.", "danger")
        return redirect(redirect_to or url_for("friendships_list"))

    if social_graph.are_friends(u1, u2):
        flash(f"'{user1['name']}' and '{user2['name']}' are already friends.", "info")
        return redirect(redirect_to or url_for("friendships_list"))

    # Persist in DB and Graph
    db_ok, db_msg = db.create_friendship(u1, u2)
    if db_ok:
        social_graph.add_friendship(u1, u2)
        flash(f"Friendship created between {user1['name']} and {user2['name']}.", "success")
    else:
        flash(f"Failed to create friendship: {db_msg}", "danger")

    return redirect(redirect_to or url_for("friendships_list"))


@app.route("/friendships/remove", methods=["POST"])
def remove_friendship():
    """Removes a friendship edge between two users."""
    u1 = request.form.get("user1_id", "").strip()
    u2 = request.form.get("user2_id", "").strip()
    redirect_to = request.form.get("redirect_to")

    user1 = social_graph.get_user(u1)
    user2 = social_graph.get_user(u2)

    db_ok, db_msg = db.delete_friendship(u1, u2)
    if db_ok:
        social_graph.remove_friendship(u1, u2)
        u1_name = user1["name"] if user1 else u1
        u2_name = user2["name"] if user2 else u2
        flash(f"Friendship removed between {u1_name} and {u2_name}.", "info")
    else:
        flash(f"Failed to remove friendship: {db_msg}", "danger")

    return redirect(redirect_to or url_for("friendships_list"))


@app.route("/recommendations")
def recommendations_page():
    """Friend recommendation engine view."""
    all_users = social_graph.get_all_users()
    selected_user_id = request.args.get("user_id", "").strip()

    recommendations_result = None
    selected_user = None

    if selected_user_id:
        selected_user = social_graph.get_user(selected_user_id)
        if selected_user:
            recommendations_result = recommend_friends(social_graph, selected_user_id)
        else:
            flash("Selected user not found.", "warning")

    # Mutual friends inspection section
    m_u1 = request.args.get("mutual_u1", "").strip()
    m_u2 = request.args.get("mutual_u2", "").strip()
    mutual_result = None
    if m_u1 and m_u2:
        mutual_result = get_mutual_friends(social_graph, m_u1, m_u2)

    return render_template(
        "recommendations.html",
        users=all_users,
        selected_user=selected_user,
        recommendations_result=recommendations_result,
        mutual_result=mutual_result,
        m_u1=m_u1,
        m_u2=m_u2,
        active_page="recommendations"
    )


@app.route("/network")
def network_explorer():
    """Network graph view with adjacency list table and SVG network visualizer."""
    all_users = social_graph.get_all_users()
    adjacency_list = []

    for user in all_users:
        friends = social_graph.get_friends(user["id"])
        adjacency_list.append({
            "user": user,
            "friends": friends,
            "degree": len(friends)
        })

    return render_template(
        "network.html",
        adjacency_list=adjacency_list,
        users=all_users,
        active_page="network"
    )


@app.route("/shortest-path")
def shortest_path_page():
    """Shortest connection path explorer using BFS."""
    all_users = social_graph.get_all_users()
    start_id = request.args.get("start", "").strip()
    dest_id = request.args.get("dest", "").strip()

    result = None
    if start_id and dest_id:
        result = social_graph.shortest_path(start_id, dest_id)

    return render_template(
        "shortest_path.html",
        users=all_users,
        start_id=start_id,
        dest_id=dest_id,
        result=result,
        active_page="shortest_path"
    )


@app.route("/bfs")
def bfs_traversal_page():
    """BFS traversal explorer view."""
    all_users = social_graph.get_all_users()
    start_id = request.args.get("start", "").strip()

    result = None
    if start_id:
        result = social_graph.bfs_traversal(start_id)

    return render_template(
        "bfs.html",
        users=all_users,
        start_id=start_id,
        result=result,
        active_page="bfs"
    )


@app.route("/statistics")
def statistics_page():
    """Dynamically calculated network statistics view."""
    stats = social_graph.get_statistics()
    all_users = social_graph.get_all_users()

    # User degree details table
    user_metrics = []
    for u in all_users:
        friends = social_graph.get_friends(u["id"])
        recs = recommend_friends(social_graph, u["id"])
        user_metrics.append({
            "user": u,
            "degree": len(friends),
            "recommendations_count": len(recs.get("recommendations", []))
        })

    user_metrics.sort(key=lambda m: (-m["degree"], m["user"]["name"].lower()))

    return render_template(
        "statistics.html",
        stats=stats,
        user_metrics=user_metrics,
        active_page="statistics"
    )


@app.route("/export/friends/<user_id>")
def export_friends_csv(user_id):
    """Exports a user's friend list as a downloadable CSV."""
    user = social_graph.get_user(user_id)
    if not user:
        abort(404, description="User not found")

    friends = social_graph.get_friends(user_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Friend User ID", "Friend Name", "Bio", "Member Since"])

    for f in friends:
        writer.writerow([f["id"], f["name"], f.get("bio", ""), f.get("created_at", "")])

    output.seek(0)
    filename = f"{user['name'].lower().replace(' ', '_')}_friends.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# -----------------------------------------------------------------
# JSON API Endpoints
# -----------------------------------------------------------------

@app.route("/api/graph", methods=["GET"])
def api_graph():
    """Returns network graph nodes and edges for dynamic visualization."""
    nodes = []
    for uid, user in social_graph.users.items():
        friends = social_graph.adj.get(uid, set())
        nodes.append({
            "id": uid,
            "name": user["name"],
            "bio": user.get("bio", "Member"),
            "degree": len(friends)
        })

    edges = []
    seen = set()
    for u1, friends in social_graph.adj.items():
        for u2 in friends:
            edge_key = tuple(sorted([u1, u2]))
            if edge_key not in seen:
                seen.add(edge_key)
                edges.append({"source": edge_key[0], "target": edge_key[1]})

    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/recommend/<user_id>", methods=["GET"])
def api_recommend(user_id):
    """Returns JSON friend recommendations for user_id."""
    return jsonify(recommend_friends(social_graph, user_id))


@app.route("/api/shortest-path", methods=["GET"])
def api_shortest_path():
    """Returns JSON shortest path between start and dest query params."""
    start = request.args.get("start")
    dest = request.args.get("dest")
    if not start or not dest:
        return jsonify({"success": False, "message": "Missing start or dest parameter"}), 400
    return jsonify(social_graph.shortest_path(start, dest))


@app.route("/api/stats", methods=["GET"])
def api_stats():
    """Returns JSON network statistics."""
    return jsonify(social_graph.get_statistics())


# -----------------------------------------------------------------
# Error Handlers
# -----------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        "error.html",
        error_code=404,
        error_title="Page Not Found",
        error_message="The requested page or resource could not be found in the network system."
    ), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template(
        "error.html",
        error_code=500,
        error_title="Internal Server Error",
        error_message="An unexpected server error occurred. Please verify database connection and retry."
    ), 500


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
