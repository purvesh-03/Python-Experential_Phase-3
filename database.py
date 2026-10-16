"""Data access layer: SQLite locally, PostgreSQL when DATABASE_URL is set."""
import os
import re
import sqlite3
from contextlib import contextmanager

from graph import SocialGraph


class DatabaseError(Exception):
    """Raised for validation or storage problems."""


NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'\-]{0,58}[A-Za-z.]$|^[A-Za-z]$")


def normalize_name(raw):
    name = " ".join((raw or "").split())
    if not name:
        raise DatabaseError("Name cannot be empty.")
    if not NAME_RE.match(name):
        raise DatabaseError(
            "Name must be 1-60 characters: letters, spaces, apostrophes, dots or hyphens.")
    return name


class Database:
    def __init__(self, url=None, sqlite_path=None):
        self.url = url if url is not None else os.environ.get("DATABASE_URL", "")
        self.is_pg = self.url.startswith(("postgres://", "postgresql://"))
        if not self.is_pg:
            self.path = sqlite_path or os.environ.get("SQLITE_PATH") or os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "data", "network.db")
            if self.path != ":memory:":
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._mem = None

    # ---- connection ---------------------------------------------------
    @contextmanager
    def _conn(self):
        if self.is_pg:
            try:
                import psycopg
            except ImportError as exc:
                raise DatabaseError("psycopg is not installed.") from exc
            try:
                conn = psycopg.connect(self.url, connect_timeout=10)
            except Exception as exc:
                raise DatabaseError("Could not connect to the database.") from exc
        else:
            if self.path == ":memory:":
                if self._mem is None:
                    self._mem = sqlite3.connect(":memory:", check_same_thread=False)
                conn = self._mem
            else:
                conn = sqlite3.connect(self.path)
            conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if not (not self.is_pg and self.path == ":memory:"):
                conn.close()

    def _run(self, conn, sql, params=()):
        if self.is_pg:
            sql = sql.replace("?", "%s")
        return conn.execute(sql, params)

    # ---- schema -------------------------------------------------------
    def init_schema(self):
        """Create tables if missing. Never drops or erases data."""
        pk = "SERIAL PRIMARY KEY" if self.is_pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
        with self._conn() as c:
            self._run(c, f"CREATE TABLE IF NOT EXISTS users ("
                         f"id {pk}, name TEXT NOT NULL, name_key TEXT NOT NULL UNIQUE)")
            self._run(c, "CREATE TABLE IF NOT EXISTS friendships ("
                         "user_a INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
                         "user_b INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,"
                         "PRIMARY KEY (user_a, user_b), CHECK (user_a < user_b))")

    def check(self):
        with self._conn() as c:
            self._run(c, "SELECT 1").fetchone()
        return True

    # ---- users --------------------------------------------------------
    def _user_id(self, c, name):
        row = self._run(c, "SELECT id FROM users WHERE name_key = ?",
                        (normalize_name(name).lower(),)).fetchone()
        if not row:
            raise DatabaseError(f"User '{name}' does not exist.")
        return row[0]

    def add_user(self, raw):
        name = normalize_name(raw)
        with self._conn() as c:
            if self._run(c, "SELECT 1 FROM users WHERE name_key = ?",
                         (name.lower(),)).fetchone():
                raise DatabaseError(f"User '{name}' already exists.")
            self._run(c, "INSERT INTO users (name, name_key) VALUES (?, ?)",
                      (name, name.lower()))
        return name

    def remove_user(self, raw):
        with self._conn() as c:
            uid = self._user_id(c, raw)
            self._run(c, "DELETE FROM friendships WHERE user_a = ? OR user_b = ?", (uid, uid))
            self._run(c, "DELETE FROM users WHERE id = ?", (uid,))

    def list_users(self):
        with self._conn() as c:
            rows = self._run(c, "SELECT name FROM users ORDER BY name_key").fetchall()
        return [r[0] for r in rows]

    def get_user(self, raw):
        with self._conn() as c:
            row = self._run(c, "SELECT name FROM users WHERE name_key = ?",
                            (" ".join((raw or "").split()).lower(),)).fetchone()
        if not row:
            raise DatabaseError(f"User '{raw}' does not exist.")
        return row[0]

    # ---- friendships --------------------------------------------------
    def add_friendship(self, a, b):
        with self._conn() as c:
            ia, ib = self._user_id(c, a), self._user_id(c, b)
            if ia == ib:
                raise DatabaseError("A user cannot be friends with themselves.")
            lo, hi = sorted((ia, ib))
            if self._run(c, "SELECT 1 FROM friendships WHERE user_a = ? AND user_b = ?",
                         (lo, hi)).fetchone():
                raise DatabaseError("These users are already friends.")
            self._run(c, "INSERT INTO friendships (user_a, user_b) VALUES (?, ?)", (lo, hi))

    def remove_friendship(self, a, b):
        with self._conn() as c:
            ia, ib = self._user_id(c, a), self._user_id(c, b)
            lo, hi = sorted((ia, ib))
            cur = self._run(c, "DELETE FROM friendships WHERE user_a = ? AND user_b = ?",
                            (lo, hi))
            if cur.rowcount == 0:
                raise DatabaseError("These users are not friends.")

    # ---- graph loading ------------------------------------------------
    def load_graph(self):
        with self._conn() as c:
            users = [r[0] for r in self._run(c, "SELECT name FROM users").fetchall()]
            edges = self._run(
                c, "SELECT a.name, b.name FROM friendships f "
                   "JOIN users a ON a.id = f.user_a JOIN users b ON b.id = f.user_b").fetchall()
        return SocialGraph.from_data(users, [(a, b) for a, b in edges])
