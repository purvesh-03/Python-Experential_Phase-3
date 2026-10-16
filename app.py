"""Flask application: routes for the Social Network Friend Recommendation System."""
import logging
import os
import secrets

from flask import (Flask, abort, flash, redirect, render_template, request,
                   session, url_for)

from database import Database, DatabaseError
from graph import GraphError
from recommendations import mutual_friends, network_statistics, recommend

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("friendnet")


class ConfigError(Exception):
    pass


def create_app(db=None):
    root = os.path.dirname(os.path.abspath(__file__))
    # Vercel serves public/** from its CDN; Flask serves the same folder locally.
    app = Flask(__name__, static_folder=os.path.join(root, "public", "static"),
                static_url_path="/static", template_folder=os.path.join(root, "templates"))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["_db"] = db
    app.config["_ready"] = db is not None and getattr(db, "_ready", False)

    def get_db():
        d = app.config["_db"]
        if d is None:
            if os.environ.get("VERCEL") and not os.environ.get("DATABASE_URL"):
                raise ConfigError(
                    "DATABASE_URL is not set. Add your PostgreSQL connection string "
                    "in the Vercel project's Environment Variables.")
            d = app.config["_db"] = Database()
        if not app.config["_ready"]:
            d.init_schema()
            app.config["_ready"] = True
        return d

    # ---- CSRF ---------------------------------------------------------
    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect():
        if request.method == "POST":
            sent = request.form.get("csrf_token", "")
            if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
                abort(400, "Your session expired or the form was invalid. Please try again.")

    @app.context_processor
    def nav():
        return {"nav_items": [
            ("index", "Dashboard"), ("users", "Users"), ("friendships", "Friendships"),
            ("recommendations", "Recommendations"), ("network", "Network Explorer"),
            ("shortest_path", "Shortest Path"), ("statistics", "Statistics")]}

    # ---- errors -------------------------------------------------------
    def show_error(code, message):
        return render_template("error.html", code=code, message=message), code

    @app.errorhandler(400)
    def bad_request(e):
        return show_error(400, getattr(e, "description", "Bad request."))

    @app.errorhandler(404)
    def not_found(e):
        return show_error(404, "The page you requested was not found.")

    @app.errorhandler(405)
    def not_allowed(e):
        return show_error(405, "That method is not allowed for this page.")

    @app.errorhandler(ConfigError)
    def config_error(e):
        log.error("Configuration error: %s", e)
        return show_error(500, str(e))

    @app.errorhandler(DatabaseError)
    def db_error(e):
        return show_error(503, str(e))

    @app.errorhandler(Exception)
    def unexpected(e):
        from werkzeug.exceptions import HTTPException
        if isinstance(e, HTTPException):
            return show_error(e.code or 500, e.description)
        log.exception("Unhandled error")
        return show_error(500, "Something went wrong on the server. Please try again.")

    # ---- helpers ------------------------------------------------------
    def back(endpoint, **kw):
        return redirect(url_for(endpoint, **kw))

    # ---- pages --------------------------------------------------------
    @app.route("/")
    def index():
        graph = get_db().load_graph()
        return render_template("index.html", stats=network_statistics(graph))

    @app.route("/health")
    def health():
        get_db().check()
        return {"status": "ok"}

    @app.route("/users", methods=["GET", "POST"])
    def users():
        db = get_db()
        if request.method == "POST":
            try:
                name = db.add_user(request.form.get("name"))
                flash(f"User '{name}' was added.", "success")
            except DatabaseError as e:
                flash(str(e), "error")
            return back("users")
        q = (request.args.get("q") or "").strip()
        graph = db.load_graph()
        names = graph.users()
        if q:
            names = [n for n in names if q.lower() in n.lower()]
        rows = [{"name": n, "friends": len(graph.adj[n])} for n in names]
        return render_template("users.html", rows=rows, q=q)

    @app.route("/users/<name>")
    def user_detail(name):
        db = get_db()
        try:
            name = db.get_user(name)
        except DatabaseError:
            abort(404)
        graph = db.load_graph()
        return render_template(
            "user_detail.html", name=name, friends=graph.friends(name),
            recs=recommend(graph, name, limit=5))

    @app.route("/users/<name>/delete", methods=["POST"])
    def delete_user(name):
        try:
            get_db().remove_user(name)
            flash(f"User '{name}' and their friendships were removed.", "success")
        except DatabaseError as e:
            flash(str(e), "error")
        return back("users")

    @app.route("/friendships", methods=["GET", "POST"])
    def friendships():
        db = get_db()
        if request.method == "POST":
            a, b = request.form.get("user_a", ""), request.form.get("user_b", "")
            try:
                db.add_friendship(a, b)
                flash(f"{a} and {b} are now friends.", "success")
            except DatabaseError as e:
                flash(str(e), "error")
            return back("friendships")
        graph = db.load_graph()
        return render_template("friendships.html", names=graph.users(), edges=graph.edges())

    @app.route("/friendships/remove", methods=["POST"])
    def remove_friendship():
        a, b = request.form.get("user_a", ""), request.form.get("user_b", "")
        try:
            get_db().remove_friendship(a, b)
            flash(f"Friendship between {a} and {b} was removed.", "success")
        except DatabaseError as e:
            flash(str(e), "error")
        return back(request.form.get("next") if request.form.get("next") in
                    ("friendships", "network") else "friendships")

    @app.route("/recommendations")
    def recommendations():
        graph = get_db().load_graph()
        names = graph.users()
        user = request.args.get("user", "")
        m1, m2 = request.args.get("m1", ""), request.args.get("m2", "")
        recs = error = mutual = mutual_error = None
        if user:
            try:
                recs = recommend(graph, user)
            except GraphError as e:
                error = str(e)
        if m1 and m2:
            try:
                mutual = mutual_friends(graph, m1, m2)
            except GraphError as e:
                mutual_error = str(e)
        return render_template("recommendations.html", names=names, user=user, recs=recs,
                               error=error, m1=m1, m2=m2, mutual=mutual,
                               mutual_error=mutual_error)

    @app.route("/network")
    def network():
        graph = get_db().load_graph()
        start = request.args.get("start", "")
        order = error = None
        if start:
            try:
                order = graph.bfs(start)
            except GraphError as e:
                error = str(e)
        table = [{"name": n, "friends": graph.friends(n)} for n in graph.users()]
        return render_template("network.html", table=table, names=graph.users(),
                               start=start, order=order, error=error)

    @app.route("/shortest-path")
    def shortest_path():
        graph = get_db().load_graph()
        src, dst = request.args.get("source", ""), request.args.get("target", "")
        path = error = None
        searched = False
        if src and dst:
            searched = True
            try:
                path = graph.shortest_path(src, dst)
            except GraphError as e:
                error, searched = str(e), False
        return render_template("shortest_path.html", names=graph.users(), src=src, dst=dst,
                               path=path, searched=searched, error=error)

    @app.route("/statistics")
    def statistics():
        graph = get_db().load_graph()
        return render_template("statistics.html", stats=network_statistics(graph))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", 5000)))
